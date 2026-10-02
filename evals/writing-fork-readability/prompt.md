---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

People keep telling me this section of my README is hard to follow. Where exactly do they get
lost? I don't want it rewritten, I want to know where it falls apart.

"Install the agent. Configure it. It then reads the manifest, which the controller has to have
already reconciled, otherwise the sidecar retries. This is why the cache matters. Set it before
the first run, unless you use the operator, in which case it is set for you, and the flag is
ignored. That also covers the webhook."
