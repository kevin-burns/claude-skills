# Parseability checklist

Apply this during Step 2 (audit) and Step 5 (rewrite). The goal: the CV extracts
to clean, correctly-ordered plain text, because every ATS — keyword or LLM —
parses to text before it does anything else. A strong CV that parses badly scores
worse than a mediocre one that parses cleanly.

**Regional override:** the rules below assume an Anglo (US/UK) résumé, which omits
photo, date of birth, nationality, and signature. If a regional format is detected
(e.g. a German/DACH Lebenslauf), `references/regional-formats.md` **overrides** this
file for those personal-data fields — they are deliberately included there. Detect
the format first (Step 2), then apply the right layer.

## Layout

- **Single column.** Multi-column layouts are the number-one parse-breaker:
  extractors read left-to-right across the whole page and interleave the columns
  into nonsense. One column, top to bottom.
- **No text inside images or text boxes.** Anything rendered as an image (a skills
  graphic, a header logo with your name in it) is invisible to text extraction.
  Name, contact details, and all content must be live text.
- **Avoid tables for layout.** Some parsers flatten table cells in the wrong order.
  If a table is unavoidable (e.g. a simple skills grid), keep it a single simple
  grid with one value per cell and no merged cells. When in doubt, use a plain
  comma-separated list instead.
- **No headers/footers for essential info.** Some parsers drop header/footer
  regions. Keep name, email, and phone in the main body, near the top.
- **No unusual glyphs as bullets or separators.** Use standard bullet characters;
  avoid decorative dingbats and icon fonts that may extract as garbage.

## Sections and headings

- Use **conventional, literal headings** the parser expects to find:
  `Experience` (or `Work Experience`), `Education`, `Skills`, `Projects`,
  `Certifications`. Creative headings like "Where I've Made an Impact" can prevent
  a parser from recognising the section.
- Put sections in a **standard order**: contact → summary (optional) → skills →
  experience → projects → education → extras.
- One clear **job entry pattern**: Title — Company — Location — Dates, each
  consistently formatted, dates in a consistent form (e.g. `MMM YYYY – MMM YYYY`).

## Content formatting

- **Dates consistent and machine-readable.** Pick one format and use it
  everywhere. Avoid date ranges expressed only in prose.
- **Spell out then abbreviate** on first use where the JD might use either form:
  e.g. "Continuous Integration / Continuous Deployment (CI/CD)". This covers both
  the literal acronym match and the spelled-out match.
- **Skills as plain delimited lists**, grouped sensibly (Languages, Cloud,
  DevOps, etc.), each skill as the JD writes it.
- **Standard file type.** Submit `.docx` or text-based `.pdf` (not a scanned/image
  PDF). If exporting to PDF, ensure the text layer is selectable, not flattened.

## Quick audit questions (run mentally on every CV)

1. If I copy-paste the whole document into a plain text editor, does it come out in
   the right reading order and lose nothing important?
2. Is any name/contact/skill information living inside an image, text box, header,
   or footer?
3. Are the section headings ones a parser would recognise literally?
4. Are dates and job entries formatted consistently?

If the answer to (1) is "no" or to (2) is "yes", fix that before anything else.
