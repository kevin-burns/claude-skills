# CV Red-Team pass (optional): push back, don't reject

An optional pass that pressure-tests a tailored CV the way a council red team
pressure-tests a proposal. It follows the council pattern (orchestrator–workers +
evaluator–optimizer, per Anthropic's *Building Effective Agents*; same idiom as the
`council-skills` red-team members): the red team **arrives last**, after a working
tailored CV exists; it **stays in lane** — it finds weaknesses, it does not rewrite
the CV or invent fixes; and it **pushes back, it does not reject** — every finding
is a flag for the candidate to act on, not a pass/fail gate. The candidate owns the
decision.

The division of labour resolves the fabrication tension by construction: the red
team *finds* gaps; the tailor (the proposer) *fixes only the truthful ones*; any gap
that can't be closed without fabricating is surfaced to the candidate as a real gap,
not papered over.

This pass is **off by default.** Run it when the user wants their CV stress-tested.

## The lenses

Run the lenses that fit; keep it lean (2–4, not all four for a small CV). Each lens
critiques from one angle and does not stray into another's.

1. **ATS Red Team (the machine).** Attacks against the screener: parseability
   breaks, missing JD keywords, linkless or live-demo-less projects, solo repos
   mislabelled as open source, tutorial-grade projects, unclaimed bonus URLs. For a
   *measured* version, score the CV through a real ATS engine **many times** and
   read the distribution — see "Using a real scorer" below.
2. **Recruiter Red Team (the human six-second scan).** Attacks as a skeptical
   reviewer: what's unreadable in one pass, which bullets have no quantified
   outcome, where seniority signal is missing or mismatched, what looks
   embellished, what a hiring manager wouldn't believe.
3. **Slop Red Team.** Attacks AI texture using `deslop-cv.md`: booster-stacked
   summary, `-ing` tails, rule-of-three, uniform cadence, weak verbs — and the
   *soft* fabrications (derived numbers, aggregate-time, vague-outcome boosters).
4. **Truth Red Team (the floor's enforcer).** Challenges each notable claim with
   "could you defend this in an interview?" Flags overstatement, unverifiable
   metrics, and anything invented. This lens has veto power over the others: a fix
   another lens wants that can only be met by fabricating is rejected here and
   becomes a candidate-decision gap instead.

   This lens is a **verifier instance** — it runs the portable verifier contract
   ([`docs/verifier-contract.md`](../../docs/verifier-contract.md), Profile B) on
   each CV claim, so it inherits the same discipline as the code fact-verifier:
   - **Source of record = the candidate's real history** (their confirmation, the
     supplied CV, employment record, public commits/repos, certs). Model memory is
     never a source — never invent a number, skill, employer, or title.
   - **SUPPORTED** = defensible in an interview (candidate-confirmed or publicly
     evidenced). **REFUTED** = overstated → carry the true, smaller value and correct
     down to it. **UNVERIFIABLE** = unbacked → return the lookup ("ask the candidate
     for the real figure / the repo URL") and leave it as a candidate-decision gap,
     never a fabricated fill.
   - **Read-only:** the lens *finds*; the tailor *fixes only the truthful ones* —
     consistent with "critique, don't propose" below.

## Output: a triage header per lens, then a synthesis

Each lens opens with the council triage header, then its findings:

```
### <Lens> Red Team
> Verdict: strong · revise · weak   (pick one)
> Top concern: <one sentence — the thing not to miss from this lens>
> Blocker before sending? yes / no

<3–6 specific findings, each: what's weak + why it costs, no rewrite proposed>
```

Then synthesise (the tailor's job, not the red team's):
- **Fix now (truthful):** weaknesses closeable by surfacing real things — add a real
  link, relabel a real contribution, foreground a real complex project, cut slop.
- **Candidate decides:** real gaps (a missing skill, thin open-source, a seniority
  mismatch) — name the trade-off, don't invent the fix.
- **Ignore (noise):** findings that target the screener's non-deterministic judgment
  band (e.g. ±5 swings on "project complexity"); chasing these is chasing noise.

## House rules (from the council pattern)

- **Critique, don't propose.** The red team names weaknesses; the tailor decides the
  response. A lens that writes "instead, add X" has drifted — cut it.
- **Don't be adversarial for its own sake.** Concentrate fire on load-bearing
  weaknesses; if a dimension is genuinely strong, say so. Manufactured critique
  burns credibility.
- **Specific, not generic.** "Bullets lack metrics" is weak; "4 of 6 bullets under
  Acme have no outcome — e.g. 'Responsible for CI pipelines' states a duty, not a
  result" is a finding.
- **Stay in lane.** ATS lens doesn't judge prose taste; Slop lens doesn't judge
  keyword coverage; Truth lens doesn't redesign layout.

## Using a real scorer (measured ATS lens)

The ATS lens can be made **quantitative** — score a CV through a real engine (e.g. a
local `hiring-agent`) many times and read the *distribution*. Two disciplines bind any
such measurement, in the script **and** in your hand-written reports:

- **Report the distribution, never a single run** ("median 84, range 78–91 over 10
  runs"). The critic is non-deterministic; one number is noise. A change is real only
  if the median rises beyond the noise band without dropping the worst-case floor.
- **Honour the minimum-successful floor.** Real scorers fail some runs; a median over
  too few survivors is noise reported as signal — which principle 1 forbids. If fewer
  than ~5 runs produced a valid score, do **not** quote a median; say "insufficient
  successful runs" instead. (The harness enforces this via `--min-successful`.)

The full setup — driving `scripts/ats_adversarial_loop.py`, wiring an adapter to a
real `hiring-agent`, the model backends (Ollama / OpenAI-compatible: gpt-5-mini,
Haiku), and the markdown-first extraction path — lives in
[`measured-scorer.md`](./measured-scorer.md). It's a separate file on purpose: that
wiring is an external-tool integration runbook, not red-team philosophy, and it loads
only when you actually run the measured loop.

## Provenance

Red-team structure and the critique-not-propose / preserve-the-finding discipline
follow the `council-skills` red-team members (MIT) and Anthropic's *Building
Effective Agents* evaluator–optimizer pattern.
