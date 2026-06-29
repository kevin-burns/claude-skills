# Measured ATS lens — driving a real scorer

The red-team's ATS lens (see `red-team.md`) can be made **quantitative**: score a CV
through a real ATS engine many times and read the *distribution*. This file is the
setup — the harness, the adapter wiring to `hiring-agent`, the model backends, and the
extraction path. It lives apart from `red-team.md` on purpose: this is an external-tool
integration runbook, not red-team philosophy, and nothing here loads unless you
actually run the measured loop.

## The two disciplines (non-negotiable)

These bind every measured result — the script enforces them and so must you when you
report by hand:

- **Report the distribution, never a single run** ("median 84, range 78–91 over 10
  runs"). The critic is non-deterministic; one number is noise. Treat a change as real
  only if the median rises beyond the noise band without dropping the worst-case floor;
  stop when the median plateaus. Note that the gain is measured against one noisy tool
  and may not transfer.
- **Honour the minimum-successful floor.** A real scorer fails some runs — malformed
  output, a flaky call (a weak model fails *often*; one 4B run we measured emitted
  `deductions.total = -6` and another dropped `bonus_points`, both schema violations).
  The harness skips those and reports the failure count, but a median computed over too
  few survivors is **noise reported as signal** — the exact thing this skill's first
  principle forbids. So the script **refuses** to print a median below
  `--min-successful` (default 5), and you must apply the same floor by hand: if fewer
  than ~5 runs produced a valid score, do not quote a median — say "insufficient
  successful runs (n=2 of 10); raise N or the backend is too unreliable to measure
  with" instead. Script-only enforcement leaves the manual path able to lie; it must not.

The harness is `scripts/ats_adversarial_loop.py` (`selftest` runs without a model
backend; `score --scorer-cmd ...` drives a real engine).

## Wiring a real hiring-agent scorer (verified recipe)

**Pinned for rot-detection: verified against `interviewstreet/hiring-agent@4db8655`**
(`4db86554e622f4fb8e653565bc99fb7df2f6ef93`, 2026-06-22 — also the commit the Family-B
levers in `ats-mechanics.md` were read from). This recipe touches hiring-agent's
*internal* surface (`score.main`, `ResumeEvaluator.evaluate_resume`, the
`deductions.total ≥ 0` schema, and provider injection by reassigning
`initialize_llm_provider`) — none of it a stable public contract. If your checkout's
HEAD differs, treat every step below as **unverified** until re-checked: the injection
can silently no-op (the native provider runs instead) and the derived levers may have
drifted. Re-pin from your own `git -C <hiring-agent> rev-parse HEAD` once you reverify.

`interviewstreet/hiring-agent` does **not** print JSON — its `score.py <pdf>` prints
a human-readable report and has no `--json` flag. So `--scorer-cmd` points at a tiny
adapter, not at `score.py` directly.

**Convert the PDF upstream, deterministically — don't let the scorer parse it.**
hiring-agent's PDF path is `PDF →(pymupdf)→ markdown →(~6 LLM calls)→ JSONResume
→(flatten)→ text →(LLM)→ score`. The evaluator scores **text**; the JSONResume is an
intermediate that gets flattened right back to text — so those ~6 LLM extraction
calls are slow, non-deterministic, *and* largely wasted. Convert the CV to markdown
**upstream** with the deterministic `markdown-converter` (markitdown) you already own,
and feed that straight to the evaluation step:

- **Preferred adapter (`score_md.py`):** `markitdown <cv>` → markdown (deterministic;
  fail loudly on empty output — a text-box/scanned doc), then call
  `ResumeEvaluator(...).evaluate_resume(markdown)` directly. **One** LLM call, not
  seven; the real CV text, not an LLM's lossy re-structuring. This is the path that
  honours the skill's extraction boundary (see `SKILL.md` Step 2). *Verified end to
  end:* markitdown → OpenAI-compatible provider (Ollama `/v1`) → a well-formed
  evaluation.
- **Fallback adapter (`score_json.py`):** run hiring-agent's own `score.main(pdf)`
  (its internal pymupdf + LLM extraction) inside `contextlib.redirect_stdout(stderr)`
  and print only the total. Use this **only** when you specifically want to reproduce
  hiring-agent's *whole* pipeline including its own parser — slower and noisier.

Both adapters: compute the total exactly as `print_evaluation_results` does (sum
capped category scores + bonus − deductions, cap at 120), wrap the LLM call in
`try/except`, and emit `{"error": ...}` on failure. The model occasionally returns
malformed structured output (e.g. a 4B emitting `deductions.total = -6`, which
violates the schema's `≥ 0`); that sample must be **skippable, not fatal**.

1. **Provider.** It supports Ollama and Gemini natively. Put in the repo's `.env`:
   `LLM_PROVIDER=ollama` and `DEFAULT_MODEL=<your-ollama-tag>` (any local tag works,
   e.g. a 4B model; it need not be in the repo's `MODEL_PARAMETERS` — it falls back
   to sane defaults). Install its `requirements.txt` in a Python 3.11 venv.
   - **Any OpenAI-compatible model (gpt-5-mini, Haiku, a gateway).** Don't fork the
     provider layer — ship a small `oai_provider.py` (an `OpenAICompatibleProvider`
     with the same `.chat(model, messages, options, **kwargs)` surface, built on the
     `openai` SDK with a configurable `base_url`/`api_key`) and have the adapter
     **inject** it by reassigning the bound `initialize_llm_provider` in the `pdf`,
     `evaluator`, and `llm_utils` modules when `LLM_BACKEND=openai`. One provider
     covers every backend that speaks Chat Completions — set `OPENAI_BASE_URL` +
     `OPENAI_API_KEY` + `DEFAULT_MODEL`:
     - Ollama's own endpoint: `http://localhost:11434/v1` (key `ollama`) — lets you
       A/B a local model against a hosted one through one code path, and verifies the
       wiring with no external key.
     - OpenAI: `https://api.openai.com/v1`, `DEFAULT_MODEL=gpt-5-mini`.
     - Anthropic (OpenAI-compat endpoint): `https://api.anthropic.com/v1`,
       `DEFAULT_MODEL=claude-haiku-4-5-20251001`.
     Translate the Ollama-style `format=<schema>` kwarg to `response_format=
     {"type":"json_object"}` (widest cross-vendor support; the prompt already names
     the JSON shape and a malformed sample is skipped upstream). Leave sampling params
     **off by default** — some newer models reject a non-default `temperature`.
     Different judge models score differently, so a distribution is **only comparable
     within one backend** — never compare a gpt-5-mini median against an Ollama one.
2. **Adapter.** Write `score_md.py` (preferred) or `score_json.py` (fallback) per the
   two bullets above — each ~30 lines, each printing only `{"total": N, "max": M}` to
   stdout and routing all other chatter to stderr.
3. **Run:** `score --cv cv.pdf --scorer-cmd ".venv/bin/python score_md.py {cv}"
   --runs N`. The harness skips failed samples and reports the count
   ("median X, range A–B over N runs (k failed/skipped)"); raise `--runs` if many
   fail.

**Caching note:** only the fallback `score_json.py` path caches (hiring-agent stores
the PDF→JSON extraction per filename in `cache/resumecache_<name>.json` under
`DEVELOPMENT_MODE`) — clear `cache/` when the CV content changes, or use a fresh
filename per variant. The preferred `score_md.py` path does the deterministic
conversion each run (cheap) and caches nothing, so there's no stale-extraction trap.
