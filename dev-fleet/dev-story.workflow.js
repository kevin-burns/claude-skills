export const meta = {
  name: 'dev-story',
  description:
    'Implement a user story through the dev fleet: plan -> build (TDD, isolated branch) -> ' +
    'verify facts -> review (bounded fix loop) -> full-suite gate, then hand a ready-to-merge ' +
    'branch back to the main agent. The fleet never merges/pushes — that stays with you.',
  phases: [
    { title: 'Plan' },
    { title: 'Build' },
    { title: 'Verify facts' },
    { title: 'Coherence' },
    { title: 'Review' },
    { title: 'Full-suite gate' },
  ],
}

// ---------------------------------------------------------------------------
// Input: the user story. Pass as a string, or { story, base } via Workflow args.
//   Workflow({ name: 'dev-story', args: 'As a user I want ...' })
//   Workflow({ name: 'dev-story', args: { story: '...', base: 'main' } })
// Returns a structured hand-back the MAIN agent acts on (it owns merge/push/PR).
// ---------------------------------------------------------------------------
const story = typeof args === 'string' ? args : args?.story
const base = (typeof args === 'object' && args?.base) || 'HEAD'
const mode = (typeof args === 'object' && args?.mode) || 'feature' // 'feature' | 'refactor'
// Coherence gate: 'auto' runs the structural check only on non-trivial changes (see below),
// 'always'/'never' override the heuristic.
const coherenceMode = (typeof args === 'object' && args?.coherence) || 'auto'
if (!story) throw new Error('dev-story: pass the task as args (string, or {story, mode, base}).')
if (!['feature', 'refactor'].includes(mode)) {
  throw new Error(`dev-story: mode must be "feature" or "refactor", got "${mode}"`)
}
if (!['auto', 'always', 'never'].includes(coherenceMode)) {
  throw new Error(`dev-story: coherence must be "auto", "always", or "never", got "${coherenceMode}"`)
}

// Mode drives what "done" means. Feature = new behavior (test-first). Refactor =
// behavior-preserving (existing suite is the safety net; don't reduce coverage).
const PLAN_MODE =
  mode === 'refactor'
    ? 'This is a BEHAVIOR-PRESERVING refactor. Do NOT plan new feature tests. Identify: the ' +
      'observable behavior to PRESERVE (the existing suite is the safety net), the structural goal ' +
      '(e.g. LOC reduction, fewer tests at equal coverage, a module split), and any characterization ' +
      'tests to add FIRST only where current coverage of the touched code is thin.'
    : 'Return the tests to write — a success case and at least one edge/failure case.'
const BUILD_MODE =
  mode === 'refactor'
    ? 'Behavior-preserving refactor: do NOT change observable behavior. The existing tests are your ' +
      'safety net — keep them green; add characterization tests first only where coverage is thin; ' +
      'achieve the structural goal; coverage must not drop. Do not write new feature tests.'
    : 'Implement test-first: write a failing test, watch it fail, then make it pass.'

// --- structured contracts (force each agent to return machine-usable data) ---
const PLAN = {
  type: 'object',
  required: ['acceptance_criteria', 'tests_to_write'],
  properties: {
    acceptance_criteria: { type: 'array', items: { type: 'string' } },
    tests_to_write: { type: 'array', items: { type: 'string' } },
    files_likely_touched: { type: 'array', items: { type: 'string' } },
    facts_needed: { type: 'array', items: { type: 'string' } },
    // Deliberate deferrals — travel with the reviewer/coherence so they don't blocking-flag
    // a scope decision (e.g. "Go CLI deferred to a companion change").
    out_of_scope: { type: 'array', items: { type: 'string' } },
  },
}
const BUILD = {
  type: 'object',
  required: ['branch'],
  properties: {
    branch: { type: 'string' },
    worktree_path: { type: 'string' },
    base_ref: { type: 'string' },
    commits: { type: 'array', items: { type: 'string' } },
    files_changed: { type: 'array', items: { type: 'string' } },
    tests: {
      type: 'object',
      properties: {
        command: { type: 'string' },
        scope: { type: 'string' }, // "targeted" | "full"
        full_suite_command: { type: 'string' }, // owed full-suite run for the orchestrator
      },
    },
    missing_facts: { type: 'array', items: { type: 'object' } },
    open_questions: { type: 'string' },
  },
}
const VERDICTS = { type: 'object', properties: { verdicts: { type: 'array' } } }
const COHERENCE = {
  type: 'object',
  required: ['verdict'],
  properties: {
    verdict: { type: 'string' }, // pass | fail
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: { check: { type: 'string' }, location: { type: 'string' },
          issue: { type: 'string' }, suggested_fix: { type: 'string' } },
      },
    },
    loop_back_target: { type: ['string', 'null'] }, // "code-builder" | null
  },
}
const REVIEW = {
  type: 'object',
  required: ['verdict', 'findings'],
  properties: {
    verdict: { type: 'string' }, // ship | ship-with-fixes | needs-rework
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: { severity: { type: 'string' }, location: { type: 'string' },
          issue: { type: 'string' }, suggested_fix: { type: 'string' } },
      },
    },
  },
}
const SUITE = {
  type: 'object',
  required: ['passed'],
  properties: { passed: { type: 'boolean' }, command: { type: 'string' }, output_tail: { type: 'string' } },
}

