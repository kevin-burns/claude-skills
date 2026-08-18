# wayfinder on beads — adapter notes

Local notes, deliberately **not** a skill and **not** published. Wayfinder is Matt Pocock's
design (github.com/mattpocock/skills, MIT, commit `9c9f36c`); this is only the mapping onto
the tracker we already run. MIT would permit publishing a port — we don't, because it is his
structure and a beads-specific port helps nobody but us. If it ever ships, it ships as
"adapter for Matt Pocock's wayfinder", never as ours.

## What wayfinder is, and the one distinction that carries it

A **map** is a single tracker issue whose children are **decision tickets** — *"questions whose
resolution is a decision, not slices of a build to execute"*. The map completes when nothing is
left to **decide**, and then hands off to planning.

**This is not work breakdown.** A normal epic decomposes into slices of the build. Break a map
into implementation tasks and you have built an ordinary epic and discarded everything wayfinder
adds. One designed exception — the `task` ticket type — is manual work that *unblocks a
decision* (provisioning access so an API can be judged). It earns its slot by unblocking a
decision, never by delivering the destination.

The map sits **at** epic level, not above it. One map = one destination = one effort.

## The mapping, verified 2026-08-18 rather than assumed

| wayfinder | beads | status |
|---|---|---|
| map issue, labelled `wayfinder:map` | `bd create -t epic` | in use (`claude-skills-6nk`) |
| decision ticket | `bd create -t decision` | **first-class type**, aliases `dec` / `adr` |
| child issue of the map | `--parent <epic-id>` | in use |
| native blocking relationship | `bd dep <blocker> --blocks <blocked>` | in use |
| **frontier** — open, unblocked, unclaimed | **`bd ready --parent <map-id>`** | exact: `bd ready` is documented as "open issues with no active blockers… excludes in_progress, blocked, deferred, and hooked" |
| claim before any work | `bd ready --claim` | **atomic** |
| fog / "not yet specified" | a section in the map's body | no primitive; prose |
| out of scope | close the ticket + one line on the map | closed is unambiguously off the frontier |

## Three places beads is better than the spec, and one where it is worse

**Atomic claim.** Wayfinder claims by assigning the ticket to yourself "first, before any work,
so concurrent sessions skip it" — a convention with a race in it. `bd ready --claim` claims
atomically. Take it; do not reimplement the assignee convention.

**`decision` is a real type.** Wayfinder expresses ticket types as `wayfinder:<type>` labels
because most trackers have nothing better. beads ships `decision` (with `adr` as an alias) as a
first-class issue type, which makes "show me only the decisions" a type filter rather than a
label convention. Use the type; keep labels for the wayfinder-specific ones (`research`,
`prototype`, `grilling`, `task`).

**`--defer` has no wayfinder equivalent.** `--defer <date>` hides an issue from `bd ready` until
then, and `bd ready` excludes deferred by default. That models *blocked on a clock* — waiting
for a cron, a session expiry, a third-party window — which wayfinder can only express as an open
ticket nobody can take. Use it, and the frontier stops lying about what is actionable.

**Worse: `bd ready --explain` silently ignores `--parent`.** Measured 2026-08-18:

```
bd ready --parent claude-skills-nnh              -> 13 issues
bd ready --parent claude-skills-nnh --explain    -> 93 issues   (repo-wide)
bd ready --explain                               -> 93 issues
```

No error, just a wrong-scope answer, and `--explain` is exactly what you reach for when asking
"why is nothing on my map ready?". **Use `bd ready --parent <map>` for the frontier and do not
add `--explain` expecting it to stay scoped.** Tracked as `claude-skills-b29`.

## Two things to cut from the spec, not port

**The local-markdown fallback.** Wayfinder defaults to a markdown tracker when none is provided.
Forbidden here: CLAUDE.md says use `bd` for ALL task tracking and specifically not markdown TODO
lists. Delete the branch.

**Splitting a map across trackers.** The frontier is one query; it has to run in one place. beads
for work in this repo, Linear for Ogham, and never one map spanning both.

## Ticket types, mapped to what we actually have

| type | mode | resolves via |
|---|---|---|
| `research` | AFK | a sub-agent lookup; the only type wayfinder allows more than one of per session |
| `prototype` | HITL | a cheap concrete artifact to react to |
| `grilling` | HITL | **our `frontier-rounds` skill**, not Matt's `grilling` — same algorithm, sub-agent dispatch scoped to read-only environment facts |
| `task` | either | manual work that unblocks a decision. Never delivers the destination |

## The rule worth adopting on day one

**Never resolve more than one ticket per session, research excepted.** This is a
compaction-survival rule, and it is the reason to bother with any of this: the map holds the
state the context window cannot.

Concretely, the session on 2026-08-17 ended on "every P1 is blocked on a person or a clock". In
wayfinder's terms that is a frontier consisting entirely of HITL decision tickets with no AFK
work on it — a fact a map surfaces at session **start**, not as an end-of-session discovery.
