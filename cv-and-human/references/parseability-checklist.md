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

## Diagnose from the extraction itself (do this first)

When you read the CV you extract its text — and **that extraction is exactly what an
ATS sees.** Don't just look at the visual layout; read the *order the text comes
out*. If the contact block, skills, or a sidebar appear **before the name**, or
sections interleave, that is a **confirmed live parse failure**, not a hypothetical
one — flag it as a blocker. This single check catches most two-column and sidebar
designs immediately, because they extract out of reading order.

## Layout

- **Single column.** Multi-column layouts are the number-one parse-breaker:
  extractors read left-to-right across the whole page and interleave the columns
  into nonsense. One column, top to bottom.
- **No text inside images or text boxes.** Anything rendered as an image (a skills
  graphic, a header logo with your name in it) is invisible to text extraction.
  Name, contact details, and all content must be live text.
- **No graphical template furniture.** Modern designed templates hide parse-killers
  in plain sight: **language/skill proficiency bars**, **boxed or pill-shaped tag
  elements** (e.g. industry tags), **decorative section numbers** (01 / 02 / 03),
  and icon glyphs. Convert each to plain text — a proficiency bar becomes
  "German (B2)", a tag row becomes a comma-separated list.
- **Avoid tables for layout.** Some parsers flatten table cells in the wrong order.
  If a table is unavoidable (e.g. a simple skills grid), keep it a single simple
  grid with one value per cell and no merged cells. When in doubt, use a plain
  comma-separated list instead.
- **No headers/footers for essential info.** Some parsers drop header/footer
  regions. Keep name, email, and phone in the main body, near the top.
- **No unusual glyphs as bullets or separators.** Use standard bullet characters;
  avoid decorative dingbats and icon fonts that may extract as garbage.

**Keep both versions — don't make the candidate destroy a good design.** If they
have a polished multi-column/designed PDF, the fix is *not* to discard it. Produce a
**single-column parser-safe version for ATS and online forms**, and tell them to
keep the **designed version for human-facing channels** (direct email, LinkedIn)
where a person reads it and the layout helps. Lead with the parser-safe one for
machines.

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
