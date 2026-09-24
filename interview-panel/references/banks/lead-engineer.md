# Question bank: lead-engineer

Topics: day-to-day-collaboration, code-review, on-call-and-incidents, mentoring,
technical-disagreement, estimating, legacy-code.

18 questions for a Lead Engineer seat: a future peer or direct report, testing day-to-day
collaboration, code review, on-call and incidents, mentoring, technical disagreement,
estimating, and legacy code. For a Lead, Staff or Principal cloud/platform/software candidate.
Every sourced rubric below cites a page actually fetched on 2026-09-24, with a quote from that
page. See the persona at `../personas/lead-engineer.md` and the rules at `../panel-rules.md`.

---

### LE01 A peer disagreement over approach
- seat: lead-engineer
- topic: day-to-day-collaboration
- type: behavioural
- level: both
- question: Tell me about a time you and a peer disagreed about how to approach a piece of work you were both going to be touching. How did the day-to-day actually go?
- strong answer contains:
  - Describes the specific disagreement and what each person's approach would have looked like
  - Shows concrete collaboration actions — a shared doc, a pairing session, an agreed compromise — not just "we talked it out"
  - States what actually got built and whether it matched either original approach
  - Reflects on what made the working relationship function afterward
- red flags:
  - Vague account with no specific approaches named
  - Implies one person just deferred with no real discussion
- follow-ups:
  - What did you concede, if anything?
  - How do you two work together differently now, if at all?
- source: none (common practice)
- source-type: none

### LE02 Pairing across a working-style mismatch
- seat: lead-engineer
- topic: day-to-day-collaboration
- type: situational
- level: both
- question: You're paired with someone whose working style is very different from yours — they want everything speced out up front, you'd rather start coding and iterate. How do you actually get work done together?
- strong answer contains:
  - Names a concrete adaptation made on both sides, not just "I adjusted"
  - Distinguishes where more upfront spec genuinely helped from where it just slowed things down
  - Shows this being negotiated explicitly rather than silently resented
  - Gives a real example of work that came out of that pairing
- red flags:
  - Frames the other person's style as simply wrong
  - No concrete adaptation described, just tolerance
- follow-ups:
  - What would you do if this was a permanent pairing, not a one-off?
  - What did you learn about your own style from working with them?
- source: none (common practice)
- source-type: none

### LE03 Pushing back hard in a code review
- seat: lead-engineer
- topic: code-review
- type: behavioural
- level: both
- question: Tell me about a code review where you had to push back hard on something a peer submitted. Walk me through it.
- strong answer contains:
  - Names the specific concern and why it mattered to code health, not a style preference
  - Distinguishes a blocking issue from a nitpick, and treats them differently in the review
  - Shows the actual back-and-forth, including if the author pushed back and what happened
  - States what shipped in the end
- red flags:
  - Can't distinguish a blocking concern from a matter of personal taste
  - No account of what the author said back
- follow-ups:
  - Did anything you flagged turn out to be wrong? What did you do then?
  - How would you have escalated if you two couldn't agree?
- source: https://google.github.io/eng-practices/review/reviewer/standard.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "Technical facts and data overrule opinions and personal preferences."

### LE04 Working code, wrong design
- seat: lead-engineer
- topic: code-review
- type: scenario
- level: both
- question: You're reviewing a peer's pull request. It works and it's tested, but you think the design is wrong in a way that will cost the team later. What do you do?
- strong answer contains:
  - Weighs shipping a working, tested change against blocking for a design concern, rather than reflexively blocking
  - Separates what must change now from what can be raised as a follow-up
  - Explains the reasoning behind the design concern rather than asserting a preference
  - Knows when to approve with a comment versus actually blocking
- red flags:
  - Blocks indefinitely over a non-blocking design preference
  - Approves without raising the concern at all, to avoid conflict
- follow-ups:
  - Now there's a deadline in two hours and the author says there's no time to rework it. What do you do?
  - Now you're the more junior of the two engineers on this review. Does your approach change?
  - Now the author simply disagrees that it's a real problem. What's your next move?
- source: https://google.github.io/eng-practices/review/reviewer/standard.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "reviewers should favor approving a CL once it is in a state where it definitely improves the overall code health of the system"

