---
name: terragrunt-skill
license: MIT
description: Comprehensive Terragrunt 1.x skill for generating, validating, reviewing, and debugging Terragrunt configurations (root.hcl, terragrunt.hcl, terragrunt.stack.hcl, units, stacks, catalogs) across AWS, Azure, and GCP. Use this skill whenever the user mentions Terragrunt, terragrunt.hcl, root.hcl, stack files, units, HCL orchestration of OpenTofu/Terraform, remote state DRY configuration, run --all, dependency blocks between modules, or asks to scaffold/lint/diagnose multi-environment IaC layouts — even if they don't say "Terragrunt" explicitly but show Terragrunt HCL.
---

# Terragrunt (1.0.x)

Single skill for all Terragrunt work, organized as a router: identify the task mode below,
read ONLY the listed reference(s), then act. References are grep-friendly — prefer
`grep` lookups over reading whole files.

## Hard policy

1. **Terragrunt 1.0.x only.** Never generate or recommend pre-1.0 forms: `run-all`,
   `plan-all`, `hclfmt`, `hclvalidate`, `graph-dependencies`, `validate-inputs`,
   `terragrunt-` prefixed flags, the `skip` attribute, `retryable_errors`, or bare
   `find_in_parent_folders()` pointing at a root `terragrunt.hcl`. If user code contains
   these, flag them and propose the 1.0 form.
2. **Fact-based generation.** Every generated pattern must trace to a documented Gruntwork
   pattern (references here carry doc links to docs.terragrunt.com). Don't invent layouts.
3. **Knowledge freshness.** Embedded references were verified against Terragrunt 1.0.x
   (June 2026). For anything newer, niche, or not found in the references, use the C7
   search skill (Context7) or fetch docs.terragrunt.com directly — do not guess.
4. Terragrunt orchestrates **OpenTofu or Terraform**; don't assume one unless the user's
   repo indicates it (`.terraform-version`, `engine` block, provider constraints).

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

## Reference index (grep, don't read whole files)

- `references/architecture-patterns.md` — layout patterns, env-agnostic root rule, unit/stack
  model, dependency wiring, runtime control. Headings: `## PATTERN:`
- `references/hcl-blocks.md` — all HCL blocks (terraform, remote_state, dependency, include,
  generate, locals, inputs, feature, exclude, errors...). `grep '^## BLOCK: dependency'`
- `references/functions.md` — built-in functions by category. `grep '^## FUNCTION: get_env'`
- `references/cli-reference.md` — full 1.0 command tree + `--filter` system.
  `grep '^## COMMAND: stack run'`
- `references/error-patterns.md` — 66 diagnosed errors with causes/solutions. Grep error
  keywords first: `grep -in 'state lock' references/error-patterns.md`
- `references/best-practices.md` — practices with priority/rationale/antipatterns, plus
  `## COMPARISON:` (e.g. dependency vs dependencies) and `## DECISION:` guides
- `references/advanced-examples.md` — 21 worked examples. `grep '^## EXAMPLE:'`

## Templates

- `templates/root/root.hcl` — root config (environment-agnostic)
- `templates/child/terragrunt.hcl` — unit including root + env.hcl
- `templates/env/env.hcl` — per-environment locals
- `templates/stack/terragrunt.stack.hcl`, `templates/catalog/` — explicit stacks & catalog units
- `templates/module/terragrunt.hcl` — standalone unit
- `templates/backends/` — remote_state for S3/GCS/Azure, essential + advanced tiers.
  **Azure caveat:** `azurerm` passes through to the native backend; Terragrunt-native
  bootstrap for Azure is experimental — do not claim `backend bootstrap` provisions Azure.
- `templates/providers/` — provider `generate` blocks

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
