#!/usr/bin/env bash
set -euo pipefail

# Skill Governance Installer
# https://github.com/dtsong/skill-governance
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
#     | bash -s -- --init
#
#   curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
#     | bash -s -- --upgrade --version v1.3.0
#
#   curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
#     | bash -s -- --user-config

REPO="dtsong/skill-governance"
DEFAULT_VERSION="v1.3.0"
GITHUB_URL="https://github.com/${REPO}"

# --- Helpers ---

log()  { printf '[governance] %s\n' "$*"; }
warn() { printf '[governance] WARNING: %s\n' "$*" >&2; }
die()  { printf '[governance] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Skill Governance Installer

Usage:
  install.sh --init    [--version VERSION]   Bootstrap governance in a new suite
  install.sh --upgrade [--version VERSION]   Upgrade governance in an existing suite
  install.sh --user-config                   Update ~/.claude/CLAUDE.md governance section

Options:
  --version VERSION    Git tag to install (default: v1.3.0)
  --suite-dir DIR      Target suite directory (default: current directory)
  --help               Show this help message

EOF
  exit 0
}

# --- Argument parsing ---

MODE=""
VERSION="${DEFAULT_VERSION}"
SUITE_DIR="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --init)        MODE="init";        shift ;;
    --upgrade)     MODE="upgrade";     shift ;;
    --user-config) MODE="user-config"; shift ;;
    --version)     VERSION="$2";       shift 2 ;;
    --suite-dir)   SUITE_DIR="$2";     shift 2 ;;
    --help|-h)     usage ;;
    *)             die "Unknown option: $1" ;;
  esac
done

[[ -n "$MODE" ]] || die "No mode specified. Use --init, --upgrade, or --user-config."

# --- Download release tarball ---

download_release() {
  local version="$1"
  local tmpdir
  tmpdir=$(mktemp -d)

  local tarball_url="${GITHUB_URL}/archive/refs/tags/${version}.tar.gz"
  log "Downloading ${version} from ${tarball_url}..."

  if ! curl -sSL --fail -o "${tmpdir}/release.tar.gz" "$tarball_url"; then
    rm -rf "$tmpdir"
    die "Failed to download release ${version}. Check the version tag exists."
  fi

  tar -xzf "${tmpdir}/release.tar.gz" -C "$tmpdir" 2>/dev/null || {
    rm -rf "$tmpdir"
    die "Failed to extract release tarball."
  }

  # Find the extracted directory (github names it skill-governance-<tag>)
  local extracted
  extracted=$(find "$tmpdir" -maxdepth 1 -type d -name "skill-governance-*" | head -1)
  if [[ -z "$extracted" ]]; then
    rm -rf "$tmpdir"
    die "Could not find extracted release directory."
  fi

  echo "$extracted"
}

# --- Config merge ---

merge_json_config() {
  local src="$1"
  local dst="$2"
  local filename
  filename=$(basename "$dst")

  if [[ ! -f "$dst" ]]; then
    cp "$src" "$dst"
    log "  Created ${filename}"
    return
  fi

  # Merge strategy: keep suite-specific overrides, update defaults
  if command -v python3 &>/dev/null; then
    python3 - "$src" "$dst" <<'PYEOF'
import json, sys

src_path, dst_path = sys.argv[1], sys.argv[2]

with open(src_path) as f:
    src = json.load(f)
with open(dst_path) as f:
    dst = json.load(f)

# Preserve suite-specific overrides
suite_overrides = dst.get("overrides", {})

# Update all default keys from source
for key, value in src.items():
    if key != "overrides":
        dst[key] = value

# Merge overrides: keep suite entries, add any new governance defaults
governance_overrides = src.get("overrides", {})
for key, value in governance_overrides.items():
    if key not in suite_overrides:
        suite_overrides[key] = value
dst["overrides"] = suite_overrides

with open(dst_path, "w") as f:
    json.dump(dst, f, indent=2)
    f.write("\n")
PYEOF
    log "  Merged ${filename} (preserved suite overrides)"
  else
    warn "python3 not found — cannot merge ${filename}. Skipping config merge."
  fi
}

