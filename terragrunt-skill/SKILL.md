---
name: terragrunt-skill
license: MIT
description: Comprehensive Terragrunt 1.x skill for generating, validating, reviewing, and debugging Terragrunt configurations (root.hcl, terragrunt.hcl, terragrunt.stack.hcl, units, stacks, catalogs) across AWS, Azure, and GCP. Use this skill whenever the user mentions Terragrunt, terragrunt.hcl, root.hcl, stack files, units, HCL orchestration of OpenTofu/Terraform, remote state DRY configuration, run --all, dependency blocks between modules, or asks to scaffold/lint/diagnose multi-environment IaC layouts — even if they don't say "Terragrunt" explicitly but show Terragrunt HCL.
---

# Terragrunt (1.x)

Single skill for all Terragrunt work, organized as a router: identify the task mode below,
read ONLY the listed reference(s), then act. References are grep-friendly — prefer
`grep` lookups over reading whole files.

## Hard policy

1. **Post-1.0 CLI only.** Never generate or recommend pre-1.0 forms: `run-all`,
   `plan-all`, `hclfmt`, `hclvalidate`, `graph-dependencies`, `validate-inputs`,
   `terragrunt-` prefixed flags, the `skip` attribute, `retryable_errors`, or bare
   `find_in_parent_folders()` pointing at a root `terragrunt.hcl`. If user code contains
   these, flag them and propose the 1.x form.
2. **Fact-based generation.** Every generated pattern must trace to a documented Gruntwork
   pattern (references here carry doc links to docs.terragrunt.com). Don't invent layouts.
