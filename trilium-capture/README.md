# trilium-capture

Write findings, clipped material and long-form documents into a self-hosted
[Trilium Notes](https://github.com/TriliumNext/Trilium) instance — filed per project, labelled
with a controlled vocabulary, and revised in place rather than duplicated.

Part of [claude-skills](../README.md).

## What it does

Trilium ships its own MCP server. This skill does not wrap it, replace it, or add a transport —
it supplies the judgment the tools have no opinion about:

- **Decides whether a thing belongs in Trilium at all.** Trilium holds what a human reads;
  Ogham (or any short-memory store) holds what an agent recalls mid-task. A three-sentence
  gotcha is a memory, not a note.
- **Files it somewhere findable.** `Projects/<project>/` located by a `#project` label rather
  than a path, so reorganising the tree breaks nothing. Anything unfiled goes to `Inbox`.
- **Labels it from a closed vocabulary** — `#capture`, `#project`, `#type`, `#source`,
  `#captured` — so two sessions produce notes that can find each other. Left to themselves,
  two agents invent two disjoint tag schemes; that is measured, not assumed.
- **Searches before writing**, so a repeated session appends to the existing note instead of
  leaving a near-duplicate beside it.
- **Treats documents as living things.** A plan or a draft is located and revised in place, and
  Trilium's built-in revision history does the versioning — which is what replaces keeping
  `.bak-2026-08-28` copies by hand.
- **Picks the right note type.** Markdown prose as `text`, diagrams as `mermaid`, Excalidraw as
  `canvas`, scripts as `code` with a mime. A `text` note will not render a mermaid fence, so a
  document with diagrams becomes a note plus `mermaid` children.

## How to use it well

- **Say where it goes, or let it ask.** "Store that in Trilium" is enough; the skill infers the
  project from the repo or `CLAUDE.md` and files to `Inbox` when it genuinely cannot tell.
- **Keep one project name across systems.** If your memory store tags `project:claude-skills`,
  the Trilium label must be `#project=claude-skills`. Two spellings split a project in half.
- **Let it skip things.** Being told "that is already captured, here is the note" is the skill
  working. A capture store earns its keep by what it declines to add.
- **Revise, don't re-add.** Ask it to update the plan; it will find the note by
  `#type=document` and overwrite, leaving a revision behind.
- **`#capture` is your filter.** `#capture` shows everything written by an agent;
  `#!capture` shows only your own notes.

## What it does NOT do

- **It does not read your notes back to you.** No retrieval, no question-answering, no summaries
  of what is in there. That is a different skill and this one does not pretend to it.
- **It does not maintain the tree.** No cleanup passes, no dedup sweeps, no re-filing, no
  orphan hunting.
- **It never touches a note that is not `#capture`.** Your own notes cannot be edited, moved or
  deleted by it. That boundary is structural, not a promise.
- **It does not delete anything at all**, including its own notes.
- **It does not write to `root`, `Calendar` or the hidden subtree.**
- **It does not capture credentials.** It records the *name* of a secret and where it lives,
  never the value — a skill that writes session content into a store is an exfiltration path
  unless it refuses this explicitly.
- **It does not invent a label.** If something needs a tag outside the vocabulary, it asks.

## Requirements

A reachable Trilium instance with its **built-in** MCP server — v0.93.0 or later, mounted at
`/mcp`, authenticated with an ETAPI token as `Authorization: Bearer <token>`. Nothing to
install: the server ships inside Trilium and shares its tool definitions with Trilium's own LLM
chat. Do not add a third-party Trilium MCP server; there are more than twenty on GitHub and the
two with any traction carry no licence.

If the MCP tools are not connected, the skill says so and returns the content in the reply
rather than dropping it.

Optional: a short-memory store such as [Ogham](https://github.com/ogham-mcp/ogham-cli) for the
recall half of the split. Without one, everything goes to Trilium and the first step is a no-op.

## Licence

MIT, like the rest of this repo. Trilium itself is AGPL-3.0 and is neither vendored nor
modified here — this skill only calls its published MCP tools.