merge_yaml_config() {
  local src="$1"
  local dst="$2"
  local filename
  filename=$(basename "$dst")

  if [[ ! -f "$dst" ]]; then
    cp "$src" "$dst"
    log "  Created ${filename}"
    return
  fi

  # For YAML: preserve suite overrides section, replace everything else
  if command -v python3 &>/dev/null && python3 -c "import yaml" 2>/dev/null; then
    python3 - "$src" "$dst" <<'PYEOF'
import yaml, sys

src_path, dst_path = sys.argv[1], sys.argv[2]

with open(src_path) as f:
    src = yaml.safe_load(f) or {}
with open(dst_path) as f:
    dst = yaml.safe_load(f) or {}

# Preserve suite-specific overrides
suite_overrides = dst.get("overrides", {})

# Update everything from source
dst.update(src)

# Restore suite overrides
if suite_overrides:
    dst["overrides"] = suite_overrides

with open(dst_path, "w") as f:
    yaml.dump(dst, f, default_flow_style=False, sort_keys=False)
PYEOF
    log "  Merged ${filename} (preserved suite overrides)"
  else
    # Fallback: just copy if pyyaml not available
    cp "$src" "$dst"
    log "  Replaced ${filename} (pyyaml not available for merge)"
  fi
}

# --- CLAUDE.md governance section ---

GOVERNANCE_MARKER_START="## Skill Governance Directive"
GOVERNANCE_MARKER_END="<!-- /skill-governance -->"

update_claude_md() {
  local claude_md="$1"
  local directive_file="$2"

  if [[ ! -f "$directive_file" ]]; then
    warn "Directive file not found: ${directive_file}"
    return
  fi

  local directive_content
  directive_content=$(cat "$directive_file")

  # Wrap directive in markers for future updates
  local block
  block=$(cat <<BLOCK
${GOVERNANCE_MARKER_START}

${directive_content}

${GOVERNANCE_MARKER_END}
BLOCK
)

  if [[ ! -f "$claude_md" ]]; then
    echo "$block" > "$claude_md"
    log "  Created ${claude_md} with governance directive"
    return
  fi

  # Check if governance section already exists
  if grep -q "$GOVERNANCE_MARKER_START" "$claude_md"; then
    # Replace existing section
    local tmpfile
    tmpfile=$(mktemp)
    python3 - "$claude_md" "$block" <<'PYEOF'
import sys

claude_md_path = sys.argv[1]
new_block = sys.argv[2]

with open(claude_md_path) as f:
    content = f.read()

start_marker = "## Skill Governance Directive"
end_marker = "<!-- /skill-governance -->"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx >= 0 and end_idx >= 0:
    end_idx += len(end_marker)
    content = content[:start_idx] + new_block + content[end_idx:]
elif start_idx >= 0:
    # No end marker — replace from start to next ## heading or EOF
    next_heading = content.find("\n## ", start_idx + 1)
    if next_heading >= 0:
        content = content[:start_idx] + new_block + "\n\n" + content[next_heading:]
    else:
        content = content[:start_idx] + new_block
else:
    content = content.rstrip() + "\n\n" + new_block + "\n"

with open(claude_md_path, "w") as f:
    f.write(content)
PYEOF
    log "  Updated governance section in ${claude_md}"
  else
    # Append governance section
    printf '\n\n%s\n' "$block" >> "$claude_md"
    log "  Appended governance directive to ${claude_md}"
  fi
}

# --- Install pipeline files ---

