#!/bin/bash
# When li-digest loses an archetype, sweep.log must say WHICH one.
#
# On 2026-09-01 the failing lane was `em` — engineering management, the user's
# stated primary target — and the log said only "ARCHETYPE(S) FAILED". Nothing
# distinguished losing the most valuable lane from losing the least, so the run
# looked like ordinary noise. The names are already in .li.log; this pins that
# they reach the log line a human actually reads.
#
# Run: bash examples/tests/test-sweep-archetype-failure.sh

set -uo pipefail
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/job-feeds-sweep.sh"
PASS=0; FAIL=0

run_sweep() {   # run_sweep <li-digest-exit> <li-digest-stderr>
    OUT="$(mktemp -d)"; local bin="$OUT/bin"; mkdir -p "$bin"
    cat > "$bin/li-assist" <<'EOF'
#!/bin/bash
[ "$1" = "auth" ] && { echo '{"logged_in":true,"stale":false,"reauth_days":14,"captured_at":"2026-09-01T06:00:00Z"}'; exit 0; }
exit 0
EOF
    cat > "$bin/li-digest" <<EOF
#!/bin/bash
printf '%s\n' "$2" >&2
echo '[{"bucket":"fresh","title":"Stub Role"}]'
exit $1
EOF
    cat > "$bin/li-report" <<'EOF'
#!/bin/bash
exit 0
EOF
    cat > "$bin/osascript" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$OUT/notifications.txt"
EOF
    chmod +x "$bin"/*
    PATH="$bin:$PATH" JOB_SWEEP_OUTDIR="$OUT" bash "$SCRIPT" >/dev/null 2>&1
}

check() {  # check <description> <file> <needle> <yes|no>
    local desc="$1" file="$2" needle="$3" want="$4" got=no
    grep -qF -- "$needle" "$file" 2>/dev/null && got=yes
    if [ "$got" = "$want" ]; then echo "  ok   $desc"; PASS=$((PASS+1))
    else echo "  FAIL $desc (wanted $want, got $got)"; FAIL=$((FAIL+1)); fi
}

echo "== one archetype fails =="
run_sweep 1 "li-digest: archetype 'em' failed (net::ERR_NETWORK_CHANGED) — continuing
li-digest: 1 archetype(s) failed: em"
check "sweep.log flags the failure"        "$OUT/sweep.log" "ARCHETYPE(S) FAILED" yes
check "sweep.log NAMES the lane"           "$OUT/sweep.log" "ARCHETYPE(S) FAILED: em" yes
check "a notification carries the detail"  "$OUT/notifications.txt" "em" yes

echo "== several fail =="
run_sweep 1 "li-digest: 2 archetype(s) failed: em, finops"
check "every named lane reaches the log"   "$OUT/sweep.log" "FAILED: em, finops" yes

echo "== a clean run says nothing about archetypes =="
run_sweep 0 "li-digest: sweeping em…"
check "no failure marker on a clean run"   "$OUT/sweep.log" "ARCHETYPE(S) FAILED" no

echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
