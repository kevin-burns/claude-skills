---
name: trilium-capture
description: Write findings, clipped material and long-form documents into a self-hosted Trilium Notes instance over its native MCP — filed under a project, labelled with a controlled vocabulary, and revised in place rather than duplicated. Use when the user says to store, capture, save or file something in Trilium; when a research finding or an article should outlive the session; or when a document produced with the user (a plan, a draft, a report) should live in their notes instead of on one machine. Do NOT use for short recallable facts an agent needs mid-task — those belong in Ogham shared memory.
---

# Trilium capture

Trilium holds what a **human reads**. Ogham holds what an **agent recalls**. Every capture
starts by deciding which, and most sessions produce some of each.

This skill is conventions only. It calls the tools Trilium's own MCP server already exposes —
`search_notes`, `create_note`, `set_attribute`, `append_to_note`, `edit_note_content` — and adds
the judgment those tools have no opinion about: where a note goes, what it is called, how it is
labelled, and when not to write one at all.

## Requirements

The Trilium MCP server must be connected. It is **built into Trilium** (v0.93.0+, mounted at
`/mcp`) — do not install or build a third-party one. If the tools are unavailable, say so and
put the content in the reply. **A capture skill that silently drops what it was given is worse
than no capture skill.**

## Step 1 — Trilium or Ogham?

| | goes to Ogham | goes to Trilium |
|---|---|---|
| shape | a few sentences | a page or more |
| consumer | an agent, mid-task | the user, reading |
| example | "CAS has been the default git path since 1.1.0" | the full release write-up |
| retrieval | `hybrid_search` | browse the tree, or `search_notes` |

**When a finding is too long to be an Ogham memory, it is a Trilium note** — and Ogham gets a
short memory naming the note. Set `#ogham=yes` on the note so the pairing is visible from both
ends. That is the only case where the same material lands in both.

A three-sentence gotcha is an Ogham memory even when the user is talking about Trilium.
Say so rather than filing it here — **once**.

**If the user asks again, or says to file it anyway, file it.** They asked for Trilium; the
routing rule is advice about shape, not a veto over an explicit instruction. Raise it in a
sentence, then do what was asked. An agent that keeps re-arguing a decision the user has
already made is worse than a slightly misfiled note.

## Step 2 — Never write without searching first

```
search_notes('#capture #project = "<name>" <distinctive keywords>', ancestorNoteId=<project note>)
```

**ALWAYS QUOTE THE LABEL VALUE.** Measured against a live instance 2026-08-28:

| query | matches |
|---|---|
| `#project = "travel-florence-2026"` | **1** |
| `#project='travel-florence-2026'` | **1** |
| `#project=travel-florence-2026` | **0** |
| `#project = travel-florence-2026` | **0** |

An unquoted value containing a hyphen matches **nothing, with no error** — the hyphen is lexed
as an operator. Project names are exactly the hyphenated kind: `claude-skills`,
`travel-florence-2026`. Unquoted, every one of them returns zero results, the next step reads
that as "does not exist", and a duplicate is created **every session**. Quoting is not style.

| result | do |
|---|---|
| same thing, same depth | **skip** — say it is already captured, and where |
| same thing, more detail | `append_to_note` or `edit_note_content` on the note that exists |
| a document being revised | `set_note_content` on that note — see Documents below |
| nothing | create it |

**Skipping this step is the single most common failure.** Two runs of the same session then
leave two near-identical notes and neither is authoritative.

## Step 3 — Locate or create the project note

```
search_notes('#project = "<name>"')     ← quoted, always
  0 hits → create under Projects, set #project=<name>
  1 hit  → use it
  2+     → STOP and report
```

Two notes carrying the same `#project` value is a split project. Report it; do not pick one.

```
Projects/                        #projectRoot
  claude-skills                  #project=claude-skills
    Terragrunt v1.1.4 findings   #capture #type=research
  travel-florence-2026           #project=travel-florence-2026
    Florence + Bologna plan      #capture #type=document
Inbox/                           #captureInbox
  A clipped article              #capture #type=clip
```

`Projects` and `Inbox` are created once if absent, marked `#projectRoot` and `#captureInbox`.

**`#captureInbox`, not `#inbox`.** `inbox` is one of Trilium's ~58 predefined system labels —
it designates the note that new notes are filed into, so setting it would silently change the
behaviour of the user's own quick-capture. If they *want* that, it is theirs to add; a skill
does not repurpose a system attribute on their behalf. The same caution applies before adding
any label: check it against Trilium's predefined list first.

**Never write to `root`, `Calendar` or `_hidden`.** Something with no project goes to `Inbox`
— an unfiled capture beats a wrongly filed one, and the label locator means nothing breaks
when the user moves it later.

## Step 4 — The label vocabulary is closed

Do not invent labels. These are all of them:

| label | value | notes |
|---|---|---|
| `#capture` | — | **on every note this skill writes.** How the user tells your notes from theirs |
| `#captureInbox` | — | on the `Inbox` root only. **Not** `#inbox`, which is a Trilium system label |
| `#project` | the project name | **the same string Ogham uses for `project:<name>`** |
| `#type` | `research` `reference` `clip` `draft` `document` `diagram` `log` | mirrors Ogham's `type:` scheme |
| `#source` | a URL, or `session` | where it came from, always set |
| `#captured` | `YYYY-MM-DD` | so `orderBy #captured desc` works |
| `#ogham` | `yes` | only when a paired Ogham memory points here |

A topic word belongs in the **title and the content**, where full-text search already finds it.
It does not belong in a new label. `#golang`, `#bug`, `#http`, `#trip`, `#status`,
`#travelDate` are all invented — every one of them came from an agent that had no vocabulary to
follow, and no two agents invent the same one.

