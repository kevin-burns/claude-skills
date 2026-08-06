#!/bin/bash
# Daily job sweep — job-feeds, plus LinkedIn via li-assist when it is available.
#
# Designed to be driven by launchd (see daily-sweep.plist beside this file).
# On macOS use launchd, not cron: `man launchd.plist` states that "unlike cron
# which skips job invocations when the computer is asleep, launchd will start
# the job the next time the computer wakes up". On a laptop that is the whole
# difference between a daily report and a report on the days you happened to
# be awake at 07:30.
#
# Design rules, each one earned:
#   - job-feeds NEVER depends on li-assist. LinkedIn needs an authenticated
#     session that expires; the public feeds need nothing. Coupling them would
#     mean a stale cookie silently costs you the eight boards too.
#   - A stale LinkedIn session is REPORTED, never silently skipped. A sweep
#     that quietly stops covering LinkedIn looks exactly like a quiet week,
#     and that confusion is the single most expensive failure this tool has.
#   - Exit non-zero only if job-feeds itself failed. LinkedIn being unavailable
#     is a normal, expected state, not an error.

set -uo pipefail

JF="$HOME/.claude/skills/job-feeds/scripts/job_feeds.py"
OUTDIR="${JOB_SWEEP_OUTDIR:-$HOME/job-search}"
LOG="$OUTDIR/sweep.log"
STAMP="$(date '+%Y-%m-%d %H:%M')"

mkdir -p "$OUTDIR"

notify() {  # notify <title> <message>
    # osascript is present on every Mac; no dependency to install. Failure to
    # notify must never fail the sweep, hence the guard.
    command -v osascript >/dev/null 2>&1 || return 0
    osascript -e "display notification \"${2//\"/}\" with title \"${1//\"/}\"" \
        >/dev/null 2>&1 || true
}

# --- job-feeds: always runs, needs no credentials -------------------------
jf_line=""
jf_status="ok"
if [ -f "$JF" ]; then
    # Capture first, THEN test the exit code. `x=$(cmd | grep)` sets $? from
    # the pipeline, not from cmd, so testing $? after the assignment reports
    # whether grep matched -- not whether the fetch worked.
    jf_out="$(python3 "$JF" fetch 2>&1)"
    jf_rc=$?
    # exit 1 means "a source failed, the rest still ran" -- degraded, not
    # broken, and still worth a report. Only 2 (config/usage) is fatal.
    if [ "$jf_rc" -ge 2 ]; then
        jf_status="failed"
    else
        [ "$jf_rc" -eq 1 ] && jf_status="degraded"
        printf '%s\n' "$jf_out" > "$OUTDIR/.jf.err"
        jf_line="$(printf '%s\n' "$jf_out" | grep -oE '[0-9]+ row\(s\).*' | tail -1)"
        # ABSOLUTE on purpose. A relative name resolves against the config's
        # report_dir, so this script's OUTDIR would silently control the log
        # while the report went somewhere else entirely -- which is exactly
        # what happened the first time this was run.
        python3 "$JF" report --out "$OUTDIR/jobs.html" >/dev/null 2>&1 \
            || jf_status="failed"
    fi
else
    jf_status="not-installed"
fi

# --- li-assist: only if installed AND the session is fresh ----------------
li_line="not-installed"
li_warn=""
if command -v li-assist >/dev/null 2>&1; then
    auth="$(li-assist auth status --json 2>/dev/null)"
    stale="$(printf '%s' "$auth" | sed -n 's/.*"stale"[[:space:]]*:[[:space:]]*\([a-z]*\).*/\1/p')"
    logged="$(printf '%s' "$auth" | sed -n 's/.*"logged_in"[[:space:]]*:[[:space:]]*\([a-z]*\).*/\1/p')"
    if [ "$logged" != "true" ]; then
        li_line="SKIP not-logged-in"
        li_warn="LinkedIn: not logged in — run 'li-assist auth login'"
    elif [ "$stale" = "true" ]; then
        li_line="SKIP stale-auth"
        li_warn="LinkedIn: session stale — run 'li-assist auth login'"
    else
        # Deliberately NOT --enrich: enrichment is the expensive half (a
        # detail fetch plus a model call per job) and belongs in an
        # interactive session where you can see what it costs.
        if li-assist jobs sweep "${JOB_SWEEP_QUERY:-platform engineer OR sre}" \
             >/dev/null 2>"$OUTDIR/.li.err"; then
            li_line="ok"
        else
            li_line="failed"
            li_warn="LinkedIn sweep failed — see $OUTDIR/.li.err"
        fi
    fi
fi

printf '%s  jf:%s %s  li:%s\n' "$STAMP" "$jf_status" "${jf_line:-—}" "$li_line" >> "$LOG"

msg="job-feeds: ${jf_line:-$jf_status}"
[ -n "$li_warn" ] && msg="$msg"$'\n'"⚠ $li_warn"
notify "Daily job sweep" "$msg"

[ "$jf_status" = "ok" ] || exit 1
exit 0
