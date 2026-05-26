#!/usr/bin/env python3
"""skill-cleaner.py — Suggest-first maintenance analyzer for skill repositories.

Reports four classes of cleanup candidates WITHOUT modifying or deleting anything
(SKILL-GOVERNANCE-SPEC §10.5). A human approves every removal or merge.

  1. Budget allocation    — total skill footprint and its share of the context window
  2. Verbose descriptions — frontmatter descriptions above the spec's 40-80 word target
  3. Overlap candidates   — skill pairs with high name+description similarity (possible merge)
  4. Unused skills        — inventoried skills with zero telemetry invocations in a window

Thresholds and the preserve-list are read from the "cleaner" block of
pipeline/config/budgets.json; CLI flags override them. Output is pure stdout — the
tool never writes, mutates, or deletes files.
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

# Reuse shared hook helpers (classification, exclusion) so this tool agrees with
# the pre-commit pipeline on what counts as a skill.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))
from _utils import classify_file, is_excluded  # noqa: E402

TOKEN_RATIO = 1.33
DEFAULT_CONTEXT_WINDOW = 200000
DEFAULT_VERBOSE_DESCRIPTION_WORDS = 80  # matches the spec's 40-80 word target ceiling
DEFAULT_OVERLAP_THRESHOLD = 0.6
DEFAULT_UNUSED_DAYS = 30
DEFAULT_TELEMETRY_FILE = os.path.expanduser("~/.claude/telemetry/skill-usage.jsonl")

# Low-signal words dropped before comparing descriptions for overlap.
STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "use",
    "uses", "using", "when", "this", "that", "from", "into", "any", "only", "not",
    "do", "does", "user", "asks", "ask", "trigger", "triggers", "first", "before",
    "after", "is", "are", "be", "it", "its", "as", "at", "by", "if", "you", "your",
    "than", "then", "but", "all", "via", "per", "out", "up", "so", "no", "yes",
    "skill", "skills", "claude", "should", "must", "will", "can", "each", "time",
}
WORD_RE = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Repository + config resolution
# ---------------------------------------------------------------------------

def resolve_repo_root(root_arg):
    """Resolve the repo root: explicit --root, else walk up for pipeline/config."""
    if root_arg:
        root = os.path.abspath(root_arg)
        if not os.path.isdir(root):
            raise SystemExit(f"ERROR: --root path does not exist: {root}")
        return root

    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(d, "pipeline", "config")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("ERROR: could not locate repo root (no pipeline/config found)")
        d = parent


def load_cleaner_config(repo_root):
    """Load the 'cleaner' block from budgets.json, falling back to defaults."""
    config_path = os.path.join(repo_root, "pipeline", "config", "budgets.json")
    cleaner = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cleaner = json.load(f).get("cleaner", {})
    except FileNotFoundError:
        print(f"WARNING: budgets.json not found at {config_path}; using defaults",
              file=sys.stderr)
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: could not parse {config_path} ({e}); using defaults",
              file=sys.stderr)

    return {
        "context_window": cleaner.get("context_window", DEFAULT_CONTEXT_WINDOW),
        "verbose_description_words": cleaner.get(
            "verbose_description_words", DEFAULT_VERBOSE_DESCRIPTION_WORDS),
        "overlap_threshold": cleaner.get("overlap_threshold", DEFAULT_OVERLAP_THRESHOLD),
        "unused_days": cleaner.get("unused_days", DEFAULT_UNUSED_DAYS),
        "preserve": list(cleaner.get("preserve", [])),
    }


# ---------------------------------------------------------------------------
# Skill inventory
# ---------------------------------------------------------------------------

def extract_frontmatter(text):
    """Parse YAML frontmatter between --- markers. Returns a dict (may be empty)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end_idx = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end_idx is None:
        return {}
    yaml_text = "\n".join(lines[1:end_idx])

    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(yaml_text)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            # One malformed SKILL.md must not abort the whole scan — warn and
            # fall through to the tolerant line-based parser below.
            print(f"WARNING: malformed YAML frontmatter ({e}); using fallback parser",
                  file=sys.stderr)

    # Fallback: handle simple `key: value` and folded `key: >` descriptions.
    data = {}
    raw = lines[1:end_idx]
    i = 0
    while i < len(raw):
        line = raw[i]
        if ":" not in line or line.startswith((" ", "-", "\t")):
            i += 1
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value in (">", "|", ">-", "|-"):
            block = []
            i += 1
            while i < len(raw) and (raw[i].startswith((" ", "\t")) or not raw[i].strip()):
                block.append(raw[i].strip())
                i += 1
            data[key] = " ".join(b for b in block if b)
            continue
        data[key] = value
        i += 1
    return data


