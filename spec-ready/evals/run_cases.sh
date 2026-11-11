#!/bin/bash
# Run spec-ready's eval cases.
#   session cases: replay the scenario's turns into a real Claude Code session (claude -p, then
#     --resume per turn), in three arms: with spec-ready as a project skill, without it (the user's
#     own configuration, e.g. superpowers), and with Matt Pocock's to-spec as a project skill.
#     The session transcript and every written file are kept for grading.
#   gate-only cases: run gate.py directly on the fixture transcript (S6 runs with no transcript).
# Usage: run_cases.sh OUT_DIR [MODEL]     (MODEL defaults to sonnet)
set -u
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
MODEL="${2:-sonnet}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVALS="$SKILL_DIR/evals/evals.json"
TO_SPEC_URL="repos/mattpocock/skills/contents/skills/engineering/to-spec/SKILL.md"

field() { python3 -c "import json,sys;d=json.load(open('$EVALS'));c=[e for e in d['evals'] if e['id']==sys.argv[1]][0];print(json.dumps(c[sys.argv[2]]) if isinstance(c[sys.argv[2]],list) else c[sys.argv[2]])" "$1" "$2"; }
nth_turn() { python3 -c "import json,sys;print(json.loads(sys.argv[1])[int(sys.argv[2])])" "$1" "$2"; }

python3 -c "import json;[print(e['id'],e['mode']) for e in json.load(open('$EVALS'))['evals']]" |
while read -r id mode; do
  if [ "$mode" = gate-only ]; then
    d="$OUT/$id-gate"; rm -rf "$d"; mkdir -p "$d/home"
    python3 "$SKILL_DIR/evals/build_fixtures.py" "$d/fx" >/dev/null
    (cd "$d/fx/$id/repo" && HOME="$d/home" env -u CLAUDE_CODE_SESSION_ID python3 "$SKILL_DIR/scripts/gate.py" check \
       --proposals "$d/fx/$id/proposals.json" --out "$d/out" >"$d/gate-stdout.json" 2>"$d/gate-stderr.txt"
     echo "$?" >"$d/exit-code.txt")
    echo "$id gate-only done"
    continue
  fi
  turns="$(field "$id" turns)"
  count="$(python3 -c "import json,sys;print(len(json.loads(sys.argv[1])))" "$turns")"
  for arm in with without to-spec; do
    d="$OUT/$id-$arm"; rm -rf "$d"; mkdir -p "$d/tmp"
    python3 "$SKILL_DIR/evals/build_fixtures.py" "$d/fx" >/dev/null
    repo="$d/fx/$id/repo"
    if [ "$arm" = with ]; then
      mkdir -p "$repo/.claude/skills"
      cp -R "$SKILL_DIR" "$repo/.claude/skills/spec-ready"
      rm -rf "$repo/.claude/skills/spec-ready/evals" "$repo/.claude/skills/spec-ready/tests"
    elif [ "$arm" = to-spec ]; then
      mkdir -p "$repo/.claude/skills/to-spec"
      gh api "$TO_SPEC_URL" --jq .content | base64 -d >"$repo/.claude/skills/to-spec/SKILL.md"
    fi
    session=""
    n=0
    while [ "$n" -lt "$count" ]; do
      text="$(nth_turn "$turns" "$n")"
      resume=()
      [ -n "$session" ] && resume=(--resume "$session")
      (cd "$repo" && TMPDIR="$d/tmp" claude -p "$text" "${resume[@]}" --model "$MODEL" --output-format json \
         --allowedTools "Read,Write,Edit,Glob,Grep,Bash,Skill,Agent" --permission-mode acceptEdits \
         </dev/null >"$d/turn-$n.json" 2>>"$d/stderr.txt")
      session="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('session_id',''))" "$d/turn-$n.json" 2>/dev/null)"
      n=$((n + 1))
    done
    slug="$(cd "$repo" && pwd -P | tr '/' '-')"
    cp "$HOME/.claude/projects/$slug/$session.jsonl" "$d/session.jsonl" 2>/dev/null || echo "session file not found" >>"$d/stderr.txt"
    (cd "$repo" && git status --porcelain | grep -v '^?? .claude/' >"$d/git-status.txt"
     find . -name prd.md -o -name spec.md -o -name readiness.json | grep -v '^./.claude/' >"$d/written.txt")
    echo "$id $arm done"
  done
done
