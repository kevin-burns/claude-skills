# spec-ready

Checks that a plan is ready to spec, from the person's own words, then writes the PRD (why) and the
spec (how). See `SKILL.md` for how the agent uses it; this file is for the person installing it.

## What it needs

Nothing beyond the agent: the scripts are Python 3.12+ standard library, run with `uv run` or
`python3`. With the `claude` CLI on `PATH`, the gate verifies each item with a headless Haiku call
(one call per item, no tools, no saved session). Without it, the agent dispatches a subagent with a
brief the script builds.

## Optional: a local verifier

To add a local System One model as a second opinion, set both:

```bash
export SPEC_READY_DECIDER=ollama:<model>
export OLLAMA_HOST=http://<your-ollama-host>:11434
```

When the headless verifier and the local model disagree, the item becomes a question to you.

## Optional: the guard hook

`hooks/guard.py` is a PreToolUse hook that refuses to write `prd.md` or `spec.md` until the
`readiness.json` beside them has passed. It stops another skill's spec step from slipping past the
gate. The skill never installs it. To opt in, add to your Claude Code settings:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{"type": "command", "command": "python3 /path/to/spec-ready/hooks/guard.py"}]
      }
    ]
  }
}
```

## Limits

What the gate cannot stop, stated plainly:

- **Editing the transcript.** It is a file the agent could edit. The gate records a hash of each
  cited turn and fails if it changes, which makes changing a turn a deliberate act. Not detected:
  appending a turn (for example through `claude -p --resume <session> "<text>"`), or writing a
  whole copy, which shows up only in the transcript path recorded in readiness.json.
- **Editing readiness.json.** A hand-edited verdict is not re-checked by the guard.
- **The guard's reach.** It watches the Write and Edit tools on files named `prd.md` and `spec.md`;
  a write through Bash or under another name is not seen.
- **Codex.** Transcripts are read from `~/.codex/sessions/`. `codex exec --help` (checked
  2026-11-11) offers `--ephemeral` and a read-only sandbox but no way to turn tools off, so the gate
  does not call it as a verifier; Codex sessions use the subagent or session-model path, or a local
  Ollama model.
- **Calibration.** No verifier has been calibrated on planning conversations yet. Overrides are
  recorded in readiness.json so that it can be.
