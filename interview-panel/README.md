# interview-panel

Rehearse a panel interview by roleplay. Two to four interviewers ask one question at a time,
follow up on what you actually said and give no coaching until the end. Then a reviewer who did
not play the panel debriefs the transcript against your own evidence base. The debrief explains
what each interviewer was listening for; it does not mark answers wrong.

Part of [claude-skills](../README.md).

## The seats

Pick two to four for a run. Each has its own persona and its own question bank.

| Seat | What they probe | Mostly |
|---|---|---|
| `head-of-cloud` | cloud strategy, hybrid and multi-cloud, operating model, delivery, cost, risk | strategic, technical |
| `head-of-hr` | motivation, conflict, values, leadership, expectations | behavioural |
| `head-of-engineering` | delivery across teams, hiring, build vs buy, tech debt, org design, metrics | situational, scenario |
| `lead-engineer` | collaboration, code review, on-call, mentoring, technical disagreement, legacy code | situational, behavioural |
| `principal-peer` | system design: a problem whose constraints change as you answer | scenario |
| `bar-raiser` | "tell me about a time", in the style of Amazon's Leadership Principles | behavioural |

122 questions in all. The lead seat takes about 60% of the time, handovers are explicit, and a
seat may cut in once when an answer strays into its lane (`references/panel-rules.md`).

## Where the questions come from

Every question says what a strong answer contains, lists red flags and follow-ups, and does one
of two things:

- **cites a page and quotes it.** The quote is checked against the live page. Sources include
  the Microsoft and AWS cloud adoption frameworks, AWS, Azure and Google Cloud's well-architected
  frameworks, the FinOps Foundation, the CNCF platforms paper, Team Topologies, DORA, the Google
  SRE book, Google's code-review guide and re:Work research, the System Design Primer, StaffEng,
  and Amazon's own Leadership Principles. Pages that show what interviewers *ask* (StaffEng,
  Amazon's interview-prep pages) ground the personas' interview
  style instead of individual rubrics.
- **says `source: none (common practice)`**, for standard interview wisdom that no single page
  states. That's 15 of the 122. Honest silence beats a borrowed citation.

## Why the checks are strict

The first version of the bank cited a source for every question. An independent review that
fetched every page found 20 of 49 rubrics citing pages that did not support them: one page was
cited 13 times for a method it never mentions, and one URL was dead. A check that a source
*exists* passed all of them. So now each citation carries a quote, and `--verify` fetches the
page and looks for it.

## What you supply

A private **brief**: company, seats, topics, level, JD paths, the path to your evidence base,
and where to save runs. Optionally, a **private bank** of questions specific to one employer, in
the same format; the panel asks those first. The brief, the private bank and the transcripts
all stay outside this repo. Use a real interviewer's name only if you've confirmed it.

## The debrief

A fresh reviewer reads the saved transcript. For each answer it gives what you said, what the
seat was listening for and why, and the step from one to the other, with the evidence-base line
you could have used. It ends with reflection prompts for you to answer before the next run.

## What it will not do

It won't predict an outcome, write answers for you to memorise, research people, or run
during a real interview.

## Check

```bash
python3 scripts/check_bank.py --summary            # structure, every bank
python3 scripts/check_bank.py --verify             # fetch each source, find its quote
python3 scripts/check_bank.py path/to/private.md   # a private bank
python3 -m pytest tests -q
```
