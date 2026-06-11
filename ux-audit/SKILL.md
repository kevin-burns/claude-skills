---
name: ux-audit
description: Heuristic usability and accessibility audit of existing web pages — load a rendered page, evaluate it against Nielsen's 10 usability heuristics + WCAG 2.2 (A/AA) + responsive behavior + the page's own goal, and return prioritized findings with a concrete fix for each. Use whenever the task is to review, audit, critique, or "find usability/UX problems" on one or more web pages, do an accessibility (a11y) check, assess responsiveness, or propose usability fixes — even if the user just says "is this page any good", "what's wrong with this UI", "make this more usable", or hands you a URL/screenshot. This is a review/audit method, not a design-decision debate (that's design-council) and not functional testing (that's webapp-testing). Read by the ux-auditor agent, which renders each page with a browser driver and fans out one auditor per page.
license: MIT
---

# UX Audit

Audit an **existing, rendered** page against a fixed rubric and return findings the caller
can act on. The discipline that makes this useful: **audit what's actually on screen, cite
the heuristic or success criterion, and propose a concrete fix.** A finding with no
location and no fix is noise; a "problem" you assumed without observing the page is worse.

This is distinct from neighbours:
- **design-council** deliberates *one* high-stakes design decision (preserves dissent).
  Use it for "should we restructure this flow?", not "audit these 12 pages."
- **webapp-testing** checks that features *work*. UX audit checks whether they're *usable
  and accessible* even when they work.

## Inputs you need

- The page(s): a URL, a local file, or a running dev server. For a *series* of pages, the
  `ux-auditor` agent fans out — one auditor per page (see that agent).
- The page's **goal** — what is the user there to do? You can't judge usability without it.
  If not given, infer it from the page and state your assumption in the finding set.
- Viewports to check (at least one mobile ~375px and one desktop ~1280px). Responsive
  problems only show up if you actually resize.

## Render the page first — don't audit blind

Audit the rendered DOM and the visual result, not the raw source. Use whatever browser
driver is installed (prefer `agent-browser`, fall back to `playwright-cli`; the CLI binary
is `playwright-cli`, **not** `playwright`):

```bash
# preference order — use whichever exists
if command -v agent-browser >/dev/null 2>&1; then echo agent-browser
elif command -v playwright-cli >/dev/null 2>&1; then echo playwright-cli
else echo NONE; fi
```

For each page capture: a **screenshot** at each viewport, the **rendered HTML/DOM**, and
(where the driver allows) computed styles for contrast and a tab-order walk for keyboard
checks. The screenshot is your evidence; reference it in findings.

**Isolate the session — the #1 cause of bad audits under fan-out.** Both drivers default
to a single shared browser session via a background daemon. When several audits run at once
(the fan-out pattern), they collide on that shared session and you get *cross-contamination*
— evals returning another page's DOM. Always give each audit its **own named session** and
close it when done. This, not the tool, is what broke an early run of this skill.

**Time-box the driver.** If it still doesn't render cleanly within a few tries, switch
drivers or drop to a static audit and *say so* — don't sink 30 calls into fighting it.

### agent-browser recipe (preferred — handles local files and concurrency cleanly)
```bash
S="uxaudit-$$"                                  # unique session per audit (fan-out safe)
agent-browser --session "$S" --allow-file-access open "file:///abs/path/page.html"
agent-browser --session "$S" --allow-file-access open "https://example.com"   # remote too
```
- **Local files load directly** with `--allow-file-access` — no HTTP server needed.
- **`eval` via `--stdin`** avoids all shell-quoting corruption (the trap that wastes calls);
  return a string with `JSON.stringify(...)`:
  ```bash
  agent-browser --session "$S" eval --stdin <<'EOF'
  JSON.stringify((() => {
    const noAlt = Array.from(document.images).filter(i => !i.alt).length;
    const p = document.querySelector("p"); const s = getComputedStyle(p);
    const b = document.querySelector("button"); const r = b.getBoundingClientRect();
    return { noAlt, color: s.color, bg: s.backgroundColor, target: r.width + "x" + r.height };
  })())
  EOF
  ```
- **Evidence & viewports:** `snapshot -i` (a11y refs/roles), `screenshot --annotate`
  (numbered labels — ideal for icon-only buttons), `screenshot --full`. For mobile, set
  viewport via config/flags or audit at the iOS profile (`-p ios`).
- **Always** `agent-browser --session "$S" close` when done.

### playwright-cli recipe (fallback — binary is `playwright-cli`, not `playwright`)
- **Serve local files over HTTP** — `file://` URLs often don't load. Start a throwaway
  server and target `http://localhost`:
  ```bash
  ( cd "$DIR" && python3 -m http.server 8731 & )      # or `uv run python -m http.server`
  playwright-cli open                                  # start the browser
  playwright-cli goto "http://localhost:8731/page.html"  # goto, not open-with-arg
  ```
  `open <url>` may stay on `about:blank`; always `goto` explicitly after `open`.
