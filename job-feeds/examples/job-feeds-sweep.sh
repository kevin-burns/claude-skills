#!/bin/bash
# Daily job sweep — job-feeds, plus LinkedIn via li-assist when it is available.
#
# Designed to be driven by launchd (see job-feeds-sweep.plist beside this file).
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
        #
        # USE li-digest, NOT `li-assist jobs sweep`. This ran for days as a
        # single hand-written `platform engineer OR sre` at li-assist's
        # default --limit 25, and it looked healthy the whole time: "ok"
        # every morning, ~6 new rows. LinkedIn ranks by relevance rather
        # than date, so the same top-25 came back each day and genuinely new
        # postings never cracked it. Measured 2026-08-10: raising that one
        # query to --limit 100 returned 61 new in a single extra call.
        #
        # But depth was only half of it. `li-assist jobs sweep <string>`
        # takes a raw keyword, so any caller has to invent its own queries --
        # and li-assist's SKILL.md already names query/match drift as this
        # project's top risk: a query that fetches roles the archetype regex
        # will not label. Hand-writing four queries here reproduced exactly
        # that, 62 unlabelled rows out of 582, and silently missed the
        # `architect` archetype altogether.
        #
        # li-digest is the tool that already solves this. It sweeps EVERY
        # archetype in ~/.config/li-assist/archetypes.json, each using the
        # `query` that was written alongside its `match`, and honours the
        # file's exclude_title / exclude_company / limit defaults. One call
        # per archetype, paced 3-6s apart by the limiter, against a 100/day
        # cap -- five archetypes is five calls.
        #
        # Exit contract (li_digest.main): 0 clean, 1 at least one archetype
        # failed, 2 config or auth error. It deliberately does NOT advance
        # its last-run marker on a partial failure, so a lane that failed
        # today still reports its postings as new tomorrow.
        #
        # stderr here is the AUDIT TRAIL ("li-digest: sweeping platform…"),
        # not an error, so it goes to a .log and not a .err. Naming it .err
        # once made a perfectly good run look like a failure.
        # `li_hard_failed` is the control flag, NOT the text of li_line. An
        # earlier version tested whether li_line started with the word
        # "failed", which worked only because the partial-failure message
        # happens to start with a digit. That coupled control flow to
        # wording invisibly: rephrasing a message could have silently
        # stopped the report being written.
        li_hard_failed=0

        # `warn` appends rather than assigns. A partial archetype failure
        # and a failed render can both happen in one run, and the earlier
        # version let the second overwrite the first -- so the notification,
        # which is the whole point of the "reported, never silently skipped"
        # rule at the top of this file, dropped the archetype detail.
        warn() { li_warn="${li_warn:+$li_warn; }$1"; }

        if command -v li-digest >/dev/null 2>&1; then
            li-digest --json >"$OUTDIR/.li.json" 2>"$OUTDIR/.li.log"
            rc=$?

            # One parse, and a PARSE_ERROR sentinel rather than a silent 0.
            # `except: print(0)` with stderr discarded made a truncated or
            # half-written .li.json indistinguishable from a genuinely empty
            # result: it rendered "0 fresh / 0 in window" with no warning,
            # which is precisely the reports-success-while-doing-nothing
            # class this file's header calls the worst bug here. Python's
            # stderr goes to .li.log so the decode error is readable.
            counts="$(python3 -c "import json,sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as exc:
    print('li-digest: could not parse .li.json: %s' % exc, file=sys.stderr)
    print('PARSE_ERROR')
else:
    print(len(d), sum(1 for r in d if r.get('bucket') == 'fresh'))
" "$OUTDIR/.li.json" 2>>"$OUTDIR/.li.log")" || counts="PARSE_ERROR"

            if [ "$counts" = "PARSE_ERROR" ] || [ -z "$counts" ]; then
                rows="?"; fresh="?"
                warn "LinkedIn: could not read li-digest output — see $OUTDIR/.li.log"
            else
                rows="${counts%% *}"
                fresh="${counts##* }"
            fi

            case "$rc" in
                0) li_line="$fresh fresh / $rows in window" ;;
                1) li_line="$fresh fresh / $rows in window — ARCHETYPE(S) FAILED"
                   detail="$(sed -n 's/^li-digest: \([0-9]* archetype(s) failed.*\)/\1/p' \
                             "$OUTDIR/.li.log" | tail -1)"
                   warn "LinkedIn: ${detail:-an archetype failed — see $OUTDIR/.li.log}" ;;
                *) li_line="failed (exit $rc)"
                   li_hard_failed=1
                   warn "LinkedIn sweep failed — see $OUTDIR/.li.log" ;;
            esac
        else
            # Fallback only. This path cannot use archetypes, so say so
            # rather than let a keyword search pass for a lane sweep.
            li-assist jobs sweep "${JOB_SWEEP_QUERY:-platform engineer OR sre}" \
                --limit "${JOB_SWEEP_LIMIT:-100}" \
                >/dev/null 2>"$OUTDIR/.li.log"
            rc=$?
            if [ "$rc" -eq 0 ]; then
                li_line="$(sed -n 's/^sweep: //p' "$OUTDIR/.li.log" | tail -1)"
                li_line="${li_line:-ok} (single query — li-digest not installed)"
                warn "li-digest is not on PATH, so only one hand-written query ran and your archetypes were not swept"
            else
                li_line="failed"
                li_hard_failed=1
                warn "LinkedIn sweep failed — see $OUTDIR/.li.log"
            fi
        fi

        if [ "$li_hard_failed" -eq 1 ]; then
            : # the sweep itself failed; do not render on top of it
        else
            # `jobs sweep` only updates the cache. Without this the LinkedIn
            # report never regenerates and silently goes stale while
            # jobs.html refreshes daily beside it -- which is exactly what
            # happened: prospects.html sat a day old next to a fresh
            # jobs.html, and nothing in the log said so.
            if command -v li-report >/dev/null 2>&1; then
                if ! li-report --out "$OUTDIR/prospects.html" \
                     >/dev/null 2>>"$OUTDIR/.li.log"; then
                    li_line="$li_line (report FAILED)"
                    warn "LinkedIn report failed — see $OUTDIR/.li.log"
                fi
            else
                li_line="$li_line (no li-report)"
                warn "li-report is not on PATH — the LinkedIn report is not being written"
            fi
        fi
    fi
fi

printf '%s  jf:%s %s  li:%s\n' "$STAMP" "$jf_status" "${jf_line:-—}" "$li_line" >> "$LOG"

msg="job-feeds: ${jf_line:-$jf_status}"
[ -n "$li_warn" ] && msg="$msg"$'\n'"⚠ $li_warn"
notify "Daily job sweep" "$msg"

[ "$jf_status" = "ok" ] || exit 1
exit 0