def file_tokens(filepath):
    """Estimate tokens for a file from its whole-text word count."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            words = len(f.read().split())
    except (OSError, UnicodeDecodeError) as e:
        print(f"WARNING: could not read {filepath} ({e}); counted as 0 tokens",
              file=sys.stderr)
        return 0
    return int(math.ceil(words * TOKEN_RATIO))


def collect_md_files(repo_root):
    """All SKILL.md and references/*.md files outside excluded directories."""
    results = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo_root).replace("\\", "/")
            if fn == "SKILL.md" and not is_excluded(full, repo_root):
                results.append(full)
            elif ("references/" in rel or "shared-references/" in rel) and not is_excluded(full, repo_root):
                results.append(full)
    return sorted(results)


def build_inventory(repo_root):
    """Build per-skill records keyed by skill directory.

    Each record: name, rel_dir, skill_md, classification, description,
    description_words, footprint_tokens (SKILL.md + references in that dir tree).
    """
    skills = {}
    for full in collect_md_files(repo_root):
        if os.path.basename(full) != "SKILL.md":
            continue
        classification = classify_file(full, repo_root)
        if classification == "skip":
            continue
        skill_dir = os.path.dirname(full)
        rel_dir = os.path.relpath(skill_dir, repo_root).replace("\\", "/")
        try:
            with open(full, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"WARNING: could not read {full} ({e}); "
                  "description and footprint will be understated", file=sys.stderr)
            text = ""
        fm = extract_frontmatter(text)
        description = (fm.get("description") or "").strip()
        skills[rel_dir] = {
            "name": fm.get("name") or os.path.basename(skill_dir),
            "rel_dir": rel_dir,
            "skill_md": os.path.relpath(full, repo_root).replace("\\", "/"),
            "classification": classification,
            "description": description,
            "description_words": len(description.split()),
            "footprint_tokens": 0,
        }

    # Attribute every md file's tokens to the nearest enclosing skill directory.
    for full in collect_md_files(repo_root):
        rel = os.path.relpath(full, repo_root).replace("\\", "/")
        owner = max((d for d in skills if rel == d + "/SKILL.md" or rel.startswith(d + "/")),
                    key=len, default=None)
        if owner is not None:
            skills[owner]["footprint_tokens"] += file_tokens(full)

    return skills


def is_preserved(rel_dir, name, preserve):
    """True if a skill matches any preserve entry (path prefix, glob, or name)."""
    import fnmatch
    for entry in preserve:
        e = entry.replace("\\", "/").rstrip("/")
        if rel_dir == e or rel_dir.startswith(e + "/") or name == e:
            return True
        if fnmatch.fnmatch(rel_dir, e) or fnmatch.fnmatch(name, e):
            return True
    return False


# ---------------------------------------------------------------------------
# Analysis sections
# ---------------------------------------------------------------------------

def significant_words(record):
    """Set of meaningful tokens from a skill's name and description."""
    text = record["name"].replace("-", " ") + " " + record["description"].lower()
    return {w for w in WORD_RE.findall(text) if len(w) > 2 and w not in STOPWORDS}


def analyze_overlap(skills, threshold):
    """Pairwise Jaccard similarity over significant words; return pairs >= threshold."""
    items = sorted(skills.items())
    word_sets = {rel: significant_words(rec) for rel, rec in items}
    pairs = []
    keys = [rel for rel, _ in items]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = word_sets[keys[i]], word_sets[keys[j]]
            if not a or not b:
                continue
            shared = a & b
            union = a | b
            score = len(shared) / len(union) if union else 0.0
            if score >= threshold:
                pairs.append({
                    "a": keys[i],
                    "b": keys[j],
                    "score": round(score, 2),
                    "shared_terms": sorted(shared),
                })
    return sorted(pairs, key=lambda p: p["score"], reverse=True)


def load_telemetry_skills(telemetry_file, days):
    """Return (set_of_skill_names, status, diagnostics) for usage within `days`.

    status is a STABLE machine code — "unavailable", "empty", "ok", or
    "error: ...". Counts of skipped/degraded entries live in diagnostics so the
    status string stays comparable by the caller; the report discloses them.
    """
    diag = {"malformed_ts": 0, "bad_json": 0}
    if not os.path.isfile(telemetry_file):
        return set(), "unavailable", diag

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen = set()
    parsed_any = False
    try:
        with open(telemetry_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    # A corrupt line may omit a real invocation, risking a false
                    # "unused" flag — track it so the report can disclose it.
                    diag["bad_json"] += 1
                    continue
                parsed_any = True
                skill = entry.get("skill")
                ts = entry.get("timestamp")
                if not skill:
                    continue
                if ts:
                    try:
                        when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if when.tzinfo is None:
                            when = when.replace(tzinfo=timezone.utc)
                        if when < cutoff:
                            continue
                    except ValueError:
                        # Present-but-unparseable timestamp: count the skill as
                        # seen (conservative — avoids a false "unused" flag) but
                        # track it so the report can disclose the bypassed window.
                        diag["malformed_ts"] += 1
                seen.add(skill)
    except OSError as e:
        return set(), f"error: reading telemetry: {e}", diag

    return seen, ("ok" if parsed_any else "empty"), diag


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def build_results(repo_root, cfg, days, context_window, telemetry_file, use_telemetry):
    skills = build_inventory(repo_root)
    preserve = cfg["preserve"]

    total_footprint = sum(r["footprint_tokens"] for r in skills.values())
    largest = sorted(skills.values(), key=lambda r: r["footprint_tokens"], reverse=True)

    verbose = [
        {"rel_dir": r["rel_dir"], "name": r["name"], "words": r["description_words"]}
        for r in sorted(skills.values(), key=lambda r: r["description_words"], reverse=True)
        if r["description_words"] > cfg["verbose_description_words"]
    ]

    overlap = [
        p for p in analyze_overlap(skills, cfg["overlap_threshold"])
        if not (is_preserved(p["a"], skills[p["a"]]["name"], preserve)
                and is_preserved(p["b"], skills[p["b"]]["name"], preserve))
    ]

    unused = []
    telemetry_status = "skipped"
    telemetry_diag = {"malformed_ts": 0, "bad_json": 0}
    if use_telemetry:
        seen, telemetry_status, telemetry_diag = load_telemetry_skills(telemetry_file, days)
        if telemetry_status in ("ok", "empty"):
            for rel, r in sorted(skills.items()):
                if r["name"] in seen:
                    continue
                if is_preserved(rel, r["name"], preserve):
                    continue
                unused.append({"rel_dir": rel, "name": r["name"]})

    return {
        "skill_count": len(skills),
        "context_window": context_window,
        "total_footprint_tokens": total_footprint,
        "footprint_pct": round(100.0 * total_footprint / context_window, 2) if context_window else 0.0,
        "largest_skill_tokens": largest[0]["footprint_tokens"] if largest else 0,
        "largest_skill": largest[0]["rel_dir"] if largest else None,
        "top_skills": [
            {"rel_dir": r["rel_dir"], "tokens": r["footprint_tokens"]}
            for r in largest[:5]
        ],
        "verbose_descriptions": verbose,
        "overlap_candidates": overlap,
        "unused_skills": unused,
        "telemetry_status": telemetry_status,
        "telemetry_diagnostics": telemetry_diag,
        "telemetry_window_days": days,
        "verbose_threshold_words": cfg["verbose_description_words"],
        "overlap_threshold": cfg["overlap_threshold"],
        "preserve": preserve,
    }


def render_text(res):
    out = ["# Skill Cleaner Report", "",
           "Suggest-first: every item below is advisory. Review before removing or merging.", ""]

    out += ["## 1. Budget Allocation",
            f"- Skills inventoried: **{res['skill_count']}**",
            f"- Total footprint: **{res['total_footprint_tokens']} tokens** "
            f"(~{res['footprint_pct']}% of {res['context_window']}-token context window)",
            f"- Largest single skill: {res['largest_skill']} "
            f"(~{res['largest_skill_tokens']} tokens)", ""]
    if res["top_skills"]:
        out.append("Top skills by footprint:")
        out += [f"  - {s['rel_dir']}: ~{s['tokens']} tokens" for s in res["top_skills"]]
    out.append("")

    out.append("## 2. Verbose Descriptions "
               f"(>{res['verbose_threshold_words']} words)")
    if res["verbose_descriptions"]:
        out += [f"  - {v['rel_dir']}: {v['words']} words — tighten toward the 40–80 word target"
                for v in res["verbose_descriptions"]]
    else:
        out.append("  None.")
    out.append("")

    out.append("## 3. Overlap / Merge Candidates "
               f"(Jaccard ≥ {res['overlap_threshold']} — review required)")
    if res["overlap_candidates"]:
        for p in res["overlap_candidates"]:
            out.append(f"  - {p['a']} ↔ {p['b']} (score {p['score']}); "
                       f"shared: {', '.join(p['shared_terms'])}")
    else:
        out.append("  None.")
    out.append("")

    out.append(f"## 4. Unused Skills (no invocations in {res['telemetry_window_days']} days)")
    if res["telemetry_status"] == "unavailable":
        out.append("  Telemetry unavailable — enable skill-telemetry.sh as a PreToolUse hook "
                   "to populate ~/.claude/telemetry/skill-usage.jsonl.")
    elif res["telemetry_status"] == "skipped":
        out.append("  Skipped (--no-telemetry).")
    elif res["telemetry_status"] == "empty":
        out.append("  Telemetry file present but empty — no usage to compare yet.")
    elif res["telemetry_status"].startswith("error"):
        out.append(f"  {res['telemetry_status']}")
    elif res["unused_skills"]:
        out += [f"  - {u['rel_dir']} ({u['name']})" for u in res["unused_skills"]]
    else:
        out.append("  None — every inventoried skill was invoked in the window.")

    diag = res.get("telemetry_diagnostics", {})
    notes = []
    if diag.get("malformed_ts"):
        notes.append(f"{diag['malformed_ts']} entries had unparseable timestamps "
                     "(counted as in-window)")
    if diag.get("bad_json"):
        notes.append(f"{diag['bad_json']} corrupt JSON lines were skipped")
    if notes:
        out.append(f"  Note: {'; '.join(notes)} — results may understate usage.")
    out.append("")

    if res["preserve"]:
        out.append(f"_Preserve-list ({len(res['preserve'])}): "
                   f"{', '.join(res['preserve'])} — never flagged for removal/merge._")
        out.append("")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Suggest-first maintenance analyzer for skill repositories (§10.5).")
    parser.add_argument("--root", help="Repo root to scan (default: auto-detect)")
    parser.add_argument("--days", type=int, default=None,
                        help="Telemetry window in days (default: cleaner.unused_days)")
    parser.add_argument("--context-window", type=int, default=None,
                        help="Context window size for the %% allocation figure")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--no-telemetry", action="store_true",
                        help="Skip the unused-skill section")
    parser.add_argument("--telemetry-file", default=DEFAULT_TELEMETRY_FILE,
                        help="Path to skill-usage.jsonl")
    args = parser.parse_args()

    repo_root = resolve_repo_root(args.root)
    cfg = load_cleaner_config(repo_root)
    days = args.days if args.days is not None else cfg["unused_days"]
    context_window = args.context_window if args.context_window is not None else cfg["context_window"]
    if context_window <= 0:
        raise SystemExit("ERROR: --context-window must be positive")
    if days < 0:
        raise SystemExit("ERROR: --days must be non-negative")

    res = build_results(repo_root, cfg, days, context_window,
                        args.telemetry_file, not args.no_telemetry)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(render_text(res))


if __name__ == "__main__":
    main()