install_pipeline() {
  local src_root="$1"
  local dst_root="$2"

  log "Installing pipeline files..."

  # Create directory structure
  mkdir -p "$dst_root/pipeline/hooks"
  mkdir -p "$dst_root/pipeline/scripts"
  mkdir -p "$dst_root/pipeline/config"
  mkdir -p "$dst_root/pipeline/specs"
  mkdir -p "$dst_root/pipeline/templates"

  # Copy hooks (always replace — these are shared infrastructure)
  cp "$src_root/pipeline/hooks/"*.py "$dst_root/pipeline/hooks/" 2>/dev/null || true
  chmod +x "$dst_root/pipeline/hooks/"*.py 2>/dev/null || true
  log "  Installed hooks"

  # Copy scripts (always replace)
  cp "$src_root/pipeline/scripts/"* "$dst_root/pipeline/scripts/" 2>/dev/null || true
  chmod +x "$dst_root/pipeline/scripts/"*.sh 2>/dev/null || true
  chmod +x "$dst_root/pipeline/scripts/"*.py 2>/dev/null || true
  log "  Installed scripts"

  # Copy specs (always replace)
  cp "$src_root/specs/"*.md "$dst_root/pipeline/specs/" 2>/dev/null || true
  log "  Installed specs"

  # Copy templates (always replace)
  cp -r "$src_root/pipeline/templates/"* "$dst_root/pipeline/templates/" 2>/dev/null || true
  log "  Installed templates"

  # Copy shell helpers (always replace)
  cp "$src_root/pipeline/shell-helpers.sh" "$dst_root/pipeline/" 2>/dev/null || true
  chmod +x "$dst_root/pipeline/shell-helpers.sh"
  log "  Installed shell-helpers.sh"

  # Copy pre-commit config template
  if [[ ! -f "$dst_root/.pre-commit-config.yaml" ]]; then
    cp "$src_root/pipeline/pre-commit-config.yaml" "$dst_root/.pre-commit-config.yaml"
    log "  Created .pre-commit-config.yaml"
  else
    log "  Skipped .pre-commit-config.yaml (already exists)"
  fi

  # Merge config files (preserve suite overrides)
  merge_json_config "$src_root/pipeline/config/budgets.json" "$dst_root/pipeline/config/budgets.json"
  merge_json_config "$src_root/pipeline/config/security-suppressions.json" "$dst_root/pipeline/config/security-suppressions.json"
  merge_yaml_config "$src_root/pipeline/config/model-routing.yaml" "$dst_root/pipeline/config/model-routing.yaml"

  # Copy GitHub Actions workflow templates
  if [[ -d "$src_root/pipeline/workflows" ]]; then
    mkdir -p "$dst_root/.github/workflows"
    cp "$src_root/pipeline/workflows/"*.yml "$dst_root/.github/workflows/" 2>/dev/null || true
    log "  Installed GitHub Actions workflows"
  fi
}

# --- Mode: init ---

do_init() {
  log "Initializing governance ${VERSION} in ${SUITE_DIR}..."

  if [[ -f "${SUITE_DIR}/.governance-version" ]]; then
    local existing
    existing=$(cat "${SUITE_DIR}/.governance-version")
    warn "Governance already initialized (${existing}). Use --upgrade instead."
    die "Aborting --init. Use --upgrade to update."
  fi

  local src_root
  src_root=$(download_release "$VERSION")

  install_pipeline "$src_root" "$SUITE_DIR"

  # Update CLAUDE.md
  update_claude_md "${SUITE_DIR}/CLAUDE.md" "${src_root}/directive/SKILL-GOVERNANCE-DIRECTIVE.md"

  # Write version tracker
  echo "$VERSION" > "${SUITE_DIR}/.governance-version"
  log "  Wrote .governance-version (${VERSION})"

  # Cleanup
  rm -rf "$(dirname "$src_root")"

  log "Governance ${VERSION} initialized successfully."
  log ""
  log "Next steps:"
  log "  pip install pre-commit pyyaml"
  log "  pre-commit install"
  log "  pre-commit install --hook-type commit-msg"
  log "  source pipeline/shell-helpers.sh"
  log ""

  # Run compliance check if pre-commit is available
  if command -v pre-commit &>/dev/null; then
    log "Running compliance check..."
    pre-commit run --all-files || true
  else
    log "Install pre-commit to run compliance checks: pip install pre-commit"
  fi
}

# --- Mode: upgrade ---

