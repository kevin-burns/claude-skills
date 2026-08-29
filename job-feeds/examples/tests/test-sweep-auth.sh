#!/bin/bash
# Tests for the li-assist auth-staleness branches of job-feeds-sweep.sh.
#
# Why these exist: on 2026-08-19 the sweep stopped covering LinkedIn for two
# consecutive runs because the session crossed li-assist's 14-day re-auth
# policy. The skip itself was correct and even fired a notification -- but it
# arrived only AFTER the session was already dead, blended into the routine
# "Daily job sweep" message, and went unnoticed. These tests pin the two
# behaviours added in response: an early warning while the session still
# works, and a dedicated notification that is visually distinct from the
# routine one.
#
# Run: bash examples/tests/test-sweep-auth.sh

set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/job-feeds-sweep.sh"
PASS=0
FAIL=0

# run_sweep <auth-json> -> populates $OUT with a temp dir containing the run's
# sweep.log and the notifications the run fired.
run_sweep() {
    OUT="$(mktemp -d)"
    local bin="$OUT/bin"
    mkdir -p "$bin"

    # Stub li-assist: only `auth status --json` is exercised here.
    cat > "$bin/li-assist" <<EOF
#!/bin/bash
[ "\$1" = "auth" ] && { cat <<'JSON'
$1
JSON
exit 0; }
exit 0
EOF

    # Stub li-digest: emits one in-window row so the happy path renders.
    cat > "$bin/li-digest" <<'EOF'
#!/bin/bash
echo '[{"bucket":"fresh","title":"Stub Role"}]'
exit 0
EOF

    cat > "$bin/li-report" <<'EOF'
#!/bin/bash
exit 0
EOF

    # Stub osascript: record each notification instead of displaying it.
    cat > "$bin/osascript" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$OUT/notifications.txt"
exit 0
EOF

    chmod +x "$bin"/*
    touch "$OUT/notifications.txt"

    # HOME is redirected so the real job_feeds.py is absent: these tests cover
    # the LinkedIn half only, and job-feeds is deliberately independent of it.
    env -i PATH="$bin:/usr/bin:/bin" HOME="$OUT/home" \
        JOB_SWEEP_OUTDIR="$OUT" bash "$SCRIPT" >/dev/null 2>&1
}

check() {  # check <description> <haystack-file> <needle> <expect: yes|no>
    local desc="$1" file="$2" needle="$3" expect="$4"
    if grep -qF -- "$needle" "$file" 2>/dev/null; then found=yes; else found=no; fi
    if [ "$found" = "$expect" ]; then
        PASS=$((PASS+1)); printf '  ok   %s\n' "$desc"
    else
        FAIL=$((FAIL+1))
        printf '  FAIL %s\n       expected %s to be present=%s, was present=%s\n' \
            "$desc" "$needle" "$expect" "$found"
        printf '       --- %s ---\n' "$file"; sed 's/^/       /' "$file"
    fi
}

echo "== session expiring soon (age 11.5 of 14) =="
run_sweep '{"logged_in":true,"stale":false,"age_days":11.5,"reauth_days":14}'
check "sweep.log flags the coming expiry" "$OUT/sweep.log" "AUTH EXPIRES" yes
check "a notification mentions re-login"  "$OUT/notifications.txt" "li-assist auth login" yes
check "the sweep still ran"               "$OUT/sweep.log" "fresh" yes

echo "== session fresh (age 2 of 14) =="
run_sweep '{"logged_in":true,"stale":false,"age_days":2.0,"reauth_days":14}'
check "no expiry warning in the log"          "$OUT/sweep.log" "AUTH EXPIRES" no
check "no re-login nag in the notification"   "$OUT/notifications.txt" "li-assist auth login" no

# li-assist marshals age_days as `float64` with `omitempty`
# (cmd/li-assist/auth.go), so the field VANISHES from the JSON whenever it
# rounds to 0 -- i.e. for any session under ~1.2h old. A warning that reads
# age_days therefore cannot compute at all on a fresh session, and would go
# silent for a stale one too if the field ever dropped for another reason.
# captured_at is always present, so the age is derived from that instead.
echo "== age_days absent (omitempty), captured_at 12 days ago =="
run_sweep "$(printf '{"logged_in":true,"stale":false,"captured_at":"%s","reauth_days":14}' \
    "$(python3 -c "import datetime;print((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=12)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))")")"
check "warns from captured_at alone" "$OUT/sweep.log" "AUTH EXPIRES" yes

echo "== age_days absent, session brand new (today's real case) =="
run_sweep "$(printf '{"logged_in":true,"stale":false,"captured_at":"%s","reauth_days":14}' \
    "$(python3 -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))")")"
check "stays silent for a brand-new session" "$OUT/sweep.log" "AUTH EXPIRES" no
check "and does not nag in notifications"    "$OUT/notifications.txt" "li-assist auth login" no

echo "== session already stale =="
run_sweep '{"logged_in":true,"stale":true,"age_days":14.8,"reauth_days":14}'
check "sweep.log records the skip"            "$OUT/sweep.log" "SKIP stale-auth" yes
check "a DEDICATED auth notification fires"   "$OUT/notifications.txt" "LinkedIn auth" yes

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
