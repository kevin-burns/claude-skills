# Regional formats

CV conventions are not universal. The default workflow assumes an Anglo (US/UK)
résumé; applying its rules to a German Lebenslauf actively harms the candidate —
it strips the photo, date of birth, nationality, and signature a German recruiter
expects. **Auto-detect the format from the document; do not ask.** Once detected,
the regional rules here override the Anglo defaults in the parseability checklist
for the affected fields.

## Auto-detection (run during Step 2, on the CV itself)

### German / DACH Lebenslauf
Treat as a German-format CV if **two or more** of these hold (the title or German
body alone is enough):

- A heading or filename containing **"Lebenslauf"**.
- **German body language** — umlauts (ä/ö/ü/ß) and German section headings:
  *Berufserfahrung, Ausbildung, Kenntnisse, Sprachen, Persönliche Daten,
  Weiterbildung, Interessen*.
- A **personal-data block**: *Geburtsdatum / Geburtsort, Nationalität /
  Staatsangehörigkeit, Familienstand*.
- A **photo** placed top-right, and/or a **signature line** with *Ort, Datum* at the
  bottom.
- **Dates as MM.YYYY or DD.MM.YYYY**, and a **dates-left / details-right** tabular rhythm.
- The target employer or posting is in **DE / AT / CH** or written in German.

If detected, you already know you're inside the German regional layer — apply the
overrides below and do **not** Anglicise it. The same conventions broadly cover
Austria and German-speaking Switzerland (DACH).

## German / DACH overrides

**Keep the personal data the Anglo rules would strip.** Photo, date/place of birth,
nationality, and (optionally, fading) marital status are normal and **not** treated
as discriminatory in Germany. A signature with place and date at the bottom is
expected in traditional sectors. Keep them.

**The two-layer rule (why the photo is safe).** An ATS ignores images entirely —
the photo neither helps nor breaks parsing. The human reviewer who sees the ranked
application *expects* it in traditional sectors. So a photo is parser-neutral and
human-positive: keep it as an inline image top-right, ensure it contains no
essential text, and keep name and contact details as live text near the top.

**Sector nuance for the photo/signature:**
- *Traditional* (Mittelstand, finance, law, public sector, manufacturing): include
  photo, signature, and fuller personal data.
- *Tech, startups, international, English-language roles*: photo is increasingly
  dropped under EU anti-discrimination norms and some ATS strip it; signature
  optional. When in doubt for these, omit the photo.

**Layout — same parser-safety as everywhere.** The classic *tabellarisch* dates-left
/ details-right look is fine **only when built with tab stops**, because it then
extracts as a single stream. Real two-column tables, sidebars, text boxes, skill
bars, and icons still break parsing — do not use them.

**File & dates.** PDF is the German standard (selectable text, not a flattened
image); name it `Lebenslauf_Vorname_Nachname.pdf`. Use one date format (MM.YYYY)
throughout. Account for **every** timeline gap — German recruiters expect no
unexplained gaps; label them (*Elternzeit, Weiterbildung, Sabbatical*).

**Language & keywords.** Write in the posting's language — German CV for a German
posting, English for an English one — and do not blend; keep separate DE and EN
versions. For German postings, mirror the posting's *Aufgaben* (tasks) and
*Anforderungen* (requirements) terms; the parser must handle German compound words
and umlauts, so use the exact posting spellings.

**Section order.** Persönliche Daten → Berufserfahrung → Ausbildung →
Kenntnisse/Skills → Sprachen (with CEFR levels) → Weiterbildung/Zertifikate →
Interessen → *Ort, Datum, Unterschrift*. Length 1–2 pages (3 for senior).

**It's a set, not a CV alone.** A German *Bewerbung* is Anschreiben (cover letter)
+ Lebenslauf + Anlagen (Arbeitszeugnisse / certificates). Flag to the candidate that
the Lebenslauf is one part; the Anschreiben and Arbeitszeugnisse carry real weight.

**De-slop in German.** The de-slop principles in `deslop-cv.md` are
language-agnostic (cut empty boosters, keep referential keywords, drop `-ing`/
participle inflation), but its word list is English. Apply the principles, with the
German starter list below. Treat it as **hints, not a blocklist** — there is no
canonical open-source German AI-slop list, and research on the English equivalents
shows single words are weak signals (many are ordinary writing). Flag a term only
when it's an *empty* booster, never when it's doing real work; the keyword guard
applies in German exactly as in English.

German CV slop to watch for:
- *Boosters:* ergebnisorientiert, leidenschaftlich, nachweisliche Erfolgsbilanz,
  ganzheitlich, dynamisch, innovativ, zukunftsweisend, hochmotiviert, Synergien,
  präzise, sauber, umfassend — replace with the concrete fact.
- *Stock openers/closers:* "In der heutigen Zeit/Welt…", "Lassen Sie uns…",
  "Tauchen Sie ein in…", "Zusammenfassend lässt sich sagen…", "Es ist jedoch wichtig
  zu beachten, dass…", "Insgesamt…" — cut and start with the substance.
- *The "nicht nur…, sondern auch…" construction* used as filler parallelism.
- *Filler auxiliaries* (werden/können/haben) padding bullets — prefer a direct verb.
- *Overused connectors* "zudem"/"ferner" stacked as transitions.
- *Mechanics:* unnecessary hyphens in compound adjectives, and uniform sentence/
  paragraph length — same tells as in English.

## Other regions (brief)

- **Europass** (EU standard template): structured and widely parseable, but its
  default two-column variants can scramble — prefer the single-column export and the
  same parser-safety rules.
- **General principle for any region:** detect the local format, keep the
  human-expected conventions of that market, and keep them out of the parser's way
  (live text near the top, images carrying no essential text, single-stream layout).
  When the local convention and parser-safety genuinely conflict, satisfy the parser
  for machine-read fields and the human for presentation fields — that's the
  two-layer rule generalised.
