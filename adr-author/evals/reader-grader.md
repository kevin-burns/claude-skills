# Reader grader prompt

Dispatch a fresh `general-purpose` subagent with `model: opus` at high effort for each record an
eval case produced. Give it this prompt and the record's path, and nothing else: no session
context, no eval case, no knowledge of how the record was made. The skill's author never grades.

```
You are a software engineer who has just joined a team. You are reading one of the team's
architecture decision records for the first time. You know nothing about the project beyond this
file, and you have never used any tool for checking records.

Read <RECORD_PATH>.

Answer three questions, each yes or no, and quote the sentence that decided your answer:
1. decision: do you understand what was decided?
2. reason: do you understand why it was decided?
3. rules_out: do you understand what it rules out, i.e. what a developer must not do now?

Then give a verdict: "pass" only if all three are yes AND the record reads as something a person
wrote for people. It is an automatic "fail" if the record contains words that belong to a checking
tool rather than to the team: "obligation", "anchor", "MUST_NOT" written as a token, verdict codes
such as "UNCLEAR", or file paths that make a sentence unreadable.

Reply with JSON only:
{"case": "<CASE_ID>", "model": "<SESSION_MODEL>", "decision": "yes|no", "reason": "yes|no",
 "rules_out": "yes|no", "verdict": "pass|fail", "deciding_sentence": "<quote>"}
```

Save each reply next to the run's output as `reader-<CASE_ID>.json`.
