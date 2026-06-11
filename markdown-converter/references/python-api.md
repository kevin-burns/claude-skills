# markitdown Python API

Use the CLI (see SKILL.md) for one-off conversions. Reach for the Python API
when you need something the CLI doesn't expose: LLM-generated image
descriptions, converting in-memory byte streams, or Azure Content Understanding
custom analyzers.

Install with the extras you need, e.g. `uv pip install 'markitdown[all]'`.

## Basic conversion

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False)
result = md.convert("report.xlsx")
print(result.text_content)
```

## Convert methods (narrowest → broadest)

- `convert_stream(stream, ...)` — a binary byte stream (give a `stream_info`
  hint for extension/MIME when the bytes alone aren't enough to identify type).
- `convert_local(path)` — local files only.
- `convert_response(response)` — an HTTP response object.
- `convert(source)` — the catch-all: handles file paths, URIs, and streams.

## LLM image descriptions

Only available through the Python API — there is no CLI flag for this. Pass an
OpenAI-compatible client; markitdown asks the model to describe images (in image
files and inside PPTX).

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(
    llm_client=client,
    llm_model="gpt-4o",
    llm_prompt="Describe this image for a document index.",  # optional
)
result = md.convert("diagram.jpg")
print(result.text_content)
```

## Azure Document Intelligence

```python
md = MarkItDown(docintel_endpoint="https://<resource>.cognitiveservices.azure.com/")
result = md.convert("scan.pdf")
```

## Azure Content Understanding

Supports prebuilt analyzers and custom field extraction. With a custom analyzer
the result is YAML front matter followed by Markdown. Use `cu_file_types` to
restrict which inputs are routed to the service (controls API billing).

```python
md = MarkItDown(cu_endpoint="https://<resource>.cognitiveservices.azure.com/")
result = md.convert("report.pdf")

# Custom analyzer for structured extraction:
md = MarkItDown(
    cu_endpoint="https://<resource>.cognitiveservices.azure.com/",
    cu_analyzer_id="invoice-analyzer",
)
result = md.convert("invoice.pdf")  # YAML front matter + Markdown
```

## Notes

- Requires Python 3.10+.
- Format support depends on the installed extras, same as the CLI — install
  `markitdown[all]` or the specific extra (`[pdf]`, `[docx]`, …).
- Source of truth: https://github.com/microsoft/markitdown
