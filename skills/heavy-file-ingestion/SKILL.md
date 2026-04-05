---
name: heavy-file-ingestion
description: >
  Use when a user asks to read, analyze, summarize, or extract from a heavyweight
  file (PDF, DOCX, PPTX, XLSX, CSV, TSV). Converts the file into markdown or CSV
  first, generates a lightweight index, and only spends model tokens on the
  compressed artifact. Trigger on "read this PDF", "look through this spreadsheet",
  "summarize this deck", or any time raw file ingestion would waste tokens.
  Do NOT trigger for plain text, markdown, JSON, YAML, or source code files —
  those are cheap to read directly.
---

# Heavy File Ingestion

## Problem

Agents waste context and money reading heavyweight files raw. Convert first, reason second.

## Trigger Conditions

- User asks to read or analyze a PDF, slide deck, spreadsheet, or word-processing file
- File is large, structured, or binary enough that raw ingestion is a bad trade
- User wants a markdown working copy, CSV extraction, or a quick map before analysis

## Core Policy

1. **Convert before reading.** Do not dump raw heavyweight files into model context if a deterministic converter can create a cheaper artifact.
2. **Index before reasoning.** Read the generated `index.md` first — it tells you what is in the file, how clean the extraction was, and whether escalation is justified.
3. **Match converter to file type.**
   - PDFs and documents → markdown artifact
   - Presentations → markdown slide outline
   - Spreadsheets → CSV per sheet plus markdown manifest
4. **Escalate by cost tier, not instinct.**
   - Tier 1: deterministic converter + index
   - Tier 2: cheap model on extracted artifact only if quality flags say the deterministic pass lost structure
   - Tier 3: expensive model only after the file has been compressed into markdown, CSV, or a sampled subset

## Process

Step 1: Identify file path, extension, and rough size.

Step 2: Run the converter — do not read the original file directly.

```bash
uv run \
  --with pdfplumber \
  --with python-docx \
  --with python-pptx \
  --with openpyxl \
  python scripts/convert_heavy_file.py /absolute/path/to/file.ext
```

- If `markitdown` is installed and preferred for PDF/DOCX, add `--prefer markitdown`.
- Output lands in `<source>.ob1/` by default.

Step 3: Read the generated `index.md` before any converted artifact.

Step 4: Use the index to decide the cheapest next action:
  - `read_extracted_artifact` → read the markdown or CSV and continue
  - `install_dependency_and_retry` → install the missing dependency and rerun
  - `cheap_model_or_stronger_converter` → retry with a better converter or use a cheaper model on the extracted artifact only

Step 5: Only escalate to a stronger model after the file has already been compressed.

## Client Rules

- Prefer deterministic scripts over model-based conversion.
- Save converted artifacts next to the source file and work from those.
- For spreadsheets, use the generated per-sheet CSV files instead of reasoning over workbook internals.
- For PDFs, treat scan detection and low-density warnings as routing signals, not reasons to read the original raw.

## Gotchas

- The converter needs Python 3.10+ and the listed dependencies. If `uv` is unavailable, fall back to `pip install` then run directly.
- Scanned PDFs produce near-empty markdown — the `scanned_pdf_suspected` quality flag tells you this happened. Do not re-read the original; escalate to Docling or a vision model on the extracted artifact.
- Large XLSX files with many sheets produce one CSV per sheet. Read the `workbook.md` manifest first to decide which sheets matter.
- The `--prefer markitdown` flag only affects PDF and DOCX. Spreadsheets and presentations always use native extractors.
- Conversion artifacts are written next to the source file. If the source is read-only or on a network mount, pass `--output-dir` to redirect.

## References

| File | Load When | Contains |
|------|-----------|----------|
| `references/open-source-stack.md` | Choosing a fallback converter or explaining tool choices | Rationale for MarkItDown, Docling, pdfplumber, openpyxl selection |
