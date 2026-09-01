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

# --- hold the machine awake for the duration ------------------------------
# Diagnosed 2026-08-27. The 07:30 run fires during a macOS DarkWake -- a brief
# maintenance wake on battery -- and powerd caps that window:
#
#   07:29:34  DarkWake from Deep Idle ... Using BATT
#   07:29:36  Entering Sleep state due to 'Sleep Service Back to Sleep'
#   07:46:25  DarkWake ... SleepService: window begins with cap time=180 secs
#
# THREE MINUTES, then the machine sleeps whether the sweep has finished or not.
# That single fact explains the whole log: evening runs fire at 17:30 exactly and
# never degrade because the machine is awake and in use; morning runs always fire
# LATE (07:30, :35, :37, :39, :43, :46 -- waiting for a DarkWake) and degraded on
# 2 of 6 mornings. On 2026-08-27 job-feeds AND li-digest failed in the SAME run,
# which is the tell: one cause, not two bugs.
#
# `caffeinate -i` holds a PreventUserIdleSystemSleep assertion for as long as the
# wrapped process runs. `-m` keeps the disk awake too. NOT `-s`: its own man page
# says it is valid only on AC power, and this machine is on battery.
#
# VERIFIED 2026-08-29, which is what the elapsed time was added to answer. Two
# battery mornings since this landed, both fine, both far past the 180s cap:
#
#   08-28 07:43  jf:ok 1439 rows  [1639s batt caff:yes]
#   08-29 07:33  jf:ok 1445 rows  [5165s batt caff:yes]
#
# Against the two before it: 08-25 07:35 degraded at 279 rows and 08-27 07:46 at
# 291, roughly a fifth of a full sweep -- the shape of being cut off mid-run.
# So the assertion does override the SleepService cap.
#
# Still true and worth knowing: the same run takes ~143s on AC and took 5165s on
# battery, a ~35x slowdown from DarkWake CPU throttling. It completes; it is not
# fast. If that ever matters, the fix is a machine that is awake, not a flag.
if [ -z "${JOB_SWEEP_CAFFEINATED:-}" ] && command -v caffeinate >/dev/null 2>&1; then
    export JOB_SWEEP_CAFFEINATED=1
    exec caffeinate -i -m "$0" "$@"
fi

JF="$HOME/.claude/skills/job-feeds/scripts/job_feeds.py"
OUTDIR="${JOB_SWEEP_OUTDIR:-$HOME/job-search}"
LOG="$OUTDIR/sweep.log"
STAMP="$(date '+%Y-%m-%d %H:%M')"
START_EPOCH="$(date +%s)"

# Was this run wrapped, and was the machine on battery? Both belong in the log
# line: without them a degraded run is indistinguishable from a slow one.
CAFF="caff:$([ -n "${JOB_SWEEP_CAFFEINATED:-}" ] && echo yes || echo NO)"
# pmset is macOS-only. Without it we do NOT know the power source, and guessing
# "batt" would put a false fact in the log -- which is the one thing this field
# exists to prevent. Report it as unknown and let the reader see the gap.
if command -v pmset >/dev/null 2>&1; then
    PWR="$(pmset -g batt 2>/dev/null | grep -qi "AC Power" && echo ac || echo batt)"
else
    PWR="pwr?"
fi

mkdir -p "$OUTDIR"

# Keep ONE previous copy of each diagnostic. These were overwritten every run, so
# by the time a failure was noticed its evidence was already gone -- which is why
# the 2026-08-27 failure had to be reconstructed from `pmset -g log`.
for f in .li.log .jf.err .li.json; do
    [ -f "$OUTDIR/$f" ] && cp "$OUTDIR/$f" "$OUTDIR/$f.prev" 2>/dev/null
