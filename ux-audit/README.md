# ux-audit

Audit a **rendered** web page against a fixed rubric — Nielsen's heuristics, WCAG 2.2 A/AA,
responsive behaviour, and the page's own goal — and return prioritised findings, each with
a location and a concrete fix.

Part of [claude-skills](../README.md).

## What it does

Loads the page in a real browser, captures screenshots and the rendered DOM at mobile and
desktop viewports, measures what can be measured (computed contrast, target sizes, tab
order), and returns JSON: one object per page, findings graded **blocking / major / minor**.

The discipline that makes it useful: **audit what is actually on screen, cite the heuristic
or success criterion, and propose a fix.** A finding with no location and no fix is noise;
a "problem" assumed without observing the page is worse than noise.

Three lenses, all walked — stopping at accessibility misses a different class of failure
than stopping at usability:

| Lens | Covers |
|---|---|
| Nielsen's 10 heuristics | System status, real-world match, control and freedom, consistency, error prevention, recognition over recall, efficiency, minimalism, error recovery, help |
| WCAG 2.2 (A/AA) | Text alternatives, contrast ≥ 4.5:1, keyboard operability and visible focus, labels and accessible names, heading structure and landmarks, target size ≥ 24×24, reflow at 320px, not relying on colour alone |
| Responsive | Layout holds at ~375px and ~1280px; no overflow, overlap or cut-off controls |

Severity has a specific meaning: **blocking** is "this stops someone" — a Level A failure
that shuts out a group, or the page's goal becoming unreachable. Reserve it for that.

## What it does NOT do

- **It is not functional testing.** It checks whether things are *usable and accessible*,
  including when they work correctly. Use webapp-testing for whether they work at all.
- **It is not a design debate.** For "should we restructure this flow?", a deliberation
  method that preserves dissent is the right tool. This skill audits many pages against a
  fixed rubric; it does not weigh one high-stakes decision.
- **It does not edit the audited site.** Read-only and advisory, always.
- **It cannot replace a human accessibility review.** Automation catches contrast ratios,
  missing labels and structural problems. It cannot tell you whether alt text is
  *meaningful*, whether an error message actually helps, or how a screen-reader user
  experiences the flow.
- **It does not guess when it cannot render.** With no driver available it sets
  `"driver": "static-only"`, audits the static HTML, and says in `notes` what was not
  checked. An honest partial audit beats an invented one.

## Requirements

A browser driver: `agent-browser` preferred, `playwright-cli` as fallback. Note the binary
is `playwright-cli`, **not** `playwright`. With neither installed you get the static-only
path described above.

## Two traps worth knowing before you run it

**Isolate the session.** This is the number one cause of bad audits under fan-out. Both
drivers default to a single shared browser session via a background daemon, so concurrent
audits collide and you get *cross-contamination* — an audit returning another page's DOM.
Give every audit its own named session and close it when done. This, not the tool, broke
an early run of this skill.

**Time-box the driver.** If a page will not render cleanly in a few tries, switch drivers
or drop to a static audit and say so. Do not sink thirty calls into fighting it.

[`SKILL.md`](./SKILL.md) has the working recipes for both drivers, including the
shell-quoting trap (`eval --stdin`) that otherwise wastes calls.

## Privacy

Audited pages and findings about a specific product are usually someone else's property.
Keep page content and results out of any shared or committed location. The skill and its
method are generic and publishable; the data they process is not.

## Output

JSON only, one object per page, carrying the goal (stated or inferred), the viewports
checked, which driver ran, a severity summary, and the findings. Be precise over
exhaustive — ten located, fixable findings beat forty vague ones.
