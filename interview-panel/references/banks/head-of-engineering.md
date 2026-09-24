# Question bank: head-of-engineering

Topics: delivery, hiring-and-growing, build-vs-buy, tech-debt-vs-roadmap, org-design,
engineering-metrics, underperformance, working-with-product.

20 questions for a Head of Engineering seat: delivery across several teams, hiring and growing
engineers, build vs buy, trading off tech debt against the roadmap, org design, engineering
metrics, handling underperformance, and working with product. For a Lead, Staff or Principal
cloud/platform/software candidate. Every sourced rubric below cites a page actually fetched on
2026-09-24, with a quote from that page. See the persona at `../personas/head-of-engineering.md`
and the rules at `../panel-rules.md`.

---

### HE01 Keeping several teams moving to one date
- seat: head-of-engineering
- topic: delivery
- type: behavioural
- level: both
- question: Tell me about a time you had to keep several teams moving toward the same delivery date without them reporting to you. What did you actually do?
- strong answer contains:
  - Names a specific cross-team delivery and the teams involved, not a generality
  - Describes a concrete coordination mechanism used — a shared dependency tracker, a standing sync, a single named owner per workstream
  - Shows the candidate surfacing risk to stakeholders before the deadline, not at it
  - States the actual outcome, including if the date moved
- red flags:
  - Coordination described only as "we all talked regularly" with no mechanism
  - Candidate can't say who owned the final delivery decision
- follow-ups:
  - Which team slipped first, and how did you find out?
  - What would you build differently next time to catch that earlier?
- source: https://handbook.gitlab.com/job-families/engineering/development/management/engineering-manager/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "They own the delivery of product commitments and are always looking to improve productivity."

### HE02 A roadmap item that's about to miss
- seat: head-of-engineering
- topic: delivery
- type: scenario
- level: both
- question: Two months into the quarter, it's clear a team's roadmap item is going to miss, and three other teams are waiting on it before they can start their own work. Walk me through what you do.
- strong answer contains:
  - Gets an evidence-based revised forecast rather than accepting "we'll catch up"
  - Tells the downstream teams before they find out on their own
  - Separates cutting scope from cutting quality when re-planning
  - Owns the decision rather than only relaying the bad news
- red flags:
  - Promises to recover the lost time with no basis
  - Downstream teams hear about the slip from someone else first
- follow-ups:
  - Now the delay is caused by a dependency your team doesn't control — a vendor's API. What changes about how you handle it?
  - Now it's week 11 of a 12-week quarter before you find out. What do you do with almost no runway left?
  - Now one of the three downstream teams is outside engineering — sales already promised a customer a date off this. How does that change the conversation?
- source: none (common practice)
- source-type: none

### HE03 A team that under-delivers despite capable people
- seat: head-of-engineering
- topic: delivery
- type: situational
- level: lead
- question: You're running four teams and one of them consistently under-delivers against its own sprint commitments, even though the individuals on it are capable. What's your read, and what do you do?
- strong answer contains:
  - Investigates before acting — scope creep, unclear ownership, interrupt load, or a manager problem, not just "the team is slow"
  - Distinguishes a capacity problem from a commitment-setting problem
  - Names a concrete intervention tied to the actual cause found
  - Follows up with a measurable check that the intervention worked
- red flags:
  - Jumps straight to performance-managing individuals without diagnosing the team-level cause
  - No follow-up check on whether the fix actually worked
- follow-ups:
  - What did you find was actually driving it?
  - How long did you give the fix before deciding it wasn't working?
- source: none (common practice)
- source-type: none

### HE04 Fixing a hiring process after a bad hire
- seat: head-of-engineering
- topic: hiring-and-growing
- type: behavioural
- level: both
- question: Tell me about hiring for a role where you'd been burned before — a bad previous hire in that same seat. What did you change?
- strong answer contains:
  - Names the specific signal that was missed in the earlier hire, not a vague "wasn't a fit"
  - Describes a concrete change to the process — a different interview question, a changed bar, a reference check done differently
  - Ties the change back to actually growing a world-class team, not just filling the seat
  - States a real, checkable outcome of the changed process
