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

- The transcript is a file the agent could edit. The gate records a hash of each cited turn and
  fails if it changes, which makes tampering a deliberate act; it does not make it impossible.
- Codex: transcripts are read from `~/.codex/sessions/`. `codex exec --help` (checked 2026-11-11)
  offers `--ephemeral` and a read-only sandbox but no way to turn tools off, so the gate does not
  call it as a verifier; Codex sessions use the subagent or session-model path, or a local Ollama
  model.
- Calibration: no verifier has been calibrated on planning conversations yet. Your overrides are
  recorded in `readiness.json` so that it can be.