### LE05 Reviewing a much more junior engineer
- seat: lead-engineer
- topic: code-review
- type: situational
- level: lead
- question: How do you review code from someone much more junior than you without either rubber-stamping it or crushing their confidence?
- strong answer contains:
  - Distinguishes must-fix issues from teaching opportunities, and marks the difference explicitly in the review
  - Treats review as a chance to teach, not only to gatekeep
  - Still holds the same code-health bar as for anyone else's change
  - Gives a real example of a comment that taught something without blocking unnecessarily
- red flags:
  - Applies a lower bar because the author is junior
  - Every comment reads as a correction with no teaching framing
- follow-ups:
  - Give me an actual comment you left that you think landed well.
  - How do you know when you've under- or over-corrected for seniority?
- source: https://google.github.io/eng-practices/review/reviewer/standard.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "Sharing knowledge is part of improving the code health of a system over time."

### LE06 The worst page you've gotten
- seat: lead-engineer
- topic: on-call-and-incidents
- type: behavioural
- level: both
- question: Tell me about the worst page you've gotten. Walk me through what you actually did, in order.
- strong answer contains:
  - Gives a real, specific incident with an identifiable start and resolution
  - Shows a structured response — triage, communication, mitigation before root cause — rather than just "I fixed it"
  - Names who else got pulled in and how that was coordinated
  - States the actual resolution and what changed afterward
- red flags:
  - Story has no clear structure or timeline
  - Candidate fixed it entirely alone with no communication to anyone
- follow-ups:
  - Who did you loop in, and when?
  - What would you do differently if it happened again tomorrow?
- source: https://sre.google/sre-book/managing-incidents/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "The incident commander holds the high-level state about the incident."

### LE07 A degraded region and nobody else awake
- seat: lead-engineer
- topic: on-call-and-incidents
- type: scenario
- level: both
- question: You're on call. A dashboard shows a service degraded in one region, traffic is still being served, and nobody else is awake yet. What do you do first?
- strong answer contains:
  - Assesses actual user impact before escalating, rather than either ignoring it or panicking
  - Knows a concrete trigger for declaring an incident — customer-visible impact, needing a second team, an hour of unsolved analysis — rather than a gut call
  - Starts documenting as they go, not only after it's resolved
  - Considers whether to wake someone up versus handling it solo, based on the actual severity
- red flags:
  - Either declares a full incident for something trivial, or sits on a real one too long
  - No documentation of actions taken as they happen
- follow-ups:
  - Now a second region starts degrading while you're investigating the first. What changes?
  - Now you realize the fix requires a change only a teammate in a different time zone can make safely. What do you do?
  - Now it's resolved, but you're not sure what actually fixed it. What happens next?
- source: https://sre.google/sre-book/managing-incidents/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "It is better to declare an incident early and then find a simple fix and close out the incident"

### LE08 Writing a postmortem on a teammate's mistake
- seat: lead-engineer
- topic: on-call-and-incidents
- type: situational
- level: both
- question: You write the postmortem for an incident that a teammate's change caused. How do you write it so it actually gets read and acted on, instead of feeling like an accusation?
- strong answer contains:
  - Focuses on the systemic and process causes rather than naming the individual as the cause
  - Still names concretely what happened and why, without softening the facts
  - Produces real action items with owners, not just a narrative
  - Shares it widely enough that others actually learn from it
- red flags:
  - Postmortem reads as blame even if unintentional
  - No concrete action items, just a description of what happened
- follow-ups:
  - How did your teammate react to reading the draft?
  - What made this postmortem actually get read, versus filed away?
- source: https://sre.google/sre-book/postmortem-culture/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "A blamelessly written postmortem assumes that everyone involved in an incident had good intentions and did the right thing with the information they had."

### LE09 Someone who genuinely got better
- seat: lead-engineer
- topic: mentoring
- type: behavioural
- level: both
- question: Tell me about someone you mentored who genuinely got better because of specific things you did, not just time passing.
- strong answer contains:
  - Names the specific skill or gap being worked on, not a vague "helped them grow"
  - Describes concrete mentoring actions — pairing, structured feedback, a stretch task — not just availability
  - Shows a real coaching approach, asking questions rather than only giving answers
  - States a checkable, specific improvement, not just a feeling that it went well
