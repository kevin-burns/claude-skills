# claude-skills

A collection of [Claude Code](https://claude.com/claude-code) skills and subagents I build and maintain, kept here so they can be versioned and shared openly. Each skill lives in its own directory with a `SKILL.md`; subagents live under [`agents/`](./agents); some bundle scripts, evals, or reference files.

All skills here are MIT licensed (see [`LICENSE`](./LICENSE)). Skills that wrap an external tool or service carry a **Provenance** note in their `SKILL.md` crediting the upstream project and its license — the MIT license covers the skill content, not the wrapped tools.

## Skills

| Skill | What it does | Wraps |
|---|---|---|
| [clear-and-human](./clear-and-human) | Construct, review, score, and rewrite prose so it reads human, not AI | — |
| [hook-and-human](./hook-and-human) | Write, punch up, and review persuasive marketing copy without fabricating | — |
| [c7search](./c7search) | Fetch up-to-date library docs via the `c7search` CLI | [Context7](https://context7.com) API |
| [markdown-converter](./markdown-converter) | Convert PDF/Office/HTML/media files to Markdown | [markitdown](https://github.com/microsoft/markitdown) (MS, MIT) |
| [nano-banana-pro-json](./nano-banana-pro-json) | Generate and edit images with structured JSON control | Google Gemini image API |
| [convert-to-webp](./convert-to-webp) | Convert images to WebP for web projects | [libwebp](https://developers.google.com/speed/webp) `cwebp` / macOS `sips` |
| [social-image-prep](./social-image-prep) | Resize and format images for social platforms | `sips` / [ImageMagick](https://imagemagick.org) / [Pillow](https://python-pillow.org) |
| [terragrunt-skill](./terragrunt-skill) | Generate, validate, review, and debug Terragrunt 1.x configs across AWS/Azure/GCP | — |
| [terraform-registry](./terraform-registry) | Provider-agnostic CLI to search/inspect the Terraform Registry via its JSON API (no scraping) | [Terraform Registry](https://registry.terraform.io) API |
| [source-snapshot](./source-snapshot) | Fetch external data once into pinned, provenance-stamped artifacts; resilient extractor fallback | [markitdown](https://github.com/microsoft/markitdown) / Defuddle / Readability |
| [dev-fleet](./dev-fleet) | Orchestration playbook driving the agent fleet through build → verify → review → commit | — |
| [report-builder](./report-builder) | Build self-contained single-page HTML reports/dashboards from data | [Jinja2](https://jinja.palletsprojects.com) / [Bootstrap 5](https://getbootstrap.com) / [Chart.js](https://www.chartjs.org) / [Plotly](https://plotly.com/javascript/) |
| [ux-audit](./ux-audit) | Heuristic usability + accessibility audit of rendered web pages (Nielsen + WCAG 2.2) | — |

## Agents

Subagents for software-development work, coordinated by the `dev-fleet` skill. Each is a `*.md` with frontmatter (`name`, `description`, `tools`, `model`) and a system-prompt body. Architecture and rationale: [`docs/agent-fleet-architecture.md`](./docs/agent-fleet-architecture.md).

| Agent | Role | Model |
|---|---|---|
| [azure-architect](./agents/azure-architect.md) | Enterprise-scale Azure / Cloud Adoption Framework design — governance, subscriptions, networking, IaC review | opus |
| [fact-verifier](./agents/fact-verifier.md) | Verify claims/code against authoritative sources — cite, refute, or return the lookup; never assert from memory | sonnet |
| [code-builder](./agents/code-builder.md) | Implement scoped changes TDD-style in an isolated worktree; commit on a branch, never push/merge/apply | sonnet |
| [code-reviewer](./agents/code-reviewer.md) | Advisory review for correctness, edge cases, contracts, security, tests — findings, not a gate | sonnet |
| [docs-reviewer](./agents/docs-reviewer.md) | Review docs (READMEs, ADRs, runbooks) for completeness, clarity, correctness, and audience fit | sonnet |
| [ux-auditor](./agents/ux-auditor.md) | Audit a rendered web page for usability/accessibility; renders via agent-browser/playwright-cli, fans out one per page (reads `ux-audit`) | sonnet |
| [commit-pr](./agents/commit-pr.md) | Write commit and PR/MR messages (reads `commit-style`) | haiku |
| [commit-style](./agents/commit-style.md) | Commit/PR style playbook used by `commit-pr` | — |

Several agents ship a deterministic behavioral eval under `agents/<name>/evals/` (run with `uv run python grade.py`).

## Install

Symlink any skill into your personal skills directory:

```bash
ln -s "$(pwd)/clear-and-human" ~/.claude/skills/clear-and-human
```

Subagents install the same way, into `~/.claude/agents/`:

```bash
ln -s "$(pwd)/agents/fact-verifier.md" ~/.claude/agents/fact-verifier.md
```

Symlinking (rather than copying) keeps this repo the single source of truth — edits here are picked up immediately.

### Requirements per skill

- **c7search** — the `c7search` binary (`go install github.com/kevin-burns/c7search@latest`). A `CONTEXT7_API_KEY` is optional.
- **markdown-converter** — `uv` (uses `uvx markitdown`, no install needed).
- **nano-banana-pro-json** — `uv` and a `GEMINI_API_KEY` environment variable. No key is bundled.
- **convert-to-webp** — `cwebp` (`brew install webp`) or macOS `sips`. No install needed on macOS.
- **social-image-prep** — `sips` (macOS), ImageMagick, or `uv` (for the Pillow fallback). Uses whichever is present.
- **terragrunt-skill** — works as static review with no tooling; the bundled `scripts/validate.sh` uses `terragrunt` (1.0.x), plus optional `tflint` and `trivy` if present. `scripts/detect_custom_resources.py` runs on Python 3.
- **terraform-registry** — Python 3 (stdlib only). `search`/`inspect-module` need only network access; `inspect-resource`/`refresh-schema` additionally need the `terraform` CLI.
- **source-snapshot** — Python 3 (stdlib only). Uses whichever extractor is present: `markitdown` (via `uv`, the reliable fallback), and optionally Defuddle (`npx defuddle-cli`, set `SNAPSHOT_DEFUDDLE_CMD`) or a Readability CLI for prose. Degrades gracefully when one is missing.
- **dev-fleet** — no tooling; it's an orchestration playbook for the agents above.
- **report-builder** — `uv` (the bundled `scripts/render.py` declares its deps via PEP 723 inline metadata; run with `uv run`). Bootstrap/Chart.js/Plotly load from CDN, or vendor them for offline reports.
- **ux-audit / ux-auditor** — a browser driver to render pages: prefers `agent-browser`, falls back to `playwright-cli`; uses whichever is installed. Degrades to a static-HTML audit (clearly flagged) if neither is present.
