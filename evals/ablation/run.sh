#!/usr/bin/env bash
# One ablation cell: run.sh <arm A|B|C> <case id> <replicate n>
# Writes runs/<case>-<arm>-<n>.json
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ARM="$1"; CASE="$2"; REP="$3"
OUT="$HERE/runs/${CASE}-${ARM}-${REP}.json"

ARMFILE="$HERE/arms/${ARM}.md"
CASEFILE="$HERE/cases/${CASE}.txt"
[ -f "$ARMFILE" ] || { echo "no arm $ARM" >&2; exit 1; }
[ -f "$CASEFILE" ] || { echo "no case $CASE" >&2; exit 1; }

# Empty sandbox cwd: nothing on disk for any arm to discover, so arm B cannot
# read the pattern list it was stripped of.
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

ARGS=(
  -p
  --model sonnet
  --safe-mode
  --no-session-persistence
  --output-format json
  --disallowed-tools "Bash" "Read" "Write" "Edit" "Glob" "Grep" "WebFetch" "WebSearch" "Agent" "Task"
  --max-budget-usd 0.60
)

# FREEFORM=1 drops the schema. Required to test anything about OUTPUT SHAPE: the
# schema overrides output formatting, so an arm that ablates a report template or
# a scoring rubric is guaranteed to look like a null while the schema is on. That
# is a property of the harness, not a finding about the skill.
if [ "${FREEFORM:-0}" != "1" ]; then
  ARGS+=(--json-schema "$(cat "$HERE/schema.json")")
else
  mkdir -p "$HERE/runs-free"
  OUT="$HERE/runs-free/${CASE}-${ARM}-${REP}.json"
fi

if [ -s "$ARMFILE" ]; then
  ARGS+=(--append-system-prompt "$(cat "$ARMFILE")")
fi

cd "$SANDBOX"
env -u ANTHROPIC_API_KEY claude "${ARGS[@]}" "$(cat "$CASEFILE")" > "$OUT" 2>"$OUT.err" </dev/null || true
echo "$OUT"
