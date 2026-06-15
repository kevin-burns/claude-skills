# Contributing

Notes for authoring and maintaining the skills in this repo. The most load-bearing one is
the **bundled-script invocation convention** below — get it wrong and a skill silently breaks
in real use.

## Invoking a skill's bundled scripts (absolute-path + uv convention)

A skill almost never runs from *this* repo — it runs from whatever project the user is working
in (an Azure IaC repo, an app repo, anywhere). So any command in a `SKILL.md` that invokes a
bundled helper must work **regardless of the current working directory**.

### The problem to avoid

A relative path like `uv run skill-name/scripts/helper.py` only resolves when the shell is
sitting in this repo's root. Run from anywhere else, `uv` aborts with
`Failed to spawn … No such file or directory` **before the script ever runs** — so no JSON /
no output is produced, and the model tends to "work around" it by scraping the upstream site or
answering from memory. That defeats the entire point of a deterministic helper. (This actually
happened; it's why the convention exists.)

Two more traps on top of the path:

- **`uv` isn't always on `PATH`.** Non-interactive shells frequently drop `~/.local/bin` or the
  Homebrew bin, so a bare `uv …` fails with `command not found`.
- **`VAR="…"; $VAR` doesn't word-split in zsh.** The repo's Bash tool runs zsh, where
  `AZ="uv run …"; $AZ status` is treated as one bogus command name and emits nothing. Shell
  state also doesn't persist between separate tool calls.

### The convention

1. **Absolute path, from the skill's base directory.** When a skill loads, its base directory
   is announced (usually `~/.claude/skills/<skill-name>`, or a plugin path). Reference the
   script there — never a relative path.
2. **Use a shell function, not a variable.** Define it at the **start of each command block**
   (re-declare per block; state doesn't persist). A function passes arguments correctly under
   both bash and zsh.
3. **Name the function so it can't shadow a real CLI.** `az` is the Azure CLI → use `azadv`;
   `terraform` exists → use `tfreg`. Pick an unambiguous prefix.
4. **Prefer `uv`; resolve it even when it's off `PATH`.** Only fall back to `python3` when the
   script is **stdlib-only** (see the decision rule below).
5. **If the helper still won't run, fix the runner/path — don't fall back to scraping or
   guessing.** State that plainly in the `SKILL.md` so the model doesn't improvise.

### Canonical snippet

```bash
# uv is the preferred runner; resolve it even when it's not on a bare PATH:
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
myskill() { "$UV" run "$HOME/.claude/skills/my-skill/scripts/helper.py" "$@"; }   # use the announced base dir

myskill status   # confirms the runner + path resolve before doing real work
```

For a script **without** PEP 723 inline metadata, use `"$UV" run python "<path>"` (the explicit
`python` form runs reliably regardless of metadata).

### uv vs python3 — the decision rule

| Script | How to tell | Runner in `SKILL.md` |
|---|---|---|
| **stdlib-only** | no PEP 723 `# dependencies = [...]` block; imports only the standard library | `uv run` **or** `python3` — document python3 as the fallback |
| **has third-party deps** | declares `dependencies` in a PEP 723 `# /// script` block (e.g. `jinja2`, `google-genai`) | **uv required** — keep uv resolvable, but do *not* offer a python3 fallback (it would fail on the missing package) |

uv is preferred either way (it pins `requires-python` from the inline metadata). python3 is only
a safety net for the stdlib-only case.

### Worked examples in this repo

| Skill | Function | Runner | Notes |
|---|---|---|---|
| [azadvertizer](./azadvertizer) | `azadv` | uv-or-python3 | stdlib-only; name avoids the `az` CLI |
| [terraform-registry](./terraform-registry) | `tfreg` | `uv run python` or python3 | stdlib-only; name avoids the `terraform` CLI |
| [source-snapshot](./source-snapshot) | `srcsnap` | `uv run python` or python3 | stdlib-only |
| [report-builder](./report-builder) | `rbuild` | uv-only | PEP 723 jinja2 dep — no python3 fallback |
| [nano-banana-pro-json](./nano-banana-pro-json) | — (inline) | uv-only | PEP 723 google-genai/pillow deps |
| [terragrunt-skill](./terragrunt-skill) | — (inline) | `bash <abs>` + uv/python3 | shell suite + a stdlib Python helper |

### Workflows (`*.workflow.js`)

Same rule for a workflow dispatched via the Workflow tool: pass an **absolute** `scriptPath`
(the skill's announced base directory), e.g.
`~/.claude/skills/dev-fleet/dev-story.workflow.js` — a relative `dev-fleet/…` won't resolve
from another repo. See [dev-fleet](./dev-fleet).

## General skill conventions

- Each skill lives in its own directory with a `SKILL.md` (`name` + `description` frontmatter).
- A skill that wraps an external tool or service carries a **Provenance** note in its
  `SKILL.md` crediting the upstream project and its license.
- Prefer stdlib-only helpers; declare any third-party deps via PEP 723 inline metadata so
  `uv run` is self-contained (no separate install step).
- Ship a deterministic, offline eval under `evals/` where the behavior is objectively checkable
  (run with `uv run python grade.py`). Add a test when you add behavior.
- All skill content here is MIT licensed (see [`LICENSE`](./LICENSE)).
