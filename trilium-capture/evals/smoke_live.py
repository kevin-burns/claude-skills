#!/usr/bin/env python3
"""LIVE smoke test — needs a reachable Trilium and TRILLIUM_ETAPI_KEY. NOT run by CI.

`grade.py` beside this file is the offline eval CI runs. This one talks to a real instance,
because four of the claims in SKILL.md cannot be checked any other way, and three of them were
WRONG until this script was run:

  - `#project=some-hyphenated-name` matched nothing, silently. Values must be quoted.
  - `get_note_revisions` does not exist on the MCP at all.
  - a leading `# H1` matching the note title is stripped from the content.

Everything is created under ONE throwaway parent at root and deleted at the end, so the
instance is left as found. Creating at root breaks the skill's own rule; it is done here
deliberately so cleanup is a single delete with nothing orphaned.

    source ~/.config/dotfiles/env.sh && python3 evals/smoke_live.py

Never prints the key.
"""

import itertools
import json
import os
import sys
import urllib.request
from datetime import date

URL = os.environ.get("TRILIUM_MCP_URL", "http://10.10.14.232:8080/mcp")
KEY = os.environ.get("TRILLIUM_ETAPI_KEY")
if not KEY:
    sys.exit("TRILLIUM_ETAPI_KEY is not set; source ~/.config/dotfiles/env.sh first")

_ids = itertools.count(1)
results: list[tuple[str, bool, str]] = []


def call(tool: str, **args):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": next(_ids), "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }).encode()
    req = urllib.request.Request(URL, data=payload, method="POST", headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode()
    line = next(x for x in body.splitlines() if x.startswith("data: "))
    d = json.loads(line[6:])
    if "error" in d:
        raise RuntimeError(f"{tool}: {d['error']}")
    text = d["result"]["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


MARKDOWN = """# Smoke document

A paragraph with **bold**, *italic* and `inline code`.

## A table

| leg | time |
|---|---|
| SMN → Bologna | 14:30 |

- a list item
- another

```python
print("fenced code")
```
"""

REVISED = MARKDOWN.replace("14:30", "15:30")

smoke_id = None
try:
    print("Creating throwaway subtree...")
    smoke = call("create_note", parentNoteId="root",
                 title="ZZ SMOKE TEST (delete me)", content="", type="text")
    smoke_id = smoke["noteId"]
    print(f"  parent noteId {smoke_id}")

    proj = call("create_note", parentNoteId=smoke_id,
                title="skill-smoke-test", content="", type="text")
    call("set_attribute", noteId=proj["noteId"], type="label",
         name="project", value="skill-smoke-test")

    # A. the label locator
    hits = call("search_notes", query='#project = "skill-smoke-test"')
    found = json.dumps(hits)
    record("A. search_notes finds a note by #project label",
           proj["noteId"] in found, f"{found[:60]}...")

    # create the document and label it from the closed vocabulary
    doc = call("create_note", parentNoteId=proj["noteId"], title="Smoke document",
               content=MARKDOWN, type="text")
    doc_id = doc["noteId"]
    for name, value in (("capture", None), ("project", "skill-smoke-test"),
                        ("type", "document"), ("source", "session"),
                        ("captured", date.today().isoformat())):
        kw = {"noteId": doc_id, "type": "label", "name": name}
        if value is not None:
            kw["value"] = value
        call("set_attribute", **kw)

    # create_note's return is meant to BE the read-back
    record("create_note returns the stored content",
           "Smoke document" in json.dumps(doc), "")

    # B. markdown round-trip
    back = call("get_note_content", noteId=doc_id)
    back_s = back if isinstance(back, str) else json.dumps(back)
    checks = {
        # A leading H1 matching the note title is REMOVED by Trilium -- documented in
        # SKILL.md. Assert the documented behaviour rather than the naive expectation.
        "title H1 stripped": "# Smoke document" not in back_s,
        "second heading kept": "A table" in back_s,
        "bold": "**bold**" in back_s,
        "table row": "SMN" in back_s and "14:30" in back_s,
        "list": "a list item" in back_s,
        "fenced code": "print(" in back_s,
    }
    record("B. Markdown content survives (normalised, not verbatim)",
           all(checks.values()), ", ".join(f"{k}={'ok' if v else 'LOST'}"
                                           for k, v in checks.items()))

    # the document locator, the query a future session uses
    hits = call("search_notes", query='#capture #type = "document" #project = "skill-smoke-test"')
    record("A2. document locator query finds exactly it",
           doc_id in json.dumps(hits), "")

    # C. revisions are NOT readable over MCP -- assert the tool is genuinely absent, so this
    # stays true if a future Trilium adds one.
    probe = call("get_note_revisions", noteId=doc_id)
    record("C. no revisions tool on the MCP (documented as such)",
           isinstance(probe, str) and "not found" in probe, str(probe)[:50])
    call("set_note_content", noteId=doc_id, content=REVISED)

    now = call("get_note_content", noteId=doc_id)
    now_s = now if isinstance(now, str) else json.dumps(now)
    record("C2. the revision kept the OLD text and the note has the NEW",
           "15:30" in now_s and "14:30" not in now_s, "")

    # D. the user's own filter
    mine = call("search_notes", query="#!capture", ancestorNoteId=smoke_id)
    record("D. #!capture excludes our notes", doc_id not in json.dumps(mine), "")

    # mermaid as a first-class type
    merm = call("create_note", parentNoteId=proj["noteId"], title="Smoke diagram",
                content="graph TD;\n  A[Send] --> B[Read body];", type="mermaid")
    record("create_note accepts type=mermaid",
           merm.get("noteId") is not None, "")

except Exception as exc:  # noqa: BLE001 - a smoke test reports, it does not raise
    record("EXCEPTION", False, f"{type(exc).__name__}: {exc}")
finally:
    if smoke_id:
        try:
            call("delete_note", noteId=smoke_id)
            gone = call("search_notes", query='#project = "skill-smoke-test"')
            record("cleanup: subtree deleted", "skill-smoke-test" not in json.dumps(gone), "")
        except Exception as exc:  # noqa: BLE001
            record("cleanup FAILED", False, f"{exc} -- delete {smoke_id} by hand")

failed = [r for r in results if not r[1]]
print()
print(f"{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