- red flags:
  - Can't name what was actually missed the first time
  - "Changed the process" turns out to mean nothing concrete changed
- follow-ups:
  - Who else did you involve in redesigning that step?
  - Has the new process caught a bad fit since?
- source: https://handbook.gitlab.com/job-families/engineering/development/management/engineering-manager/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "hiring a world-class team, and putting them in the best position to succeed"

### HE05 Growing someone when there's no open Staff role
- seat: head-of-engineering
- topic: hiring-and-growing
- type: situational
- level: both
- question: One of your senior engineers is ready for the next step but there's no open Staff role on your team right now. What do you actually do?
- strong answer contains:
  - Distinguishes what's in the manager's control (scope, visibility, stretch work) from what needs a title change
  - Names a concrete coaching mechanism — regular career conversations, a documented growth plan — rather than a one-off promise
  - Is honest with the engineer about the real constraint instead of implying a title is imminent
  - Considers the retention risk explicitly rather than assuming loyalty
- red flags:
  - Vague reassurance with no concrete plan attached
  - No acknowledgment of the retention risk
- follow-ups:
  - What would you actually put in front of them in writing?
  - What do you do if they get an offer at the next level elsewhere?
- source: https://rework.withgoogle.com/intl/en/guides/following-the-data-the-research-behind-great-managers (retrieved 2026-09-24)
- source-type: answer
- evidence: "Develop People involves setting clear expectations, providing relevant feedback and coaching, engaging in meaningful career conversations"

### HE06 Hire senior or grow from within
- seat: head-of-engineering
- topic: hiring-and-growing
- type: strategic
- level: principal
- question: How do you decide whether to grow this org's capability by hiring senior people in, or by developing the mid-level engineers you already have?
- strong answer contains:
  - Treats it as a genuine trade-off — hiring senior brings speed and a fresh perspective, growing internal talent builds retention and institutional knowledge — rather than a default position
  - Names a concrete signal for when each path is right (urgency of the gap, whether the capability is core or one-off)
  - Considers the cost of hiring seniors on the growth ceiling available for people already on the team
  - Gives a real example of a decision made either way
- red flags:
  - Absolute position ("always hire senior" or "always grow from within") with no nuance
  - No consideration of the effect on existing team members' growth ceiling
- follow-ups:
  - Tell me about a time you chose the option you don't usually favor. Why?
  - How do you know a capability gap is core enough to hire externally for?
- source: none (common practice)
- source-type: none

### HE07 Build vs buy on one component
- seat: head-of-engineering
- topic: build-vs-buy
- type: scenario
- level: both
- question: A team wants six weeks to build an internal permissions and entitlements service in-house instead of using an off-the-shelf identity provider. How do you evaluate that?
- strong answer contains:
  - Frames the decision at the component level, not "build the whole system or buy the whole system"
  - Weighs whether this component is core to the product's differentiation versus commodity capability
  - Names concrete evaluation criteria beyond cost — data residency, integration effort, lock-in, ongoing maintenance burden
  - Doesn't default to buy or build without asking what's differentiating here
- red flags:
  - Treats build vs buy as a single company-wide policy rather than a per-component decision
  - No mention of the ongoing maintenance cost of the build option
- follow-ups:
  - Now the off-the-shelf option doesn't support one regulatory requirement you actually need. Does that change the call?
  - Now the team that would build it in-house is the same team that would maintain the bought integration. Does that change your answer?
- source: https://www.thoughtworks.com/insights/blog/technology-strategy/enterprises-build-buy-software (retrieved 2026-09-24)
- source-type: answer
- evidence: "The decision has shifted from building or buying systems to building or buying components."

### HE08 Where the build-vs-buy line sits
- seat: head-of-engineering
- topic: build-vs-buy
- type: strategic
- level: principal
- question: Where do you draw the line between what this engineering org should always build itself and what it should never build?
- strong answer contains:
  - Ties "always build" to what's core to the product's identity or competitive differentiation
  - Ties "never build" to commodity capability available as a well-supported component
  - Names the architecture step that has to happen before the decision — identifying the components, not deciding build-or-buy for the whole system upfront
  - Acknowledges the line moves over time as the product and market change
