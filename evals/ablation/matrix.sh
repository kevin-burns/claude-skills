#!/usr/bin/env bash
# Full matrix: 4 cases x 3 arms x 3 replicates = 36 runs, 3 at a time.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

CASES="${CASES:-1 3 8 9}"
ARMS="${ARMS:-A B C}"
REPS="${REPS:-1 2 3}"

n=0
for c in $CASES; do
  for a in $ARMS; do
    for r in $REPS; do
      if [ "${FREEFORM:-0}" = "1" ]; then
        out="$HERE/runs-free/${c}-${a}-${r}.json"
      else
        out="$HERE/runs/${c}-${a}-${r}.json"
      fi
      [ -s "$out" ] && { echo "skip $c-$a-$r"; continue; }
      "$HERE/run.sh" "$a" "$c" "$r" &
      n=$((n+1))
      if [ $((n % 3)) -eq 0 ]; then wait; fi
    done
  done
done
wait
results=0
for f in "$HERE"/runs/*.json; do
  [ -e "$f" ] && results=$((results + 1))
done
echo "matrix complete: $results result files"
