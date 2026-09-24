#!/usr/bin/env bash
# The bandit gate, in ONE place. CI's lint job and the pre-commit hook both run this
# file, so the two cannot disagree about what counts as a finding. Before 2026-09-24
# the step lived inline in ci.yml only, and a B310 in a new script passed every local
# hook and turned main red. Why baselined, why medium, why tracked files only: see the
# comment above the bandit step in .github/workflows/ci.yml.
set -euo pipefail

pyfiles_list="$(mktemp)"
report="$(mktemp)"
trap 'rm -f "$pyfiles_list" "$report"' EXIT

git ls-files '*.py' | grep -v 'agents/.*/evals/fixtures' > "$pyfiles_list"
printf 'scanning %s tracked python file(s)\n' "$(wc -l < "$pyfiles_list" | tr -d ' ')"

# `|| true` because bandit exits non-zero merely for HAVING findings. The verdict comes
# from reading the report, never from this exit code -- bandit also exits 0 when it
# could not read its input at all.
# A read loop rather than `mapfile`: mapfile is bash 4+, and macOS ships bash 3.2.
pyfiles=()
while IFS= read -r f; do pyfiles+=("$f"); done < "$pyfiles_list"
uvx bandit@1.9.4 --severity-level medium \
  -b .bandit-baseline.json -f json -o "$report" \
  "${pyfiles[@]}" > /dev/null 2>&1 || true
python3 .github/scripts/check_bandit.py "$report"