// 1) PLAN — decompose the story into a testable spec (no code yet).
phase('Plan')
const plan = await agent(
  `Scope this task for implementation (mode: ${mode}). Do NOT write code.\n\nSTORY:\n${story}\n\n` +
    `${PLAN_MODE}\n\nAlso return: acceptance criteria as a checklist, files likely touched, any ` +
    `FACTS that must be verified before coding (versions, APIs, IDs, config values), and ` +
    `out_of_scope — anything deliberately deferred to a companion change, so review doesn't ` +
    `treat a scope decision as a bug.`,
  { label: 'plan', phase: 'Plan', schema: PLAN },
)

// 2) BUILD — code-builder implements test-first on its own isolated branch.
phase('Build')
const build = await agent(
  `Implement this change in an isolated worktree on a feature branch; commit on the branch only ` +
    `— never merge/push. ${BUILD_MODE} Bound your test runs (targeted during iteration; the ` +
    `relevant module once before committing) and report full_suite_command for the orchestrator.\n\n` +
    `STORY:\n${story}\n\nPLAN:\n${JSON.stringify(plan, null, 2)}\n\n` +
    `Use ONLY these facts; if anything else is unknown, return it in missing_facts (do not invent):\n` +
    `${JSON.stringify(plan?.facts_needed ?? [], null, 2)}\n\nBase ref: ${base}`,
  { agentType: 'code-builder', label: 'build', phase: 'Build', schema: BUILD },
)
if (!build?.branch) {
  return { ok: false, stage: 'build', note: 'code-builder did not produce a branch', plan, build }
}
const where = build.worktree_path
  ? `worktree ${build.worktree_path} (branch ${build.branch})`
  : `branch ${build.branch}`

// 2b) VERIFY FACTS — only if the builder flagged anything unknown.
let facts = null
if (build.missing_facts?.length) {
  phase('Verify facts')
  facts = await agent(
    `Resolve these facts a code change depends on. For each: cite a source you read, refute with ` +
      `the correct value, or return the exact read-only lookup. Never assert from memory.\n` +
      `${JSON.stringify(build.missing_facts, null, 2)}`,
    { agentType: 'fact-verifier', label: 'facts', phase: 'Verify facts', schema: VERDICTS },
  )
  // Unresolved facts are a hard stop — hand back rather than ship guesses.
  const unresolved = (facts?.verdicts ?? []).filter((v) => v.verdict === 'UNVERIFIABLE')
  if (unresolved.length) {
    return { ok: false, stage: 'facts', note: 'unresolved facts — main agent must resolve before merge',
      branch: build.branch, plan, build, facts, unresolved }
  }
}

// 2c) COHERENCE — structural fit of the impl vs plan/spec/verified facts. Runs AFTER fact
// verification (so refuted assumptions are known) and BEFORE review (cheaper structural pass
// than line-level review). Gated on complexity: a one-file, one-commit change doesn't earn the
// extra stage. Bounded fix loop, same shape as review.
const filesN = build.files_changed?.length ?? 0
const commitsN = build.commits?.length ?? 0
const criteriaN = plan?.acceptance_criteria?.length ?? 0
const runCoherence =
  coherenceMode === 'always' ||
  (coherenceMode !== 'never' && (filesN > 5 || commitsN > 3 || criteriaN > 3))
