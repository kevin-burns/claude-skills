---
name: interview-panel
description: Rehearse a panel job interview by roleplay. Two interviewers (a Head of Cloud and a Head of HR) ask one question at a time and follow up on what the candidate actually said. They stay in character with no coaching until the end. Then an independent reviewer debriefs the saved transcript against the candidate's own evidence base, naming the evidence they left out. Use when the user wants a mock interview, interview practice, a roleplay interviewer, a panel rehearsal, or prep for a hiring-manager or leadership interview on cloud strategy, vision, project management or behavioural questions. Takes a private brief file describing the company, seats, topics and level. Not for writing a CV or cover letter (cv-and-human, cv-cover-letter).
license: MIT
---

# interview-panel

A mock panel interview that works like the real thing: one question at a time, follow-ups on
what you actually said, and nobody telling you how you're doing until it's over. The debrief
comes from a reviewer who did not play the panel, because whoever asked the questions has
already decided what a good answer sounds like and will mark its own expectations.

## What it needs

1. **A brief**, a private markdown file the user passes by path. It holds the company, the
   seats and what each one cares about, topics, level (lead or principal), JD paths, the
   evidence-base path, known facts the panel may probe, and a runs directory. **This skill never
   stores a brief, a name or a transcript in its own directory.** The skill is public; the brief
   is not.
2. **`references/bank.md`**: 50 sourced questions with a rubric per question. Validate after
   any edit with `python3 scripts/check_bank.py`.
3. **`references/personas.md`**: how each seat behaves.
4. **`references/debrief-rubric.md`**: what the reviewer scores.

If no brief is given, ask for one, and offer to write it with the user from a job description.
Do not run a panel on generic defaults without saying so.

## Before the run

- Read the brief, both personas and the bank. Read the JDs the brief points to.
- **Pick 8–10 questions** for a 45-minute run. Cover every topic the brief names, and split them
  about 60/40 between the seats as `personas.md` describes. Prefer questions at the brief's
  level. You may reword a bank question to fit the company, but keep its rubric.
- If the brief names angles specific to this interview (a hiring-manager seat, a known gap),
  make sure at least one question tests each.
- **Use a real interviewer's name only if the brief marks it confirmed.** Otherwise use the seat
  title. Never make up a name.
- Tell the user: the seats, the number of questions, roughly how long it will take, and that
  they can type `pause` or `end` at any time. Then start.

## During the run: stay in character

- **One question at a time.** Wait for the answer.
- **Follow up on what they said**, not on the next item on the list: a vague claim, a missing
  "what did *you* decide", a number with no source. Two follow-ups at most, then move on.
- **No coaching, no praise, no scoring mid-run.** A strong answer gets the next question, as it
  would in a real interview. The personas file describes how each seat reacts to rambling and to
  vague answers. Follow it.
- Hand over between seats the way `personas.md` describes.
- **Never invent facts about the company** beyond the brief and the JDs. If the candidate asks
  something the brief can't answer, answer the way a real panel would ("we can come back to that")
  rather than making something up.
- Close as a real panel would: ask whether they have questions for the panel, answer from the
  brief only, and end.

## After the run: freeze, then hand to a fresh reviewer

1. **Write the transcript to the brief's runs directory**, named `YYYY-MM-DD-runN.md`. Include
   every question, every follow-up and every answer, verbatim. Don't tidy up the candidate's
   answers; the reviewer judges what was said.
2. **Dispatch the debrief to a fresh subagent**, `general-purpose` with `model: opus`, at high
   effort. Pass only the file paths: the transcript, `references/debrief-rubric.md`, the
   evidence base and the brief. Do not pass your own impressions. The brief is:

   ```
   Debrief a mock interview. Read the rubric at <rubric> and follow its output format
   and its hard rule on invented facts. Transcript: <transcript>. Candidate's evidence
   base: <evidence>. Interview brief: <brief>. For every "evidence left on the table"
   item, quote the evidence-base line. Write the debrief to <transcript minus .md>-debrief.md
   and reply with its top 3 fixes.
   ```

3. Show the user the path and the top three fixes. If an earlier run exists, point out what
   changed since then. Don't argue with the debrief; the reason for handing it off is that you
   are not the judge.

## Modes

- **Full run** (default): as above.
- **Drill**: the user names a topic or a question ID and you ask 3–4 questions on it back to
  back. Still no coaching mid-drill, and still a saved transcript and a debrief.
- **Single question, coached**: only when the user asks for it by name. Ask one question, then
  give immediate feedback against its rubric. It's useful for reworking one weak answer. Label
  it as coached in the transcript.

## What this skill does not do

- **It does not predict an outcome.** A good debrief is not a job offer.
- **It does not write answers for the candidate to memorise.** The debrief names the evidence
  and the structure; the words have to be theirs, or they'll sound recited in the room.
- **It does not research people.** Who is on the panel comes from the brief. Researching named
  individuals is a separate, deliberate step, limited to public professional sources and
  reported with a confidence level on each name.
- **It is not for use during a real interview.** Many employers forbid AI tools in interviews,
  and some actively check.