- red flags:
  - No distinction between differentiating and commodity capability
  - Treats the line as fixed forever rather than something to revisit
- follow-ups:
  - Give me a capability you'd have said "never build" five years ago that you'd reconsider today.
  - Who gets to make the call when a team disagrees with where you've drawn the line?
- source: https://www.thoughtworks.com/insights/blog/technology-strategy/enterprises-build-buy-software (retrieved 2026-09-24)
- source-type: answer
- evidence: "The first step is to design your system architecture blueprint with the required components"

### HE09 A tech lead flags fast-growing debt
- seat: head-of-engineering
- topic: tech-debt-vs-roadmap
- type: scenario
- level: both
- question: Your roadmap for the quarter is full, and one of your tech leads says a module is accumulating debt fast enough that it'll slow every feature that touches it. How do you decide what to do?
- strong answer contains:
  - Distinguishes debt in code that's touched frequently (worth paying down) from debt in stable, rarely-touched code (safe to leave)
  - Treats the trade-off as a real cost/benefit decision, not a binary "always pay it down" or "always ship features"
  - Gets a concrete estimate of the ongoing cost before deciding, rather than reacting to alarm alone
  - Names who actually has to agree to the trade-off — not a unilateral engineering call if it affects the roadmap
- red flags:
  - Automatically defers all debt work in favor of features with no cost/benefit check
  - No distinction between debt in active versus dormant code
- follow-ups:
  - What number or evidence would have changed your decision?
  - How do you keep this from becoming a recurring fight every quarter?
- source: https://martinfowler.com/bliki/TechnicalDebt.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "areas of high activity need a zero-tolerance attitude to cruft, because the interest payments are cripplingly high"

### HE10 Taking on debt deliberately to hit a date
- seat: head-of-engineering
- topic: tech-debt-vs-roadmap
- type: situational
- level: both
- question: A team wants to take on debt deliberately — ship something rougher than they'd like — to hit a date. How do you decide whether that's the right call?
- strong answer contains:
  - Distinguishes a deliberate, planned trade-off with an intent to repay from simply cutting corners with no plan
  - Requires an explicit decision to take on the debt, not something that happens by default under pressure
  - Asks what the actual repayment plan is and when it will happen
  - Names a real cost the team accepted when they got the timing wrong before
- red flags:
  - Treats "we're under pressure" as sufficient justification with no repayment plan attached
  - Can't distinguish this from reckless, unplanned corner-cutting
- follow-ups:
  - Tell me about a case where the debt was never repaid. What happened?
  - Who tracks whether repayment actually happens, six months later?
- source: https://martinfowler.com/bliki/TechnicalDebt.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "Technical Debt is a metaphor, coined by Ward Cunningham, that frames how to think about dealing with this cruft"

### HE12 Inheriting a siloed org
- seat: head-of-engineering
- topic: org-design
- type: situational
- level: both
- question: You inherit an org where every team has become a rigid silo — nobody moves between them, and every cross-team request goes through a formal handoff. What's your diagnosis, and what's the fix?
- strong answer contains:
  - Diagnoses the interaction-mode problem specifically — too much request-based interaction and not enough deliberate collaboration where it's actually needed
  - Distinguishes collaboration mode, meant to be temporary and high-bandwidth, from an as-a-service mode with a clear boundary
  - Proposes a concrete, bounded change rather than a full reorg on day one
  - Recognizes over-collaboration is also a failure mode, not just under-collaboration
- red flags:
  - Prescribes constant collaboration as the fix for everything, creating a new bottleneck
  - No distinction drawn between the different ways teams can interact
- follow-ups:
  - Which team relationship did you change first, and why that one?
  - How did you know the new interaction mode was working, versus just different?
- source: https://teamtopologies.com/key-concepts (retrieved 2026-09-24)
- source-type: answer
- evidence: "Collaboration: Working closely together (high bandwidth, high cost)"

