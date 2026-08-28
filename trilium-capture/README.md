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

## Setting it up

Nothing to install — the MCP server ships **inside** Trilium. There are three steps and one
trap, and the trap is where the time goes.

**1. Mint an ETAPI token.** In Trilium: **Options → ETAPI → Create new token**. Copy it once;
you cannot read it back. Put it in whatever file holds your other secrets, never in a config
file that gets committed:

```sh
export TRILIUM_ETAPI_KEY='...'      # in ~/.config/dotfiles/env.sh, or your equivalent
```

**2. Point your agent at `/mcp`.** For Claude Code, at **user** scope — project scope would
put your private host in a repo:

```sh
claude mcp add --transport http trilium http://YOUR-HOST:8080/mcp -s user \
  -H 'Authorization: Bearer ${TRILIUM_ETAPI_KEY}'
```

The `${VAR}` is expanded at connect time, so the token stays out of `~/.claude.json`. Plain
`http` to a host on your own network is fine — the client does not require TLS.

**3. Make sure the variable is actually in the agent's environment.** This is the trap.

`${TRILIUM_ETAPI_KEY}` expands from the **process** environment of the agent, fixed when it
launched. A secrets file that nothing sources is invisible to it, and so is one sourced from
`~/.zshrc` — that file is read only by *interactive* shells, which a child process is not. The
symptom is a 401 that looks like a bad token:

```
Failed to connect — Server rejected the configured Authorization header (HTTP 401)
{"error":"MCP requires an ETAPI token. Create one in Options > ETAPI ..."}
```

Restarting the agent does not help, and neither does reconnecting: the config is re-read, the
environment is not. Source the file from **`~/.zshenv`**, which every zsh reads including new
tmux panes, then start the agent fresh:

```sh
# ~/.zshenv
[ -f ~/.config/dotfiles/env.sh ] && source ~/.config/dotfiles/env.sh
```

Anything in `~/.zshenv` must be **silent** — output there breaks `scp` and `rsync`. Check with
`zsh -c 'source ~/.config/dotfiles/env.sh' | wc -c`, which must print `0`.

### Verifying it, without guessing

Prove the endpoint and the token independently of the client:

```sh
curl -s -H "Authorization: Bearer $TRILIUM_ETAPI_KEY" http://YOUR-HOST:8080/etapi/app-info
# -> {"appVersion":"0.105.0", ...}

curl -s -X POST http://YOUR-HOST:8080/mcp \
  -H "Authorization: Bearer $TRILIUM_ETAPI_KEY" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
# -> serverInfo {"name":"trilium-notes","version":"0.105.0"}
```

If those work and the client still 401s, **the problem is the environment, not the token** —
the header is going out with the placeholder as literal text. `evals/smoke_live.py` in this
directory exercises the whole convention set the same way, creating a throwaway subtree and
deleting it.

**Requires Trilium v0.93.0+** for the `Bearer` header form. Verified against **0.105.0**.

## Requirements

A reachable Trilium instance with its **built-in** MCP server — v0.93.0 or later, mounted at
`/mcp`. See [Setting it up](#setting-it-up) above for the token, the client config and the
environment trap that produces a misleading 401.

Nothing to install: the server ships inside Trilium and shares its tool definitions with
Trilium's own LLM chat. **Do not add a third-party Trilium MCP server** — there are more than
twenty on GitHub, and the two with any traction carry no licence at all.

If the MCP tools are not connected, the skill says so and returns the content in the reply
rather than dropping it.

Optional: a short-memory store such as [Ogham](https://github.com/ogham-mcp/ogham-cli) for the
recall half of the split. Without one, everything goes to Trilium and the first step is a no-op.

## Licence

MIT, like the rest of this repo. Trilium itself is AGPL-3.0 and is neither vendored nor
modified here — this skill only calls its published MCP tools.