If a project genuinely needs a label outside this list, ask the user before adding it.

## Step 5 — Pick the note type

| content | `type` | |
|---|---|---|
| prose, findings, an article, a plan | `text` | Markdown in and out |
| a diagram | `mermaid` | source only, no fences |
| an Excalidraw drawing | `canvas` | JSON — the `excalidraw-diagram` skill emits it |
| a config, script or log kept verbatim | `code` | set `mime`, e.g. `text/x-python` |
| a query worth keeping | `search` | content is the query |

**A `text` note does not render a mermaid fence.** A document containing diagrams becomes a
`text` note plus one `mermaid` child per diagram, with the fenced block replaced by a pointer to
the child. This is the one place where a Trilium note is not simply the Markdown file.

`create_note` returns the stored content. **That is your read-back — do not call
`get_note_content` afterwards to verify.**

**Markdown is normalised, not stored verbatim.** A `text` note is HTML underneath
(`mime: text/html`); Markdown is converted on the way in and regenerated on the way out.
Measured on a live 0.105.0 instance:

| sent | stored |
|---|---|
| `- item` | `*   item` |
| `# Heading` (≠ the note title) | `## Heading` |
| `# Heading` **matching the note title** | **removed entirely** |

The content survives; the exact bytes do not. **Do not repeat the title as an H1 in the body** —
Trilium strips it, because the title already is the H1. Set the title, start the body under it.

Two consequences. **Do not diff what comes back against your source file and conclude the write
failed.** And `edit_note_content` matches exact text, so an edit targeting `- item` will not
find it — read the note first and match what is actually stored, or use `set_note_content`.

## Documents are revised, not re-created

A capture is written once. A document — a plan, a draft, a report — is the same living thing
across sessions, and Trilium keeps its history automatically, which replaces keeping `.bak`
copies by hand.

**You cannot read that history over MCP.** There is no revisions tool: `get_note_revisions`
does not exist and returns `MCP error -32602: Tool not found`, and `get_note` carries no
revision count. Verified against a live 0.105.0 instance 2026-08-28. Revisions are real and
they are for the **user**, viewed in Trilium's own UI. Never offer to show or diff them, and
never call a tool to check one landed.

**Revisions are what makes this better than a file, and two system labels can switch them off.**
`#disableVersioning` stops revisions being created for a note; `#versioningLimit` caps how many
are kept. Neither should be set on a document. If a document's history looks shorter than
expected, check for an inherited one of these before assuming Trilium lost it.

**A document is ONE note, however long.** Do not split a plan or a report into a note per
section. The revision history is per note, so splitting a 450-line document into six gives you
six unrelated histories and no record of the document changing as a whole — which is the entire
reason it is here rather than in a file. The only thing that ever leaves the note is a diagram,
because a `text` note cannot render one (see Step 5).

The trap is that **a later session does not remember the noteId.** Intending to update in place
is not enough; without a way to find the note again, the next session creates a second one. So a
document is always found the same way it was filed:

```
search_notes('#capture #type = "document" #project = "<name>"')
```

Set `#type=document` at creation precisely so this query works later.

## Never capture a credential

This skill writes session content into a store, which makes it an exfiltration path by
construction. Capture the **name** of a secret and where it lives; never its value.

```
✅  "the key is OPENROUTER_API_KEY, set in ~/.config/dotfiles/env.sh"
❌  "OPENROUTER_API_KEY=sk-or-v1-..."
```

The same goes for connection strings, tokens, and anything pasted from an env file or a
credentials file. If a value has already reached the draft, remove it before writing the note.

## What this skill does NOT do

- **It does not retrieve or answer questions** from the notes. It writes.
- **It does not maintain the tree** — no cleanup, no dedup sweeps, no re-filing.
- **It never touches a note without `#capture`.** The user's own notes are out of reach:
  no edit, no move, no delete.
- **It does not delete anything**, including its own notes. Ask the user.
- **It does not write to `Calendar` or `_hidden`**, and never to `root`.
- **It does not decide what a project is called.** Take the name from the repo, from
  `CLAUDE.md`, or from Ogham's existing `project:` tag — matching Ogham matters more than
  being tidy.

## Common mistakes

| mistake | what happens |
|---|---|
| Creating without searching | two near-identical notes, neither authoritative |
| Inventing a container at `root` | every session adds a synonym: `Findings`, `Notes`, `Research` |
| Inventing labels | two agents produce two disjoint vocabularies and neither queries the other's |
| Omitting `#capture` | the user cannot separate their notes from ours |
| Filing a 3-sentence gotcha here | it should have been an Ogham memory; Trilium fills with things nothing reads |
| Re-creating a document | the revision history that made Trilium worth using is lost |
| Putting a mermaid fence in a `text` note | it renders as a code block, not a diagram |
| Trusting the noteId across sessions | next session cannot find it and writes a duplicate |
| Leaving a label value unquoted | a hyphenated project matches nothing, silently, and duplicates every session |
| Calling a revisions tool | there is none on the MCP; the history is the user's, in the UI |
| Diffing the returned Markdown against the source | it is normalised, not verbatim — the write did not fail |
| Repeating the note title as an H1 in the body | Trilium silently removes that line |

## Provenance

[Trilium Notes](https://github.com/TriliumNext/Trilium) (AGPL-3.0) and its built-in MCP server,
which exposes the same tool definitions Trilium's own LLM chat uses. This skill wraps nothing
and reimplements nothing — it supplies conventions for tools Trilium already ships.