### HE13 Standing up a new platform team
- seat: head-of-engineering
- topic: org-design
- type: scenario
- level: principal
- question: You're asked to stand up a new platform team from scratch to serve four existing product teams. Walk me through how you'd design it.
- strong answer contains:
  - Starts from a real, current pain point the product teams have, not a speculative capability
  - Names a concrete first capability to build and ship as self-service, not a broad mandate
  - Plans an explicit path from high-touch collaboration mode into a lower-cost, self-service interaction as the capability matures
  - Considers team size against cognitive load, not just headcount available
- red flags:
  - Platform team's first move is a big-bang redesign with no immediate user
  - No plan to move out of hands-on collaboration mode over time
- follow-ups:
  - Now you only get two engineers for this team, not the five you asked for. What do you cut first?
  - Now one of the four product teams refuses to adopt the new platform. What do you do?
  - Now leadership wants a visible win in six weeks. What ships first?
- source: https://teamtopologies.com/key-concepts (retrieved 2026-09-24)
- source-type: answer
- evidence: "Platform team: a grouping of other team types that provide a compelling internal product to accelerate delivery by Stream-aligned teams"

### HE14 What goes on the engineering dashboard
- seat: head-of-engineering
- topic: engineering-metrics
- type: technical
- level: both
- question: Walk me through the metrics you'd actually put on a monthly engineering dashboard for this org, and why those and not others.
- strong answer contains:
  - Names concrete delivery metrics — change lead time, deployment frequency, and a stability measure like change fail rate — rather than only activity counts
  - Distinguishes throughput measures from stability measures and explains why both matter together
  - Avoids relying on one single metric to represent overall health
  - Ties the chosen metrics to what the specific audience (board, engineers, finance) actually needs, not one dashboard for everyone
- red flags:
  - Only offers activity metrics (tickets closed, lines of code) with no delivery or stability measure
  - Treats speed and stability as a trade-off rather than something to track together
- follow-ups:
  - Which of these would you actually put in front of the CEO, and which stay internal to engineering?
  - What would make you conclude one of these metrics is being gamed?
- source: https://dora.dev/guides/dora-metrics-four-keys/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "Change lead time: The amount of time it takes for a change to go from committed to version control to deployed in production."

### HE15 The CEO wants board metrics in two weeks
- seat: head-of-engineering
- topic: engineering-metrics
- type: situational
- level: both
- question: The CEO asks you for "engineering productivity metrics" for the board deck with two weeks' notice. What do you actually send, and what do you push back on?
- strong answer contains:
  - Distinguishes what the CEO actually needs — a proxy for engineering's contribution to business strategy — from a deep optimization metric they won't be able to interpret
  - Reuses existing planning or delivery metrics rather than building something new under time pressure
  - Pushes back on being measured purely by efficiency metrics that don't reflect actual impact
  - Explains the metric in terms the board can act on, not raw numbers
- red flags:
  - Sends raw efficiency metrics (story points, commits) with no framing for a non-technical audience
  - Doesn't push back at all, even when the ask doesn't fit the timeline or audience
- follow-ups:
  - What did you leave out of the board deck on purpose, and why?
  - How do you handle it if the board later misreads one of these numbers?
- source: https://lethain.com/measuring-engineering-organizations/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "there are many modes of engineering measurement, each of which is appropriate for a given scenario"

### HE16 Stopping a metric from being gamed
- seat: head-of-engineering
- topic: engineering-metrics
- type: strategic
- level: principal
- question: How do you avoid a team gaming its own delivery metrics once you start reporting on them?
- strong answer contains:
  - Recognizes that setting a metric as an explicit target increases the risk it gets gamed
  - Tracks metrics with deliberate tension between them (speed and stability together) rather than one metric in isolation
  - Uses metrics as a guide for improvement conversations, not a performance score for individuals or teams to hit
  - Reviews the metric's own integrity periodically, not just the number it reports
- red flags:
  - Sets a single metric as a hard target with no counter-metric
  - Uses delivery metrics to rank or compare individuals directly
