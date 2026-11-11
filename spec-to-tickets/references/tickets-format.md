# tickets.md

One file beside the spec. Front matter, then increments, then slices. The person may edit it by
hand; `check_tickets.py` reports anything it cannot read, with the line number.

## Front matter

| key | meaning |
|---|---|
| `source` | where the breakdown came from (a path, an issue list, or `built here`) |
| `prd`, `spec` | paths relative to this file |
| `timebox` | the length of one increment; `1 week` unless the person says otherwise |
| `layers` | the layers the spec's implementation decisions name, e.g. `[storage, core, api, ui]` |
| `accepted` | overrides the person gave, one JSON object per line, written by `check_tickets.py accept` |

## Increments and slices

`## Increment N — <title>` groups the slices that fit one timebox. Increment 1 is the walking
skeleton. Each slice is a `### <ID> — <title>` heading followed by:

| field | values |
|---|---|
| `moscow` | `Must`, `Should`, `Could`, `Won't` (Won't Have this time) |
| `size` | `S` (1), `M` (2), `L` (4) |
| `layers` | the layers it touches, `[a, b]` |
| `kind` | `slice`, or `prefactor`, `expand`, `migrate`, `contract` for horizontal work that is meant to be horizontal |
| `traces` | `[turn:<id>]` (a settled turn in spec-ready's readiness.json), a quoted PRD sentence, or `Proposed: <why>` |
| `blocked by` | slice ids, `[T1, T2]` |
| `parallel` | `yes` or `no`: advice only, `yes` when it touches no files another open slice touches |
| `note` | required for `L`: why it is still one context window and one pull request |
| `acceptance` | a list; each item ends `(proves: <user story, success check or goal>)`; an item that adds a figure or name the PRD and spec do not give starts `Proposed:` |