- red flags:
  - Can't name a specific skill that improved
  - Mentoring described as purely "being there" with no concrete action
- follow-ups:
  - What's one thing you tried that didn't work?
  - How did you know it was actually landing, versus them just agreeing with you?
- source: https://rework.withgoogle.com/intl/en/guides/coach-using-the-grow-model (retrieved 2026-09-24)
- source-type: answer
- evidence: "Practice active listening and ask open-ended questions to facilitate the team member's own insight"

### LE10 When someone just wants the answer
- seat: lead-engineer
- topic: mentoring
- type: situational
- level: both
- question: You're mentoring someone who keeps asking you to just tell them the answer instead of working through the problem. What do you actually do in that conversation?
- strong answer contains:
  - Recognizes when to shift from giving answers to asking questions that help them find it themselves
  - Balances not leaving them stuck too long against not solving it for them
  - Names a concrete technique — an open-ended question, a smaller version of the problem — rather than just refusing to help
  - Knows when it's actually faster and kinder to just tell them
- red flags:
  - Always gives the answer, undermining their own problem-solving
  - Always refuses to help regardless of how stuck they are, with no judgment call
- follow-ups:
  - Give me the actual question you'd ask instead of the answer.
  - When would you just tell them, and why?
- source: https://rework.withgoogle.com/intl/en/guides/coach-using-the-grow-model (retrieved 2026-09-24)
- source-type: answer
- evidence: "knows when to stop giving advice and lets the team member choose their next steps"

### LE11 Mentoring someone more senior
- seat: lead-engineer
- topic: mentoring
- type: behavioural
- level: principal
- question: Tell me about mentoring someone more senior than you, or with more tenure — someone you couldn't just tell what to do.
- strong answer contains:
  - Names the specific area where the candidate had something to offer despite the seniority gap
  - Shows influence built through credibility and evidence rather than authority
  - Describes the actual approach taken to make it land without seeming presumptuous
  - States a real outcome, including if it didn't fully land
- red flags:
  - Claims authority they didn't actually have
  - No account of how the seniority gap was actually navigated
- follow-ups:
  - What did you do differently than you would with someone more junior?
  - Did they take the feedback? How did you know?
- source: none (common practice)
- source-type: none

### LE13 Watching a teammate build the wrong thing
- seat: lead-engineer
- topic: technical-disagreement
- type: scenario
- level: both
- question: You're convinced a teammate's architecture choice is wrong, but they've already started building it and it's not clearly worse, just different from what you'd have done. What do you do?
- strong answer contains:
  - Distinguishes a genuine correctness or maintainability problem from a personal stylistic preference
  - Raises the concern directly and early rather than letting it build silently or escalating immediately
  - Brings a real argument or evidence, not just seniority or opinion
  - Commits to the decision once it's actually made, even if it goes the other way
- red flags:
  - Escalates immediately without raising it with the person first
  - Can't actually commit once the decision goes against them, and undermines it afterward
- follow-ups:
  - Now you're the more junior person in the disagreement. Does your approach change?
  - Now it's two weeks before the deadline and there's no time to rework it either way. What do you do?
  - Now the decision goes against you and it later turns out you were right. What do you do with that?
- source: https://www.aboutamazon.com/about-us/leadership-principles (retrieved 2026-09-24)
- source-type: answer
- evidence: "Leaders are obligated to respectfully challenge decisions when they disagree, even when doing so is uncomfortable or exhausting."

### LE14 Getting to consensus when neither side is convinced
- seat: lead-engineer
- topic: technical-disagreement
- type: situational
- level: principal
- question: How do you actually get to consensus with a peer on a code review when neither of you is going to be convinced by the other's argument?
- strong answer contains:
  - Tries to reach consensus directly first, through the content of the discussion, before escalating
  - Moves to a synchronous conversation when written back-and-forth stalls, and records the outcome afterward
  - Names a real escalation path — a tech lead, a broader team discussion — rather than letting it stall indefinitely
  - Doesn't let the change sit blocked while the disagreement is unresolved
- red flags:
  - Lets the review sit blocked indefinitely with no escalation
  - Escalates immediately without attempting to resolve it directly first
