# interview-panel

Rehearse a panel interview by roleplay. Two interviewers ask one question at a time, follow up
on what you actually said and give no coaching until the end. Then a reviewer who did not play
the panel debriefs the transcript against your own evidence base.

Part of [claude-skills](../README.md).

## What it does

- **Two seats, one realistic panel.** A Head of Cloud (strategy, vision, delivery, operating
  model, cost, risk) and a Head of HR (motivation, conflict, values, leadership, expectations).
  They split the time about 60/40 and hand over between themselves the way a real panel does.
- **A sourced question bank.** Fifty questions. Each has what a strong answer contains, red
  flags, follow-ups, and the public framework its rubric came from: the cloud adoption
  frameworks, Well-Architected, the FinOps Foundation, the CNCF platforms paper, Team
  Topologies, DORA, the Scrum Guide, the APM, and structured-interview guidance.
  `scripts/check_bank.py` fails any question without a dated source.
- **Follow-ups on your answer, not the next line of a script.** Probing for specifics is the
  part a question list can't practise.
- **An independent debrief.** Whoever asked the questions already decided what a good answer
  sounds like, so a fresh subagent marks the saved transcript instead. For anything you could
  have used but didn't, it quotes the line in your evidence base.

## What you supply

A private **brief**: company, seats, topics, level, JD paths, the path to your evidence base,
and where to save runs. It stays outside this repo, and so do the transcripts. Use a real
interviewer's name only if you've confirmed it.

## What it will not do

It won't predict an outcome, write answers for you to memorise, research people, or run
during a real interview.

## Check

```bash
python3 scripts/check_bank.py --summary
python3 -m pytest tests -q
```
