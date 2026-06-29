# De-slopping a CV (removing AI texture, keeping authority)

AI-written CVs have a recognisable texture; both human reviewers and LLM screeners
increasingly down-rank it, and it reads as undifferentiated. This step strips that
texture while protecting the ATS work and staying truthful.

**This skill is self-contained.** Everything needed to de-slop a CV is in this file
— no other skill is required. If the `clear-and-human` skill happens to be
installed, you *may* use its fuller `references/ai-patterns.md` as an extended
detection list, but treat that as an optional enhancement, never a dependency.

**Do not pipeline `clear-and-human` and `hook-and-human` on the CV.** They optimise
for opposite things (credibility vs reach) and their own docs warn they fight. The
de-slop list below is the engine. From `hook-and-human` borrow exactly two ideas:
(1) "lead the summary line with a real specific," applied only to the summary line;
(2) the soft-fabrication floor below, applied to every metric.

## The keyword guard (the rule that makes de-slopping safe)

The AI-vocabulary cut-list below overlaps with real JD keywords and real technology
names. De-slopping must not strip a term the ATS keyword-matching step needs.

- **KEEP** a flagged word when it is *referential* — a keyword in the target JD, or
  the accurate name of a technology, methodology, or metric the candidate actually
  used ("Agile" the method; "scalable" describing an architecture that genuinely
  scaled; "optimised" naming real measured work).
- **CUT or replace** it when it is *empty* — connective tissue, an unquantified
  booster, or inflation with no referent ("leveraging synergies", "robust
  solutions", "passionate about optimising outcomes").

Rule of thumb: if the word sits next to a concrete thing with a number or a named
system, it stays; if it's decorating a vague claim, it goes — and the fix is to
replace it with the concrete thing it was hiding.

## CV-channel rewrite rules (override generic humanizing advice)

A CV is its own channel. Unlike blog/linkedin de-slopping, do **not**:
- add first person or "I";
- add contractions, conversational asides, or "personality";
- turn fragment bullets into full prose sentences.

Do keep fragment bullets led by a past-tense action verb (Built, Migrated, Reduced,
Owned, Automated), each leading with a quantified outcome. The summary/profile line
is the one place a light, plain human register fits — still no boosters.

## The AI/slop pattern list for CVs (detect → fix)

Adapted and condensed (MIT / public-domain sources) for résumé prose. Flag each
with the exact phrase and a concrete fix.

**Empty AI vocabulary (cut, or replace with the specific thing):**
leverage, utilise, spearhead (as inflation), robust, seamless, dynamic, synergy,
holistic, comprehensive, transformative, cutting-edge, best-in-class, world-class,
passionate, results-driven, detail-oriented, proven track record, go-getter, team
player, think outside the box, value-add, results-oriented, dynamic professional.

**Weak verbs (replace with a strong specific verb + outcome):**
"Responsible for", "Helped with", "Worked on", "Assisted with", "Involved in",
"Tasked with" → name what you did and what changed.

**Significance inflation:** "played a pivotal role", "was instrumental in",
"spearheaded a transformative initiative", "revolutionised", "drove
game-changing…". → State the action and the measured result.

**Superficial `-ing` tails:** "...migrated the cluster, ensuring scalability and
reliability." The tail bolts fake depth on a sentence. → Cut it, or make it a real
measured outcome ("...cutting failover from 40s to 4s").

**Rule of three:** every bullet ending in a triad ("scalable, robust, and
maintainable"). Most triads have one real item and two fillers — keep the real one.

**Uniform bullet cadence/length:** the loudest tell. Mix short outcome bullets with
one or two longer ones.

**Vague quantification:** "significantly", "substantially", "various", "numerous",
"multiple" used as a stand-in for a number. → Real number, or drop the claim.

**Mechanics (also help parseability):** em-dashes (—) → commas/periods; curly
quotes → straight; Title Case In Headings → sentence case; decorative emoji/dingbat
bullets → standard bullets; mechanical bolding of key terms → plain.

## The soft-fabrication floor (from hook-and-human; governs every metric)

The dangerous fabrications on a punched-up CV aren't outright lies — they're *soft*
ones, because they look like measured results:
- **Derived numbers** — extrapolating an approved figure ("build 40→6 min" becoming
  "saves 30 minutes per build" when you don't know the run rate).
- **Aggregate-time claims** — "saved the team hundreds of hours" from one instance.
- **Soft outcomes** — "dramatically improved reliability", "significantly reduced
  costs" with no measured basis.
Use only the real, measured number, or state the action without a metric. Leave an
`[ADD REAL METRIC]` placeholder rather than inventing one.

## Order of operations

De-slop **after** the ATS rewrite and **before** delivery, so the keyword guard can
see which terms were deliberately included. After de-slopping, re-check skills
coverage to confirm no genuine JD keyword was removed.

## Provenance

Pattern list adapted/condensed (all MIT or public domain): `clear-and-human`'s
`ai-patterns.md` (itself merged from Wikipedia "Signs of AI writing" and
blader/humanizer); soft-fabrication floor from `hook-and-human`; Strunk's *Elements
of Style* (public domain) for the constructive rules.
