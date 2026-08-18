#!/usr/bin/env bash
# One cell: anchor_run.sh <prompt-name> <replicate>
# Reads prompts/<prompt-name>.md, writes runs/<prompt-name>-<rep>.json
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
NAME="$1"; REP="$2"
PROMPT="$HERE/prompts/${NAME}.md"
OUT="$HERE/runs/${NAME}-${REP}.json"
[ -f "$PROMPT" ] || { echo "no prompt $NAME" >&2; exit 1; }
mkdir -p "$HERE/runs"

# Empty sandbox and every file tool disallowed: the member must work from the prompt
# alone. That also makes any `## What to consult` pointer inert -- deliberate here, since
# the pointer is identical in both conditions and cancels out of the comparison. Pointer
# FIRING is a different question and needs the opposite setup (see README).
SANDBOX="$(mktemp -d)"; trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX"
env -u ANTHROPIC_API_KEY claude \
  -p --model sonnet --safe-mode --no-session-persistence --output-format json \
  --disallowed-tools "Bash" "Read" "Write" "Edit" "Glob" "Grep" "WebFetch" "WebSearch" "Agent" "Task" \
  --max-budget-usd 0.60 \
  "$(cat "$PROMPT")" > "$OUT" 2>"$OUT.err" </dev/null || true
echo "$OUT"