done

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
# Auth problems travel separately from li_warn so they can be notified on
# their own. See the notification block at the foot of this file for why.
auth_warn=""
# How many days before the re-auth policy bites to start warning. The point
# is to warn while the session STILL WORKS -- a warning that arrives with the
# skip is a post-mortem, not an early warning.
AUTH_WARN_LEAD_DAYS="${AUTH_WARN_LEAD_DAYS:-3}"
if command -v li-assist >/dev/null 2>&1; then
    auth="$(li-assist auth status --json 2>/dev/null)"
    stale="$(printf '%s' "$auth" | sed -n 's/.*"stale"[[:space:]]*:[[:space:]]*\([a-z]*\).*/\1/p')"
    logged="$(printf '%s' "$auth" | sed -n 's/.*"logged_in"[[:space:]]*:[[:space:]]*\([a-z]*\).*/\1/p')"
    if [ "$logged" != "true" ]; then
        li_line="SKIP not-logged-in"
        auth_warn="LinkedIn: not logged in — run 'li-assist auth login'"
    elif [ "$stale" = "true" ]; then
        li_line="SKIP stale-auth"
        auth_warn="LinkedIn: session stale — run 'li-assist auth login'"
    else
        # Early warning: the session is still good, but not for long. Compute
        # the remaining days and, inside the lead window, mark BOTH the log
        # line and the notification. Unparseable values yield an empty
        # days_left and simply skip the warning -- a missing warning must
        # never cost you the sweep itself.
        # Derived from captured_at, NOT age_days. li-assist marshals age_days
        # as `float64` with `omitempty` (cmd/li-assist/auth.go), so the field
        # DISAPPEARS from the payload whenever it rounds to 0 -- i.e. on any
        # session under ~1.2h old. Reading it means a fresh session reports
        # nothing rather than "14 days left", and the arithmetic silently
        # yields no warning at all. captured_at is unconditional; age_days
        # survives only as a fallback for a payload that lacks captured_at.
        days_left="$(printf '%s' "$auth" | python3 -c "
import json, sys, datetime
try:
    d = json.load(sys.stdin)
    reauth = float(d['reauth_days'])
    cap = d.get('captured_at')
    if cap:
        t = datetime.datetime.fromisoformat(cap.replace('Z', '+00:00'))
        age = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 86400.0
    else:
        age = float(d['age_days'])
    print('%.1f' % (reauth - age))
except Exception:
    pass
" 2>/dev/null)"
        auth_expiring=""
        if [ -n "$days_left" ] && awk -v d="$days_left" -v lead="$AUTH_WARN_LEAD_DAYS" \
             'BEGIN { exit !(d <= lead) }'; then
            auth_expiring="$days_left"
            auth_warn="LinkedIn: session expires in ${days_left}d — run 'li-assist auth login' now, before it goes stale"
        fi

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
                1) detail="$(sed -n 's/^li-digest: \([0-9]* archetype(s) failed.*\)/\1/p' \
                             "$OUTDIR/.li.log" | tail -1)"
                   # NAME the lanes in the log, not just the fact. On 2026-09-01 the
                   # failing archetype was `em` -- engineering management, the primary
                   # target lane -- and sweep.log said only "ARCHETYPE(S) FAILED", so
                   # nothing distinguished losing the most valuable lane from losing
                   # the least. The names are already in .li.log; carry them across.
                   names="$(printf '%s' "$detail" | sed -n 's/.*failed: *//p')"
                   li_line="$fresh fresh / $rows in window — ARCHETYPE(S) FAILED${names:+: $names}"
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

        # Appended last so it survives whatever li_line ended up as above.
        # Upper-case on purpose: this is the one line in the log that means
        # "act now" rather than "here is what happened".
        [ -n "$auth_expiring" ] && li_line="$li_line — AUTH EXPIRES IN ${auth_expiring}d"
    fi
fi

# Elapsed, power source and caffeinate state are on every line now. A run that
# degrades at ~180s on battery is the DarkWake cap; one that degrades at 20s is a
# different bug, and the old log line could not tell them apart.
ELAPSED="$(( $(date +%s) - START_EPOCH ))"
printf '%s  jf:%s %s  li:%s  [%ss %s %s]\n' \
    "$STAMP" "$jf_status" "${jf_line:-—}" "$li_line" "$ELAPSED" "$PWR" "$CAFF" >> "$LOG"

# Auth trouble still appears in the combined message and the log, so nothing
# that read li_warn before loses information.
[ -n "$auth_warn" ] && li_warn="${li_warn:+$li_warn; }$auth_warn"

msg="job-feeds: ${jf_line:-$jf_status}"
[ -n "$li_warn" ] && msg="$msg"$'\n'"⚠ $li_warn"
notify "Daily job sweep" "$msg"

# ...and then AGAIN, on its own. On 2026-08-19 the stale-session warning was
# already in the combined message above and was still missed: under a routine
# "Daily job sweep" title it reads as part of the normal daily noise, and the
# sweep went two runs without covering LinkedIn. Auth is the only failure here
# that needs a human action rather than a glance, so it gets its own title.
[ -n "$auth_warn" ] && notify "⚠ LinkedIn auth" "$auth_warn"

[ "$jf_status" = "ok" ] || exit 1
exit 0
