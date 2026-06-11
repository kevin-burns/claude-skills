---
name: markdown-converter
description: Convert documents and files to Markdown using markitdown. Use when converting PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx, .xls), HTML, CSV, JSON, XML, images (with EXIF/OCR), audio (with transcription), ZIP archives, YouTube URLs, Outlook (.msg), or EPubs to Markdown format for LLM processing or text analysis.
license: MIT
---

# Markdown Converter

Convert files to Markdown using `uvx markitdown` — no manual install required.

## Choosing the invocation (read this first)

markitdown ships format support as **optional extras**. A bare `markitdown`
install only handles HTML, plain text, CSV, JSON, and XML. PDF, Office files,
audio, YouTube, and Outlook each need an extra, so you must request them in the
`uvx` call — otherwise the run fails with a missing-dependency error.

```bash
# All formats, simplest — use this unless you have a reason not to:
uvx 'markitdown[all]' input.pdf

# Lighter: pull only the extra you need (faster first run, smaller cache).
# With a single extra the command name no longer matches the package spec,
# so name it explicitly with --from:
uvx --from 'markitdown[pdf]'  markitdown input.pdf
uvx --from 'markitdown[docx]' markitdown report.docx -o report.md
```

Available extras: `pptx`, `docx`, `xlsx`, `xls`, `pdf`, `outlook`,
`audio-transcription`, `youtube-transcription`, `az-doc-intel`,
`az-content-understanding`, and `all`.

## Basic Usage

```bash
# To stdout
uvx 'markitdown[all]' input.pdf

# To a file
uvx 'markitdown[all]' input.pdf -o output.md
uvx 'markitdown[all]' input.docx > output.md

# From stdin — give a type hint since there's no filename to sniff
cat input.pdf | uvx 'markitdown[all]' -x .pdf > output.md
```

## Supported Formats

- **Documents**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx, .xls)
- **Web/Data**: HTML, CSV, JSON, XML
- **Media**: Images (EXIF + OCR), Audio (EXIF + transcription)
- **Mail**: Outlook (.msg)
- **Other**: ZIP (iterates contents), YouTube URLs, EPub

## Options

```bash
-o, --output OUTPUT     # Output file (default: stdout)
-x, --extension EXT     # Hint file extension (for stdin), e.g. .pdf
-m, --mime-type MIME    # Hint MIME type
-c, --charset CHARSET   # Hint charset, e.g. UTF-8
--keep-data-uris        # Keep base64 images in output (truncated by default)
-p, --use-plugins       # Enable 3rd-party plugins
--list-plugins          # List installed plugins
-d, --use-docintel      # Use Azure Document Intelligence (requires -e)
-e, --endpoint URL      # Document Intelligence endpoint
--use-cu                # Use Azure Content Understanding (requires --cu-endpoint)
--cu-endpoint URL       # Content Understanding endpoint
--cu-analyzer ID        # Content Understanding analyzer (auto-selected if omitted)
--cu-file-types LIST    # Comma-separated types to route to Content Understanding
-v, --version           # Print version
```

`-d` and `--use-cu` are mutually exclusive — pick one cloud path, or neither for
fully offline conversion.

## Examples

```bash
# Word document
uvx 'markitdown[all]' report.docx -o report.md

# Excel spreadsheet
uvx 'markitdown[all]' data.xlsx > data.md

# PowerPoint presentation
uvx 'markitdown[all]' slides.pptx -o slides.md

# Keep embedded images (e.g. for downstream OCR) instead of truncating them
uvx 'markitdown[all]' brochure.pdf --keep-data-uris -o brochure.md

# Scanned/complex PDF via Azure Document Intelligence
uvx 'markitdown[all]' scan.pdf -d -e "https://your-resource.cognitiveservices.azure.com/"
```

## Notes

- Output preserves document structure: headings, tables, lists, links.
- First run resolves and caches dependencies; later runs are faster. `[all]`
  caches more than a single extra.
- Requires Python 3.10+; `uvx` provisions a suitable interpreter automatically.
- For scanned or layout-heavy PDFs where offline extraction is poor, use `-d`
  with Azure Document Intelligence.
- Discover plugins by searching GitHub for the `#markitdown-plugin` topic.

## Python API

For programmatic use — LLM-generated image descriptions, byte-stream
conversion, or Azure Content Understanding analyzers — markitdown exposes a
Python API beyond what the CLI covers. See `references/python-api.md`.

## Provenance

This skill is a thin wrapper around **[markitdown](https://github.com/microsoft/markitdown)** (© Microsoft, MIT licensed), invoked via `uvx`. markitdown does the actual conversion; this skill documents the workflow and is not affiliated with Microsoft. The optional `-d` / `--use-cu` paths use Azure services, which require your own Azure resource and credentials.
