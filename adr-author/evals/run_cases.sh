#!/bin/bash
# Run every behaviour case twice, with the skill installed as a project skill and without it.
# Each case and arm gets a fresh fixture, its own TMPDIR (so scratch files never leak between
# cases) and a closed stdin (so the case list is never read as part of a prompt).
# Usage: run_cases.sh OUT_DIR [MODEL]     (MODEL defaults to sonnet)
set -u
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
MODEL="${2:-sonnet}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVALS="$SKILL_DIR/evals/evals.json"
python3 -c "import json;[print(e['id'],e['fixture']) for e in json.load(open('$EVALS'))['evals']]" |
while read -r id fixture; do
  for arm in with without; do
    d="$OUT/$id-$arm"; rm -rf "$d"; mkdir -p "$d/tmp"
    python3 "$SKILL_DIR/evals/build_fixtures.py" "$d/fx" >/dev/null
    repo="$d/fx/$fixture"
    if [ "$arm" = with ]; then
      mkdir -p "$repo/.claude/skills"
      cp -R "$SKILL_DIR" "$repo/.claude/skills/adr-author"
      rm -rf "$repo/.claude/skills/adr-author/evals/runs" "$repo/.claude/skills/adr-author/tests"
    fi
    prompt="$(python3 -c "import json;print([e for e in json.load(open('$EVALS'))['evals'] if e['id']=='$id'][0]['prompt'])")"
    (cd "$repo" && TMPDIR="$d/tmp" claude -p "$prompt" --model "$MODEL" --output-format stream-json --verbose \
       --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill" --permission-mode acceptEdits \
       </dev/null >"$d/transcript.jsonl" 2>"$d/stderr.txt")
    (cd "$repo" && git status --porcelain | grep -v '^?? .claude/' >"$d/git-status.txt"; git log --oneline >"$d/git-log.txt")
    echo "$id $arm done"
  done
done
