#!/bin/bash
# Run spec-to-tickets' eval cases: replay each case's turns into a real Claude Code session
# (claude -p, then --resume per turn) in three arms: with spec-to-tickets (and spec-ready, which it
# uses for overrides) as project skills, without them, and with Matt Pocock's to-tickets fetched
# from github.com/mattpocock/skills (MIT) and called by name (it sets disable-model-invocation).
# Usage: run_cases.sh OUT_DIR [MODEL] [CASES] [ARMS]
set -u
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
MODEL="${2:-sonnet}"
CASES="${3:-}"
ARMS="${4:-with without to-tickets}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVALS="$SKILL_DIR/evals/evals.json"
TO_TICKETS_URL="repos/mattpocock/skills/contents/skills/engineering/to-tickets/SKILL.md"

turns_of() { python3 -c "import json,sys;d=json.load(open('$EVALS'));print(json.dumps([e for e in d['evals'] if e['id']==sys.argv[1]][0]['turns']))" "$1"; }
nth() { python3 -c "import json,sys;print(json.loads(sys.argv[1])[int(sys.argv[2])])" "$1" "$2"; }

python3 -c "import json;[print(e['id']) for e in json.load(open('$EVALS'))['evals']]" |
while read -r id; do
  if [ -n "$CASES" ] && [[ " $CASES " != *" $id "* ]]; then continue; fi
  turns="$(turns_of "$id")"
  count="$(python3 -c "import json,sys;print(len(json.loads(sys.argv[1])))" "$turns")"
  for arm in $ARMS; do
    d="$OUT/$id-$arm"; rm -rf "$d"; mkdir -p "$d/tmp"
    python3 "$SKILL_DIR/evals/build_fixtures.py" "$d/fx" >/dev/null
    repo="$d/fx/$id/repo"
    if [ "$arm" = with ]; then
      mkdir -p "$repo/.claude/skills"
      for skill in spec-to-tickets spec-ready; do
        cp -R "$SKILL_DIR/../$skill" "$repo/.claude/skills/$skill"
        rm -rf "$repo/.claude/skills/$skill/evals" "$repo/.claude/skills/$skill/tests"
      done
    elif [ "$arm" = to-tickets ]; then
      mkdir -p "$repo/.claude/skills/to-tickets"
      gh api "$TO_TICKETS_URL" --jq .content | base64 -d >"$repo/.claude/skills/to-tickets/SKILL.md"
    fi
    touch "$d/start"
    session=""
    n=0
    while [ "$n" -lt "$count" ]; do
      text="$(nth "$turns" "$n")"
      if [ "$arm" = to-tickets ] && [ "$n" -eq 0 ]; then text="/to-tickets $text"; fi
      resume=()
      [ -n "$session" ] && resume=(--resume "$session")
      (cd "$repo" && TMPDIR="$d/tmp" claude -p "$text" ${resume[@]+"${resume[@]}"} --model "$MODEL" --output-format json \
         --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill,Agent" --permission-mode acceptEdits \
         </dev/null >"$d/turn-$n.json" 2>>"$d/stderr.txt")
      session="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('session_id',''))" "$d/turn-$n.json" 2>/dev/null)"
      n=$((n + 1))
    done
    found="$(find "$HOME/.claude/projects" -maxdepth 2 -name "$session.jsonl" 2>/dev/null | head -1)"
    if [ -n "$session" ] && [ -n "$found" ]; then cp "$found" "$d/session.jsonl"; else echo "session file not found" >>"$d/stderr.txt"; fi
    (cd "$repo" && find . -path ./.git -prune -o -path ./.claude -prune -o -type f -newer "$d/start" -print >"$d/written.txt")
    echo "$id $arm done"
  done
done
