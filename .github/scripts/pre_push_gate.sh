#!/usr/bin/env bash
# Pre-push gate: run what CI would fail on before anything leaves the machine.
#
# Why: pre-commit only sees staged files, and the test suites ran only in CI, so a
# green commit could still turn the public main red (the 2026-09-06 contract-test
# break, the 2026-09-24 bandit B310). The global rule is "ask before every push";
# this makes the push itself refuse a tree CI would reject.
#
# What it runs:
#   1. every prek hook over the whole repo (about 6 seconds);
#   2. the test suites of each top-level skill directory the pushed commits touch,
#      discovered the same way ci.yml does (tests/ with pytest, scripts/tests/ with
#      unittest, shell suites one file at a time).
# CI still runs every suite and the offline evals; this is the fast local subset.
#
# Called from the git pre-push hook with git's own stdin:
#   <local ref> <local sha> <remote ref> <remote sha>
# Fails closed: a missing prek or pytest blocks the push rather than skipping.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if ! command -v prek >/dev/null 2>&1; then
  echo "pre-push gate: prek not found; refusing to push without the hooks" >&2
  exit 1
fi
echo "pre-push gate: prek run --all-files"
if ! prek run --all-files >/dev/null 2>&1; then
  prek run --all-files 2>&1 | grep -vE 'Passed$|Skipped$' >&2 || true
  echo "pre-push gate: hooks failed" >&2
  exit 1
fi

zero=0000000000000000000000000000000000000000
touched=""
while read -r _local_ref local_sha _remote_ref remote_sha; do
  [ -n "${local_sha:-}" ] || continue
  [ "$local_sha" = "$zero" ] && continue          # deleting a remote branch
  if [ "$remote_sha" = "$zero" ]; then
    base=$(git merge-base "$local_sha" origin/main 2>/dev/null || true)
    [ -n "$base" ] || base=$(git rev-list --max-parents=0 "$local_sha" | tail -1)
  else
    base="$remote_sha"
  fi
  touched="$touched
$(git diff --name-only "$base" "$local_sha" | awk -F/ 'NF>1 {print $1}')"
done

status=0
ran=0
while IFS= read -r d; do
  [ -n "$d" ] && [ -d "$d" ] || continue
  if [ "$d" = ".github" ]; then
    # ci.yml names this suite on its own ("Mirror builder tests"): pytest, run from
    # the repo root. It is not a skill's unittest suite.
    ran=$((ran + 1)); echo "pre-push gate: .github/scripts/tests (pytest)"
    uv run --quiet --with pytest python -m pytest .github/scripts/tests -q -p no:cacheprovider || status=1
    continue
  fi
  if [ -d "$d/scripts/tests" ]; then
    ran=$((ran + 1)); echo "pre-push gate: $d/scripts/tests (unittest)"
    ( cd "$d/scripts" && uv run --quiet python -m unittest discover -s tests -q ) || status=1
  fi
  if [ -d "$d/tests" ]; then
    if compgen -G "$d/tests/test_*.py" >/dev/null || compgen -G "$d/tests/*_test.py" >/dev/null; then
      ran=$((ran + 1)); echo "pre-push gate: $d/tests (pytest)"
      ( cd "$d" && uv run --quiet --with pytest python -m pytest tests -q -p no:cacheprovider ) || status=1
    elif compgen -G "$d/tests/*.sh" >/dev/null; then
      for t in "$d"/tests/*.sh; do
        ran=$((ran + 1)); echo "pre-push gate: $t"
        ( cd "$d" && bash "tests/${t##*/}" ) || status=1
      done
    fi
  fi
done < <(printf '%s\n' "$touched" | sort -u)

if [ "$status" -ne 0 ]; then
  echo "pre-push gate: a test suite failed; nothing was pushed" >&2
  exit 1
fi
echo "pre-push gate: passed (hooks + $ran suite(s))"