let coherence = null
if (runCoherence) {
  phase('Coherence')
  let crounds = 0
  while (crounds < 2) {
    coherence = await agent(
      `Check the STRUCTURAL fit of the implementation on ${where} against the plan, the spec it ` +
        `cites, and the verified facts — NOT line-level correctness (that's the reviewer's job). ` +
        `Read the diff: git diff ${build.base_ref || base}...${build.branch}. Apply your five checks ` +
        `(spec-to-code + plan-to-commit traceability, inverse-pair round-trip fidelity WITHOUT ` +
        `normalization tricks, cross-implementation parity, contract/docstring fidelity). Return ` +
        `verdict (pass|fail), findings, and loop_back_target.\n\n` +
        `PLAN:\n${JSON.stringify(plan, null, 2)}\n\n` +
        `VERIFIED FACTS (confirm the code uses corrected values, not refuted assumptions):\n` +
        `${JSON.stringify(facts?.verdicts ?? [], null, 2)}\n\n` +
        `OUT OF SCOPE (deliberate deferrals — do NOT fail on these):\n` +
        `${JSON.stringify(plan?.out_of_scope ?? [], null, 2)}`,
      { agentType: 'coherence-checker', label: `coherence:r${crounds + 1}`, phase: 'Coherence', schema: COHERENCE },
    )
    if (coherence?.verdict !== 'fail') break
    const cfix = await agent(
      `On ${where}, fix ONLY these structural coherence mismatches, test-first, commit on the branch ` +
        `(no merge/push). For an inverse-pair failure the round-trip test must assert EXACT identity ` +
        `— no .rstrip()/.lower()/sorted()/set() normalization that hides the delta:\n` +
        `${JSON.stringify(coherence.findings ?? [], null, 2)}`,
      { agentType: 'code-builder', label: `coherence-fix:r${crounds + 1}`, phase: 'Coherence', schema: BUILD },
    )
    if (cfix?.commits?.length) build.commits = [...(build.commits ?? []), ...cfix.commits]
    crounds++
  }
}

// 3) REVIEW + bounded fix loop (max 2 rounds) — review, fix blockers, re-review.
phase('Review')
let review = null
let rounds = 0
while (rounds < 2) {
  review = await agent(
    `Review the change on ${where}. Read the diff: git diff ${build.base_ref || base}...${build.branch}. ` +
      `Return findings (severity + location + suggested_fix) and a verdict. Advisory, not a gate.\n` +
      `Out of scope (deliberately deferred — do NOT blocking-flag these):\n` +
      `${JSON.stringify(plan?.out_of_scope ?? [], null, 2)}`,
    { agentType: 'code-reviewer', label: `review:r${rounds + 1}`, phase: 'Review', schema: REVIEW },
  )
  const blockers = (review?.findings ?? []).filter((f) => f.severity === 'blocking')
  if (review?.verdict === 'ship' || blockers.length === 0) break
  const fix = await agent(
    `On ${where}, address ONLY these blocking review findings, test-first, and commit on the branch ` +
      `(no merge/push):\n${JSON.stringify(blockers, null, 2)}`,
    { agentType: 'code-builder', label: `fix:r${rounds + 1}`, phase: 'Review', schema: BUILD },
  )
  if (fix?.commits?.length) build.commits = [...(build.commits ?? []), ...fix.commits]
  rounds++
}

// 4) FULL-SUITE GATE — the orchestrator's job (the builder bounded its own runs).
phase('Full-suite gate')
let suite = null
const suiteCmd = build.tests?.full_suite_command
if (suiteCmd) {
  suite = await agent(
    `Run the full test suite ONCE on ${where} and report the outcome verbatim. Do NOT change code — ` +
      `just run and report pass/fail.\nCommand: ${suiteCmd}`,
    { agentType: 'code-builder', label: 'full-suite', phase: 'Full-suite gate', schema: SUITE },
  )
}

// 5) HAND BACK — the main agent decides merge/push/PR. The fleet never does.
const suiteState = suite ? (suite.passed ? 'green' : 'RED') : 'not-run'
return {
  ok: true,
  story,
  branch: build.branch,
  worktree_path: build.worktree_path ?? null,
  commits: build.commits ?? [],
  files_changed: build.files_changed ?? [],
  plan,
  facts,
  coherence: runCoherence
    ? { verdict: coherence?.verdict ?? null, findings: coherence?.findings ?? [] }
    : { state: 'skipped (below complexity threshold)' },
  review: { verdict: review?.verdict ?? null, rounds: rounds + 1, findings: review?.findings ?? [] },
  full_suite: { state: suiteState, command: suiteCmd ?? null, detail: suite ?? null },
  next_actions: [
    `Inspect ${where}`,
    suiteState === 'RED'
      ? 'Full suite RED — do NOT merge until green'
      : suiteState === 'not-run'
        ? `Full suite not run — run it before merge${suiteCmd ? `: ${suiteCmd}` : ''}`
        : 'Full suite green',
    runCoherence && coherence?.verdict === 'fail'
      ? 'Coherence still FAILING — structural mismatch unresolved after fix loop; weigh before merge'
      : 'Coherence OK',
    review?.verdict === 'needs-rework' ? 'Review still wants rework — weigh findings' : 'Review OK',
    'You (main agent) decide: merge / push / open PR — the fleet never does this.',
  ],
  open_questions: build.open_questions ?? '',
}