do_upgrade() {
  log "Upgrading governance to ${VERSION} in ${SUITE_DIR}..."

  if [[ ! -d "${SUITE_DIR}/pipeline" ]]; then
    warn "No pipeline/ directory found. Use --init for first-time setup."
    die "Aborting --upgrade."
  fi

  local old_version="unknown"
  if [[ -f "${SUITE_DIR}/.governance-version" ]]; then
    old_version=$(cat "${SUITE_DIR}/.governance-version")
  fi
  log "  Current version: ${old_version}"
  log "  Target version:  ${VERSION}"

  local src_root
  src_root=$(download_release "$VERSION")

  install_pipeline "$src_root" "$SUITE_DIR"

  # Update CLAUDE.md
  update_claude_md "${SUITE_DIR}/CLAUDE.md" "${src_root}/directive/SKILL-GOVERNANCE-DIRECTIVE.md"

  # Update version tracker
  echo "$VERSION" > "${SUITE_DIR}/.governance-version"
  log "  Updated .governance-version (${old_version} -> ${VERSION})"

  # Cleanup
  rm -rf "$(dirname "$src_root")"

  log "Governance upgraded to ${VERSION} successfully."

  # Run compliance check if pre-commit is available
  if command -v pre-commit &>/dev/null; then
    log "Running compliance check..."
    pre-commit run --all-files || true
  fi
}

# --- Mode: user-config ---

do_user_config() {
  log "Updating user-level governance config..."

  local claude_dir="${HOME}/.claude"
  local claude_md="${claude_dir}/CLAUDE.md"

  mkdir -p "$claude_dir"

  # Minimal governance directive for user-level config
  local directive
  directive=$(cat <<'DIRECTIVE'
## Skill Governance Directive

All skills in this repository must comply with the Skill Governance Specification.

### Token Budgets (Hard Limits)

- Coordinator SKILL.md: ≤800 tokens (~600 words)
- Specialist / Standalone SKILL.md: ≤2,000 tokens (~1,500 words)
- Reference files: ≤1,500 tokens (~1,100 words)
- Maximum simultaneous context load: ≤5,000 tokens

### Architecture Rules

- Coordinators contain ONLY: classification logic, skill registry, load directive, handoff protocol
- Load one specialist at a time — never pre-load multiple specialists
- Checklists >10 items go in reference files, loaded conditionally
- Eval cases and templates live outside skill directories
- No cross-references between specialist skills — use handoff protocol

### Writing Rules

- Procedure steps use imperative sentences — no explanatory prose
- Decision points as inline conditionals — no nested sub-sections
- One compact output example per skill — no redundant schema descriptions
- Reference files are pure content — no preamble or meta-instructions

### Enforcement

Pre-commit hooks validate: token budgets, frontmatter, reference integrity,
cross-skill isolation, and suite context load ceiling.

Run `pre-commit run --all-files` to check compliance manually.

Full spec: `pipeline/specs/SKILL-GOVERNANCE-SPEC.md`

<!-- /skill-governance -->
DIRECTIVE
)

  if [[ ! -f "$claude_md" ]]; then
    echo "$directive" > "$claude_md"
    log "  Created ${claude_md} with governance directive"
  elif grep -q "$GOVERNANCE_MARKER_START" "$claude_md"; then
    # Use a temp file for the replacement
    python3 - "$claude_md" "$directive" <<'PYEOF'
import sys

path = sys.argv[1]
new_block = sys.argv[2]

with open(path) as f:
    content = f.read()

start = "## Skill Governance Directive"
end = "<!-- /skill-governance -->"

si = content.find(start)
ei = content.find(end)

if si >= 0 and ei >= 0:
    ei += len(end)
    content = content[:si] + new_block + content[ei:]
elif si >= 0:
    nh = content.find("\n## ", si + 1)
    if nh >= 0:
        content = content[:si] + new_block + "\n\n" + content[nh:]
    else:
        content = content[:si] + new_block

with open(path, "w") as f:
    f.write(content)
PYEOF
    log "  Updated governance section in ${claude_md}"
  else
    printf '\n\n%s\n' "$directive" >> "$claude_md"
    log "  Appended governance directive to ${claude_md}"
  fi

  log "User config updated."
}

# --- Main ---

case "$MODE" in
  init)        do_init ;;
  upgrade)     do_upgrade ;;
  user-config) do_user_config ;;
  *)           die "Unknown mode: $MODE" ;;
esac
