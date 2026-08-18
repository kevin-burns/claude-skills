# Provenance — clear-and-human

Sources, citations and the reasoning behind what this skill measures. Kept out of
`SKILL.md` deliberately: none of it changes what the skill does at runtime, and it was
loaded on every invocation for nothing.

Measured before moving (`evals/ablation`, arm G, 2026-08-18): removing it changed nothing
the instrument could see. Between-arm agreement sat at or above the within-arm noise floor
on three of four cases, gaps -0.009 / +0.000 / -0.008 / +0.017. The one guardrail inside
this section — the paragraph on what is deliberately excluded and why — stayed in
`SKILL.md`, because it stops a future agent reaching for an AI-detector score or
burstiness, and that is a runtime behaviour rather than an attribution.

---

Merged and adapted (all MIT / public domain):
- `the-humanizer.md` — channel detection, scoring rubric, structured report (user-supplied from reddit).
- `blader/humanizer` (MIT) — soul/voice section and the self-audit loop.
- `softaworks/agent-toolkit/writing-clearly-and-concisely` (MIT; orig. @joshuadavidthomas) — Strunk layer.
- *The Elements of Style*, Strunk 1918 (public domain).

The two scripts under `scripts/` measure rather than judge — they print a rate and the source
behind it, never a score or a threshold to write toward. Their features come from the
authorship and register literature, not from AI-detection tooling:

- Biber, D. (1988), *Variation Across Speech and Writing*, Cambridge University Press — the
  involved/informational dimension, from which contractions (.90), second person (.86),
  negation (.78), demonstratives (.76), first person (.74), word length (−.58) and
  type/token ratio (−.54) are taken.
- Herbold, Hautli-Janisz, Heuer, Kikteva & Trautsch (2023), *Scientific Reports* 13:18617 —
  nominalisation, counted by suffix rather than parsed, as they did.
- Pavlick & Tetreault (2016), *TACL* 4, 61–74 — contraction expansion measured as a discrete
  formalising edit.
- Bradner, S. (1997), "Key words for use in RFCs to Indicate Requirement Levels", BCP 14,
  RFC 2119 — the requirement group of `fidelity_check.py`'s claim-word list (must, shall,
  should, may, required, recommended, optional). Borrowed as a word list only: RFC 8174
  (Leiba, B., 2017) confines the defined meanings to the uppercase forms, and the script
  matches case-insensitively over ordinary prose. The other three groups — ranking, scope
  and relation — are assembled by judgement and say so in the source.

Two later studies test Biber's framework on LLM output directly, and both bear on this
skill's design:

- Milička, J., Marklová, A., & Cvrček, V. (2025), "Benchmark of stylistic variation in
  LLM-generated texts", arXiv:2509.10179 — Biber's multidimensional analysis over
  **AI-Brown**, a corpus built to parallel BE-21 contemporary British English, across many
  models including Claude and Gemini, replicated in Czech. LLMs shift on **Dimension 1**,
  toward the informational pole, and the shift varies a lot by model. Independent
  confirmation, on general prose rather than academic abstracts, that Dimension 1 is where
  the difference sits — which is what the stiffness axis is built on.
- Dawkins, H., Fraser, K. C., & Kiritchenko, S. (2025), "When Detection Fails", arXiv:2506.09975
  — the same Biber features over 505,159 social-media posts, finding systematic differences
  but **different ones**, because genre changes which features move. That is the argument
  for per-channel rules, with evidence.

Reinhart, A. (maintained), *LLM writing styles*, <https://www.refsmmat.com/notebooks/llm-style.html>
— an annotated bibliography kept by an author of the PNAS study on the same question,
spanning fiction, social media, student writing and code. Useful as a maintained secondary
source; check it before commissioning new research.

Deliberately excluded, and it matters that they are: any AI-detector score (Liang et al.,
*Patterns* 4(7):100779, measured a 61.22% false-positive rate against non-native English
writers across seven detectors), burstiness (no grounding found; GPTZero dropped it in
autumn 2023), and readability indices (validated on schoolchildren and Navy trainees, not on
whether prose sounds like a person). This skill is not a detector and not a grammar checker.
- `ognjengt/founder-skills` (MIT) — the shared-context-file pattern (`FOUNDER_CONTEXT.md`), adopted here as `WRITING_CONTEXT.md`.
