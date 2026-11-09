---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

ADR 4 says we never call payments synchronously, but the code does now and that's fine. Supersede it.