- follow-ups:
  - Tell me about a metric you had to stop using because it got gamed.
  - How do you tell the difference between a metric improving because behavior actually improved, versus because it's being gamed?
- source: https://dora.dev/guides/dora-metrics-four-keys/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "increases the likelihood that teams will try to game the metrics"

### HE17 A capable engineer who was genuinely underperforming
- seat: head-of-engineering
- topic: underperformance
- type: behavioural
- level: both
- question: Tell me about a capable engineer on your team who was genuinely underperforming. What did you actually do, from the first conversation onward?
- strong answer contains:
  - Describes a real, specific performance gap, not a personality clash relabeled
  - Shows a direct, clear conversation naming the gap early, rather than letting it run unaddressed
  - Distinguishes whether the block was importance, disagreement about the expectation, or missing resources, and acted differently for each
  - States the actual outcome, including if it ended in a plan, a role change, or an exit, and how that was handled
- red flags:
  - Waited months before naming the problem directly
  - No account of what actually happened at the end
- follow-ups:
  - What was the specific moment you knew a direct conversation, not more coaching, was the next step?
  - What would you have done differently in how early you raised it?
- source: https://larahogan.me/blog/performance-improvement-plans/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "Do I believe this person will be able to meet these expectations within 30 days, and consistently thereafter?"

### HE18 Pushed to write a PIP you're not convinced by
- seat: head-of-engineering
- topic: underperformance
- type: situational
- level: both
- question: HR wants you to put someone on a formal performance improvement plan, but you're not convinced it will change anything. What do you do?
- strong answer contains:
  - Separates whether the person can actually meet the role's expectations from whether a plan alone will fix it
  - Considers alternatives explicitly — a role change, a negotiated exit with severance — rather than defaulting to whatever HR's template says
  - Insists the plan's expectations are the same ones anybody in the role would be held to, not softened or inflated for this person
  - Pushes back on the process when appropriate rather than just executing it
- red flags:
  - Runs the process purely as a formality with no real belief it will work
  - Accepts HR's template without checking whether its expectations match the real role
- follow-ups:
  - What did you actually push back on, and did it change anything?
  - How did you handle it with the rest of the team once the outcome was known?
- source: https://larahogan.me/blog/performance-improvement-plans/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "make sure that the contents of the PIP are measurable and time-bound"

### HE19 A real disagreement with a product lead
- seat: head-of-engineering
- topic: working-with-product
- type: behavioural
- level: both
- question: Tell me about a real disagreement with a product lead about what to build next, that you actually had to resolve.
- strong answer contains:
  - Names the specific disagreement and what each side was optimizing for
  - Shows engineering's case made in terms product could act on — cost, risk, sequencing — not just technical preference
  - Describes the actual resolution mechanism, not just that a decision eventually got made
  - States what the working relationship looked like afterward
- red flags:
  - Frames product as an obstacle rather than a partner with legitimate priorities
  - No account of how the disagreement was actually resolved
- follow-ups:
  - What would you have done if you'd lost that argument?
  - How's the relationship with that product lead now?
- source: https://www.svpg.com/empowered-product-teams/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "in strong product organizations, teams exist for a very different purpose"

### HE20 Getting engineers into product discovery, not just delivery
- seat: head-of-engineering
- topic: working-with-product
- type: situational
- level: both
- question: How do you make sure your engineers are shaping the product roadmap, not just being handed a spec to build?
- strong answer contains:
  - Wants engineers genuinely involved in problem discovery, not only implementation, so they can influence what gets built
  - Names a concrete mechanism — engineers in discovery conversations, a shared roadmap review — rather than an aspiration
  - Recognizes this requires product's buy-in too, not something engineering can force unilaterally
  - Gives a real example of an engineer's input changing what got built
- red flags:
  - Describes engineering as purely execution against a spec with no upstream input
  - No concrete mechanism, only a stated value
- follow-ups:
  - Give me an example where an engineer's input actually changed the plan.
  - How do you handle a product lead who resists engineers being in discovery conversations?
- source: https://www.svpg.com/empowered-product-teams/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "The product vision is the shared objective for the product organization."