3. **Knowledge freshness.** Embedded references were verified against Terragrunt 1.x
   (current stable **v1.1.2**, released 2026-07-29). **v1.1.0 graduated six experiments to
   GA** — `stack-dependencies`, `cas`, `catalog-redesign`, `mark-many-as-read`,
   `opt-out-auth`, `dag-queue-display` — so their features are now **enabled by default**;
   passing the old `--experiment`/`TG_EXPERIMENT` value only prints a "completed experiment"
   warning. The stack-dependency features (`autoinclude`, `unit.<name>.path` /
   `stack.<name>.path`, `dependency` on stack dirs via `autoinclude`) and the CAS attributes
   (`update_source_with_cas`, `mutable`) therefore require **v1.1.0+** — flag them and do NOT
   emit them for repos pinned to ≤1.0.x.

   **v1.1.1 added two experiments** (opt-in, not GA), both on the `terraform` block and both
   requiring **v1.1.1+**: `oci` (module sources from OCI registries via `oci://`) and
   `version-attribute` (a `version` constraint for `tfr://` registry modules). Syntax and the
   gating rules are in `references/hcl-blocks.md` under `## BLOCK: terraform`. v1.1.1 was
   otherwise a bug-fix release — it introduced no new GA surface.

   **v1.1.2 added no new GA surface either, but two of its fixes change what to advise.**
   Recommend **v1.1.2+** rather than v1.1.1 wherever either applies:
   - The **provider cache server**'s archive-download endpoint did not require the run's
     token before v1.1.2, so another local process could use a running cache server to pull
     from a private registry with the starting user's registry credentials. Relevant on
     shared CI runners. See `references/scale-and-performance.md`.
   - **v1.1.1 specifically broke `iam_role`** (and `--iam-assume-role` / `TG_IAM_ASSUME_ROLE`)
     when combined with static AWS credentials: backend operations assumed the role a second
     time, so it tried to assume itself and AWS returned `AccessDenied`. The error points at
     the trust policy, but editing the trust policy is the wrong fix — upgrading is. See
     `references/hcl-blocks.md` under `## BLOCK: iam_role`.

   **Experiments are not a short list, and they move in patch releases.** Alongside the two
   above, `azure-backend`, `deep-merge`, `dependency-fetch-output-from-state`,
   `hook-context-env`, `iac-engine`, `optional-hooks`, `slow-task-reporting` and `symlinks`
   were active as of v1.1.1, and **v1.1.2 added `otel-logs`** (OpenTelemetry logs signal via
   `TG_TELEMETRY_LOGS_EXPORTER`) **and `profiling`** (pprof CPU/heap/goroutine collection for
   debugging Terragrunt itself, not the infrastructure it manages) — twelve active as of
   v1.1.2. v1.1.2 also changed two existing ones: `azure-backend` went from inert to
   functional (see `references/azure-backend.md` — this reverses a long-standing "Terragrunt
   never bootstraps Azure state" rule), and `oci` gained CAS caching plus Docker
   credential-helper auth. These references cover only some of them, so an unfamiliar
   `--experiment` value
   is not evidence that it is wrong — look it up rather than flagging it. For anything newer,
   niche, or not found in the references, use the C7 search skill (Context7) or fetch
   docs.terragrunt.com directly — do not guess.
4. Terragrunt orchestrates **OpenTofu or Terraform**; don't assume one unless the user's
   repo indicates it (`.terraform-version`, `terraform_binary`, provider constraints, or an
   `engine` block — the latter is gated behind the `iac-engine` experiment and is not covered
   in `references/hcl-blocks.md`, so look it up before editing one).

## Terminology (1.0)

**Unit** = directory with `terragrunt.hcl` deploying one module. **Stack** = group of units;
*implicit* (directory tree) or *explicit* (`terragrunt.stack.hcl`). **Catalog** = library of
reusable unit/module definitions. Targeting uses `--filter` expressions.

## Mode router

| Task | Mode | Read first |
|---|---|---|
| "Create/scaffold/set up" configs, envs, stacks | GENERATE | references/architecture-patterns.md + relevant templates/ |
| "Validate/lint/check/CI" existing configs | VALIDATE | validate.sh header (abs path in VALIDATE workflow); references/cli-reference.md as needed |
| "Review/audit/best practice" a repo or file | REVIEW | references/best-practices.md |
| Error message pasted / "why is this failing" | DIAGNOSE | grep references/error-patterns.md |
| "What does X do" (block/function/command) | LOOKUP | grep the matching reference below |
| Complex/edge-case examples (multi-account, CI, mocks) | EXAMPLES | references/advanced-examples.md |
| Anything Azure backend/provider (state, auth, gotchas) | (any mode) | **also** references/azure-backend.md |
| "Only run changed units", slow `run --all`, CI fan-out, performance at scale | SCALE | references/scale-and-performance.md |
| "Migrate to stacks", convert an `_envcommon`/tree layout to `terragrunt.stack.hcl` | MIGRATE | references/architecture-patterns.md `## PATTERN: migrate an existing tree to explicit stacks` |

## Reference index (grep, don't read whole files)

- `references/architecture-patterns.md` — layout patterns, env-agnostic root rule, unit/stack
  model, dependency wiring, runtime control. Headings: `## PATTERN:`
- `references/hcl-blocks.md` — all HCL blocks (terraform, remote_state, dependency, include,
  generate, locals, inputs, feature, exclude, errors...). `grep '^## BLOCK: dependency'`
- `references/functions.md` — built-in functions by category. `grep '^## FUNCTION: get_env'`
- `references/cli-reference.md` — full 1.0 command tree + `--filter` system.
  `grep '^## COMMAND: stack run'`
- `references/error-patterns.md` — 68 diagnosed errors with causes/solutions. Grep error
  keywords first: `grep -in 'state lock' references/error-patterns.md`
- `references/best-practices.md` — practices with priority/rationale/antipatterns, plus
  `## COMPARISON:` (e.g. dependency vs dependencies) and `## DECISION:` guides
- `references/advanced-examples.md` — 21 worked examples. `grep '^## EXAMPLE:'`
- `references/azure-backend.md` — Azure (`azurerm`) remote state + provider setup and
  gotchas: whether Terragrunt bootstraps Azure depends on version + experiment
  (no by default, yes on v1.1.2+ with `--experiment azure-backend`), backend key list, auth methods,
  `use_azuread_auth`/Entra ID, provider v4 `subscription_id`, RBAC + shared-key gotchas,
  OIDC for CI. Read this for ANY Azure backend/provider task.
- `references/scale-and-performance.md` — running only changed units/stacks at scale:
  `--filter` git+graph targeting (`--filter-affected`), `find --json` CI matrices, provider
  cache server, CAS, dependency-output-from-state, parallelism, per-unit overhead, OSS vs
  paid Scale. Read for "only plan/apply what changed", slow `run --all`, or CI fan-out.

## Templates

- `templates/root/root.hcl` — root config (environment-agnostic)
- `templates/child/terragrunt.hcl` — unit including root + env.hcl
- `templates/env/env.hcl` — per-environment locals
- `templates/stack/terragrunt.stack.hcl`, `templates/catalog/` — explicit stacks & catalog units
- `templates/module/terragrunt.hcl` — standalone unit
- `templates/backends/` — remote_state for S3/GCS/Azure, essential + advanced tiers.
  **Azure caveat:** `azurerm` passes through to the native backend; Terragrunt does NOT
  bootstrap/migrate/delete Azure storage — the account/container must pre-exist. Full
  detail + gotchas in `references/azure-backend.md`.
- `templates/providers/` — provider `generate` blocks (`aws-generate-provider.hcl`,
  `azure-generate-provider.hcl`). For Azure, `subscription_id` is **required** by
  `azurerm` provider v4+ — see `references/azure-backend.md`.

Replace ALL placeholder variables before presenting (`{{mustache}}` in templates/backends and
templates/providers; `[BRACKET]` style everywhere else); never leave placeholders or invent
secrets/account IDs — ask or use obvious dummies labelled as such.

## GENERATE workflow

1. Determine pattern via references/architecture-patterns.md; output the pattern selection
   checklist (in that file) before writing files.
2. Read the relevant template(s); adapt, don't freestyle.
3. Verify the include/read graph: every `find_in_parent_folders`/`read_terragrunt_config`
   target must exist from the referencing file's location.
4. Validate if tooling exists (see VALIDATE); otherwise state what wasn't validated.
5. Present: directory tree, file list, run commands (`terragrunt run --all plan`), and any
   placeholders the user must fill.

## VALIDATE workflow

> **Bundled scripts run by absolute path.** They live in this skill's base directory (announced
> when the skill loads, usually `~/.claude/skills/terragrunt-skill`). You'll be working inside an
> IaC repo, so a relative `scripts/…` won't resolve — always use the base-dir path. The Python
> helper is stdlib-only: prefer `uv run python <path>`, falling back to `python3 <path>` if uv
> isn't on PATH (`UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"`).

