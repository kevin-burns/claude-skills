---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?hook-and-human"'
---

Did Claude actually invoke `hook-and-human`? Added 2026-10-02 (claude-skills-b9nk.5): the first real
run showed the no-plugin arm passing the `llm` routing grader too, so that grader alone cannot
say whether the skill fired. This one can. It is reported as an indicator, not scored.