- **`eval` takes a function and the value prints under `### Result`.** Use `() => ...`
  form; a bare expression containing `=>` is misparsed as a function-to-apply. Return a
  string (`JSON.stringify(...)`) so the result is unambiguous:
  ```bash
  playwright-cli eval "() => { const b=document.querySelector('button'); const r=b.getBoundingClientRect(); return JSON.stringify({w:r.width,h:r.height}); }"
  ```
- **High-yield evals:** images missing `alt`, inputs whose `.labels` is empty, computed
  `color`/`backgroundColor` for contrast, `getBoundingClientRect()` for target size.
- **Viewports & evidence:** `playwright-cli resize 375 812` then `screenshot`, repeat at
  `1280 900`. `playwright-cli snapshot` dumps the accessibility tree (names/roles).
- Always `playwright-cli close` when done.

If no driver is installed (or you abandoned a flaky one), set `"driver": "static-only"`,
audit the static HTML + any screenshot the user provides, and flag in `notes` that
dynamic/contrast/keyboard/viewport checks were not performed. An honest partial audit beats
a guess.

## The rubric

Walk all three lenses. Don't stop at accessibility — usability and responsiveness catch
different failures.

### 1. Nielsen's 10 usability heuristics
1. **Visibility of system status** — does the UI show what's happening (loading, saved,
   selected, where-am-I)?
2. **Match with the real world** — language/concepts the user knows, not system jargon.
3. **User control & freedom** — undo, cancel, back, clear exits from unwanted states.
4. **Consistency & standards** — same thing looks/acts the same; platform conventions.
5. **Error prevention** — constraints, confirmations, sensible defaults that stop mistakes.
6. **Recognition over recall** — options visible; don't make users remember across steps.
7. **Flexibility & efficiency** — accelerators for experts without blocking novices.
8. **Aesthetic & minimalist design** — no competing clutter; signal over noise.
9. **Help users recover from errors** — plain-language errors that say what and how to fix.
10. **Help & documentation** — findable, task-oriented help where needed.

### 2. WCAG 2.2 — target Level A & AA
Check the high-yield criteria first:
- **Text alternatives** — meaningful `alt` on informative images; empty `alt=""` on
  decorative ones.
- **Contrast (1.4.3 / 1.4.11)** — text ≥ 4.5:1 (≥ 3:1 for large text ≥ 18.66px bold /
  24px); UI components & graphics ≥ 3:1. Measure from computed colours, don't eyeball.
- **Keyboard (2.1.1) & focus visible (2.4.7)** — everything operable by keyboard; a
  visible focus indicator; logical tab order; no keyboard traps.
- **Labels & names (1.3.1 / 4.1.2)** — form controls have associated `<label>`s; controls
  expose an accessible name; ARIA used correctly (or not at all).
- **Headings & structure (1.3.1 / 2.4.6)** — one logical heading outline; landmarks
  (`main`, `nav`, `header`); descriptive page `<title>`.
- **Target size (2.5.8, new in 2.2)** — interactive targets ≥ 24×24 CSS px (or spaced).
- **Resize/reflow (1.4.10)** — usable at 320px width / 400% zoom without horizontal scroll.
- **Don't rely on colour alone (1.4.1)** — state shown by more than hue.

### 3. Responsive & device behaviour
- Layout holds at mobile (~375px) and desktop (~1280px); no overflow, overlap, or cut-off
  controls. Tap targets aren't cramped. Content reflows rather than requiring zoom/scroll.

## Severity — so the caller can triage

Match the fleet's review scale (same as `code-reviewer`):
- **blocking** — users can't complete the page's goal, or a WCAG **Level A** failure shuts
  out a group (e.g. unlabeled critical control, keyboard trap, no alt on the only CTA icon).
- **major** — serious friction or a WCAG **AA** failure (contrast below 4.5:1, focus not
  visible, confusing error with no recovery).
- **minor** — polish: inconsistency, clutter, small-but-real friction.

Reserve `blocking` for "this stops someone," and back every finding with what you observed.

## Return format (final message) — JSON only

One object per audited page. (When fanned out, the agent merges these.)

```json
{
  "page": "url-or-path",
  "goal": "what the user is here to do (stated or inferred)",
  "viewports_checked": ["375x812", "1280x900"],
  "driver": "agent-browser | playwright-cli | static-only",
  "summary": { "blocking": 0, "major": 0, "minor": 0 },
  "findings": [
    {
      "severity": "blocking | major | minor",
      "lens": "usability | accessibility | responsive",
      "ref": "Nielsen #5 | WCAG 1.4.3 | responsive@375px",
      "location": "selector or region, e.g. 'form#signup > button.submit'",
      "evidence": "what you observed (+ screenshot ref / measured value)",
      "suggested_fix": "concrete change to make",
      "confidence": "high | medium | low"
    }
  ],
  "notes": "assumptions, what couldn't be checked, empty if none"
}
```

Be precise over exhaustive. Ten located, fixable findings beat forty vague ones. If you
couldn't render the page, say what you could and couldn't assess rather than inventing
problems.

## Privacy

The audited pages and any findings about a specific product are often the client's
property — keep the *page content and results* out of any shared/committed location. This
skill and the `ux-auditor` agent are generic and publishable; the data they process is not.