`bash ~/.claude/skills/terragrunt-skill/scripts/validate.sh [DIR]` runs the layered suite:
`hcl fmt --check`, `hcl validate`, tflint, Trivy, dag check, optional plan. Control via env
vars: `SKIP_PLAN`, `SKIP_SECURITY`, `SKIP_LINT`, `SKIP_INIT`, `SKIP_BACKEND_INIT=true`
(CI/offline: init with `-backend=false`), `SOFT_FAIL_SECURITY`. No terragrunt binary available?
Fall back to static review: check 1.0-only policy violations, include-graph integrity, then
REVIEW mode checklist. `uv run python ~/.claude/skills/terragrunt-skill/scripts/detect_custom_resources.py [DIR]`
finds non-registry providers/modules needing research.

## DIAGNOSE workflow

1. Extract distinctive tokens from the error (e.g. "state lock", "Could not find").
2. `grep -in '<token>' references/error-patterns.md`; read matched `## ERROR:` sections.
3. No match → C7 search / docs.terragrunt.com troubleshooting; say the pattern wasn't in the
   embedded set.

## REVIEW workflow

Audit against best-practices.md as a checklist; report findings ordered by priority with the
practice name, why it matters, and the doc link. Include 1.0-policy violations (Hard policy
item 1) as findings.

## Provenance

This skill is original content (MIT). Its patterns and references trace to the public
Terragrunt documentation (<https://docs.terragrunt.com>); **Terragrunt** is © Gruntwork, Inc.
(MIT licensed). This skill is not affiliated with or endorsed by Gruntwork. The bundled
`scripts/validate.sh` invokes external tools when present — `terragrunt`, `tflint` (MPL-2.0),
and `trivy` (Apache-2.0) — but does not bundle them; their own licenses apply.