- follow-ups:
  - Who did you actually escalate to, and what did they ask you both for?
  - What did you record afterward so the next person doesn't reopen the same argument?
- source: https://google.github.io/eng-practices/review/reviewer/standard.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "Don't let a CL sit around because the author and the reviewer can't come to an agreement."

### LE15 An estimate for something you've never done
- seat: lead-engineer
- topic: estimating
- type: situational
- level: both
- question: Your manager asks for an estimate on a piece of work you've never done before, and wants a number today. What do you actually give them?
- strong answer contains:
  - Distinguishes a genuine estimate from a fixed time budget being handed to them disguised as a question
  - Gives a real number with its uncertainty stated, rather than either refusing or making one up with false confidence
  - Names what would need to be true to narrow the estimate further, and how long that would take
  - Pushes back on treating a rough number as a firm commitment
- red flags:
  - Refuses to give any number at all
  - Gives a precise-sounding number with no stated uncertainty, for something never done before
- follow-ups:
  - What did you actually say when the real work took longer than the estimate?
  - How do you renegotiate an estimate once you're partway in and it's clearly wrong?
- source: https://basecamp.com/shapeup/1.2-chapter-03 (retrieved 2026-09-24)
- source-type: answer
- evidence: "An appetite is completely different from an estimate."

### LE16 Given a fixed window, not asked for one
- seat: lead-engineer
- topic: estimating
- type: scenario
- level: both
- question: You're given a fixed two-week window for a piece of work, not asked to estimate it. Walk me through how you'd actually plan the work inside that constraint.
- strong answer contains:
  - Recognizes the difference between a time-boxed budget and an open-ended estimate, and adapts the approach accordingly
  - Narrows the problem to fit the window rather than trying to fit the full original idea in
  - Identifies what's core and what's peripheral, and is willing to cut the peripheral parts
  - Uses the constraint productively rather than treating it as unreasonable by default
- red flags:
  - Tries to force the original full scope into the fixed window and slips
  - Never narrows the problem, just works faster and hopes
- follow-ups:
  - Now, four days in, you realize the two-week window was based on a wrong assumption. What do you do?
  - Now the window shrinks to one week with no warning. What's the first thing you cut?
- source: https://basecamp.com/shapeup/1.2-chapter-03 (retrieved 2026-09-24)
- source-type: answer
- evidence: "We use the appetite as a creative constraint on the design process."

### LE17 A feature request on an untested module
- seat: lead-engineer
- topic: legacy-code
- type: technical
- level: both
- question: You're handed a module with no tests and told to add a feature to it. Walk me through what you actually do before writing the feature.
- strong answer contains:
  - Recognizes the module as legacy specifically because it lacks tests, not because it's old or ugly
  - Gets some characterization or safety net in place — even a minimal one — before changing behavior
  - Scopes the change to avoid triggering a full rewrite when a narrower change would do
  - Balances the time spent on safety net against the size of the actual feature
- red flags:
  - Changes behavior directly with no safety net at all, calling it fine because "it's simple"
  - Insists on a full rewrite before touching anything, regardless of the size of the ask
- follow-ups:
  - What's the minimum safety net you'd accept before touching this module?
  - How do you make the case for that time to someone who just wants the feature shipped?
- source: https://understandlegacycode.com/blog/what-is-legacy-code-is-it-code-without-tests/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "To me, legacy code is simply code without tests."

### LE18 A teammate wants a full rewrite
- seat: lead-engineer
- topic: legacy-code
- type: situational
- level: both
- question: A teammate wants to rewrite a legacy module from scratch instead of incrementally improving it. How do you weigh that?
- strong answer contains:
  - Weighs the real risk of a rewrite — losing undocumented behavior the old code handled — against the appeal of a clean start
  - Considers whether the real problem is the code's age or its lack of tests and safety net
  - Proposes incremental improvement as the default, with a rewrite reserved for cases that genuinely justify it
  - Names a concrete criterion for when a rewrite is actually the right call
- red flags:
  - Defaults to "rewrite it" without weighing the risk of losing undocumented behavior
  - No criterion offered for when a rewrite would actually be justified
- follow-ups:
  - What would have to be true for you to actually back the rewrite?
  - Tell me about a rewrite you were part of that went wrong. What happened?
- source: none (common practice)
- source-type: none
