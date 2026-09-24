# Interview Panel — Principal Peer Bank

15 system-design and scenario questions for the `principal-peer` seat: a Staff or Principal
engineer running a design-and-scenario round for Lead, Staff and Principal cloud, platform and
software engineering roles. Every scenario is progressive — each follow-up changes one
constraint (traffic, an outage, budget, a new compliance requirement) rather than moving to an
unrelated topic.

**Topics:** `multi-region-architecture`, `multi-tenant-platform`, `datacenter-migration`,
`zero-downtime-cutover`, `observability`, `cost-blowups`, `reliability-failure-modes`.

Every sourced rubric below carries an `evidence:` quote actually present on the cited page
(retrieved 2026-09-24). Where no single framework page supports a rubric, the block says
`source: none (common practice)` rather than borrowing a URL. See the bottom of this file for
the full source list and what shaped the bank's scope versus its rubrics: the *scope* (which
scenarios a Staff/Principal loop actually tests) draws on the System Design Primer and
staffeng.com's guides on Staff-plus interview loops and signals — see
`references/personas/principal-peer.md` for how that shaped the seat's style. The *rubrics*
below (what a strong answer contains) draw on the AWS Well-Architected Framework, the Google
Cloud Architecture Framework, the Google SRE book, and the Azure Well-Architected Framework.

---

### PP01 Design a Multi-Region Platform
- seat: principal-peer
- topic: multi-region-architecture
- type: scenario
- level: both
- question: Walk me through how you'd design a multi-region deployment for a platform that needs to survive a full region outage. Where do you start?
- strong answer contains:
  - Starts from a reliability target tied to business impact — not "more regions is automatically better"
  - Chooses active-active or active-passive deliberately, naming the cost and complexity trade-off between them rather than defaulting to one
  - Names a data replication and consistency strategy for cross-region state, not just compute redundancy
  - Prefers managed or global services with built-in redundancy over custom failover plumbing where one exists
  - Treats failback as a distinct, planned process from failover, not an afterthought
- red flags:
  - Says "put it in three regions" with no reliability target or RTO/RPO behind the number
  - Treats active-active as free, with no cost or consistency trade-off named
- follow-ups:
  - Traffic just went 10x overnight — what in this design breaks first, and what do you change?
  - One of your two regions just went dark for six hours — walk me through what happens, automatically and manually.
  - Finance says the DR region is too expensive — halve the budget. What do you give up?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/redundancy (retrieved 2026-09-24)
- source-type: answer
- evidence: "Active-active deployments maximize service availability by running multiple instances of a workload simultaneously, each actively handling traffic."

### PP02 Replication Strategy Under Constraint
- seat: principal-peer
- topic: multi-region-architecture
- type: scenario
- level: principal
- question: You're designing the data layer for a multi-region platform. When do you reach for synchronous replication versus asynchronous, and what does each cost you?
- strong answer contains:
  - Names synchronous replication as zero-data-loss but higher-latency, reserved for the highest-priority data
  - Names asynchronous replication as lower-latency with some acceptable data loss, tied to a defined RPO
  - Ties the choice to the RPO of the specific flow rather than picking one policy for the whole platform
  - Recognizes that geographically distant regions add resilience to large-scale disaster at the cost of latency and consistency complexity
- red flags:
  - Picks one replication strategy for the entire platform with no distinction by flow or criticality
  - Can't explain what RPO the choice is protecting
- follow-ups:
  - A regulator says customer data for this workload must stay in-region — how does that change your replication design?
  - You've now got a single global write path and it's the bottleneck at 10x traffic — what do you do?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/redundancy (retrieved 2026-09-24)
- source-type: answer
- evidence: "Determine whether synchronous or asynchronous data replication is necessary for your workload's functionality."

### PP03 Depth Check: Failover Mechanics
- seat: principal-peer
- topic: multi-region-architecture
- type: technical
- level: principal
- question: Walk me through exactly how a request gets routed and served during an active region failover in your design — DNS, load balancer, and all.
- strong answer contains:
  - Names a specific global routing mechanism (latency-based, weighted, or priority) directing traffic away from the failed region
  - Distinguishes automated, health-check-driven failover from any manual approval gate, and says plainly which parts are which
  - Accounts for DNS propagation delay as part of the real recovery time, not an instant switch
  - Addresses what happens to in-flight requests and sessions during the cutover, not just steady-state routing
- red flags:
  - "DNS just switches over" with no mention of propagation delay or health checks
  - Assumes failover is instant with no discussion of in-flight requests
- follow-ups:
  - Your health check itself is now the flaky thing, not the region — what happens?
  - How do you test this failover path without taking down production to find out if it works?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery (retrieved 2026-09-24)
- source-type: answer
- evidence: "For processes outside your control, like DNS propagation, validate potential delays when evaluating recovery times."

### PP04 Isolating Tenants on a Shared Platform
- seat: principal-peer
- topic: multi-tenant-platform
- type: scenario
- level: lead
- question: You're building a multi-tenant internal developer platform for 40 product teams. How do you isolate tenants from each other, and what does that isolation cost you?
- strong answer contains:
  - Names a concrete isolation boundary — namespace, account, cluster, or a self-contained per-tenant-tier unit — rather than "logical separation" left vague
  - Ties the isolation level to blast radius: a noisy or compromised tenant shouldn't be able to degrade another tenant's service
  - Distinguishes tiers of tenant, naming which get dedicated infrastructure versus shared, rather than one isolation model for all 40 teams
  - States the operational cost of stronger isolation — more infrastructure to patch, monitor and upgrade — as a real trade-off, not free
- red flags:
  - "Logical isolation" with no concrete mechanism named
  - No acknowledgment that stronger isolation has an ongoing operational cost
- follow-ups:
  - One tenant's job just took down shared infrastructure for the other 39 — what in your design should have contained that, and didn't?
  - A new compliance requirement says one specific tenant's data can never leave the EU — does that change the platform for everyone, or just for them?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/redundancy (retrieved 2026-09-24)
- source-type: answer
- evidence: "isolated failure domains that contain blast radius"

### PP05 Depth Check: Noisy-Neighbor Defense
- seat: principal-peer
- topic: multi-tenant-platform
- type: technical
- level: principal
- question: Walk me through exactly how you'd stop one tenant's noisy workload from starving another tenant's compute or API quota, without giving every tenant its own cluster.
- strong answer contains:
  - Names concrete preventive mechanisms — per-tenant rate limits, resource quotas, priority classes — rather than "we'd monitor it"
  - Distinguishes prevention (quotas, admission control) from detection (monitoring, alerting) as two things needed together, not one substituting for the other
  - Explains what happens to the noisy tenant's own requests once it hits its limit — degrade gracefully versus hard fail
  - Recognizes shared-cluster efficiency versus isolation as an ongoing trade-off, not a problem solved once
- red flags:
  - "We'd monitor it and react" with no preventive mechanism at all
  - No answer for what happens to the offending tenant itself once throttled
- follow-ups:
  - Now it's not one noisy tenant — it's a synchronized spike across 10 tenants at once. Same defense, or different?
  - Budget's halved — do you keep per-tenant quotas, or is that the first thing to go?
- source: none (common practice)
- source-type: none

### PP06 Sequencing a Data Center Exit
- seat: principal-peer
- topic: datacenter-migration
- type: scenario
- level: both
- question: You're migrating a platform off a physical data center to the cloud, no rewrite budget. Walk me through how you sequence that.
- strong answer contains:
  - Starts with an inventory and dependency analysis of what's actually running before proposing an order
  - Prioritizes by business criticality, sequencing high-risk-if-broken, low-complexity-to-move workloads early enough to learn from, not last
  - Chooses a strategy per workload rather than one blanket "lift and shift everything" or "rewrite everything" answer
  - Names a rollback path for each cutover step, not just a forward plan
- red flags:
  - Proposes a cutover order with no inventory or dependency step first
  - Treats the whole estate as needing the same migration strategy
- follow-ups:
  - Compliance just added a requirement that one of these systems can't touch the public cloud yet — what changes in your sequencing?
  - You're now told the data center lease ends in 90 days, not 9 months — what do you cut from this plan?
- source: none (common practice)
- source-type: none

### PP07 Lift-and-Shift vs Re-Architect
- seat: principal-peer
- topic: datacenter-migration
- type: strategic
- level: principal
- question: Two teams disagree — one wants to lift-and-shift everything to hit the deadline, the other wants to re-architect as they go. How do you decide, and who gets the final call?
- strong answer contains:
  - Frames it as a deliberate trade-off between migration speed and long-term operability, not a single right answer for the whole estate
  - Splits the estate by workload — lift-and-shift for what's low-value or leaving anyway, re-architect for what will carry real load for years
  - Names a decision owner and a documented criterion, rather than letting the split be settled by whoever argues longest
  - Revisits the split once real cloud cost and performance data is in, instead of locking it in at kickoff
- red flags:
  - Applies one migration strategy to the entire estate with no differentiation by workload
  - No named decision owner or criterion — describes an ongoing argument instead of a decision
- follow-ups:
  - The re-architected piece is now going to slip the deadline by a quarter — what do you do?
  - Budget's halved — does that change which pieces get lift-and-shift versus re-architected?
- source: none (common practice)
- source-type: none

### PP08 Zero-Downtime Database Cutover
- seat: principal-peer
- topic: zero-downtime-cutover
- type: scenario
- level: both
- question: Design the cutover for moving a live, stateful production database from an old system to a new one with zero downtime. Walk me through the sequence.
- strong answer contains:
  - Names a dual-write or replication phase that runs before cutover so both systems are consistent, not a single big-bang switch
  - Tests the actual failback/rollback path before cutover day, not only the forward migration
  - Defines a concrete go/no-go checkpoint with a measurable signal, such as replication lag under a stated threshold
  - Treats failback as a separate, equally planned process from the forward cutover, in case it has to be reversed
- red flags:
  - Plans the forward migration only, with no tested rollback
  - The go/no-go decision is a feeling, not a measurement
- follow-ups:
  - You're mid-cutover and replication lag just spiked — do you continue or abort, and how do you know?
  - Now do this across two regions simultaneously — what changes?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery (retrieved 2026-09-24)
- source-type: answer
- evidence: "If failback is not treated as a distinct, well-defined process separate from failover, teams may experience confusion"

### PP09 Depth Check: Testing the Rollback
- seat: principal-peer
- topic: zero-downtime-cutover
- type: technical
- level: principal
- question: Walk me through exactly how you'd test a rollback path for a cutover before you ever run it in production.
- strong answer contains:
  - Uses automation to simulate the failure or rollback scenario in a non-production environment first, not just documents the steps
  - Tests both the mechanics (does the rollback script work) and the timing (does it finish inside the real maintenance window)
  - Treats a successful rollback test as exposing failure pathways to fix before the real cutover, not a formality
  - Names who's on call during the real cutover, informed by what the rollback test showed could go wrong
- red flags:
  - Treats "rollback is documented" as equivalent to "rollback is tested"
  - No non-production simulation before the real cutover
- follow-ups:
  - The rollback test just showed it takes 40 minutes and your maintenance window is 20 — what do you do?
- source: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/design-principles.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "You can use automation to simulate different failures or to recreate scenarios that led to failures before."

### PP10 Observability From Scratch
- seat: principal-peer
- topic: observability
- type: scenario
- level: lead
- question: You've inherited a platform with dashboards everywhere and nobody trusts any of them. Design the observability stack from scratch — what do you actually instrument, and why?
- strong answer contains:
  - Anchors instrumentation on a small number of high-signal metrics tied to user-facing behavior — latency, traffic, errors, saturation — rather than instrumenting everything available
  - Distinguishes what pages a human (urgent, user-facing symptoms) from what's dashboard-only or ticket-only, so alert fatigue doesn't bury real pages
  - Plans for post-hoc analysis (logs, traces) separately from real-time alerting, rather than one system trying to do both jobs
  - Retires or consolidates the untrusted legacy dashboards rather than adding a new layer on top of them
- red flags:
  - Wants to instrument "everything" with no prioritization
  - Every metric pages a human — no distinction between page-worthy and dashboard-only signals
- follow-ups:
  - Traffic just went 10x — which of your signals moves first, and what's your actual response?
  - The budget for your observability vendor just got halved — what do you cut first, and what do you protect?
- source: https://sre.google/sre-book/monitoring-distributed-systems/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "The four golden signals of monitoring are latency, traffic, errors, and saturation."

### PP11 Depth Check: Alerting on Saturation
- seat: principal-peer
- topic: observability
- type: technical
- level: principal
- question: Walk me through exactly how you'd set an alert threshold for saturation on a service that has no hard resource limit, like a queue depth.
- strong answer contains:
  - Uses an indirect signal with a known upper bound, or a leading indicator like rising p99 latency, rather than the raw unbounded queue depth
  - Explains why a latency increase is an early warning of saturation, catchable before the system is fully saturated
  - Sets the threshold from an actual load test or observed capacity, not a round number picked by feel
  - Names what the alert should trigger — capacity add, load-shed, or a page — not just "alert fires"
- red flags:
  - Picks an arbitrary threshold with no load test or capacity baseline behind it
  - Can't explain why latency is a useful proxy for saturation
- follow-ups:
  - This alert is now firing constantly and everyone's ignoring it — what do you do?
- source: https://sre.google/sre-book/monitoring-distributed-systems/ (retrieved 2026-09-24)
- source-type: answer
- evidence: "Latency increases are often a leading indicator of saturation."

### PP12 Diagnosing a Cost Blow-Up
- seat: principal-peer
- topic: cost-blowups
- type: scenario
- level: both
- question: Cloud spend has tripled in a quarter with no corresponding growth in users. Walk me through how you find out why, and what you do about it.
- strong answer contains:
  - Starts by measuring actual usage and cost together rather than cutting resources blind
  - Attributes the spend to specific workloads or teams before deciding what to cut, so the fix targets the real driver
  - Distinguishes a one-time cut from an ongoing practice, and looks for what would cause the same blow-up next quarter
  - Separates "stop paying for what's unused" from "redesign for a lower baseline cost" as two fixes with different timelines
- red flags:
  - Proposes a blanket percentage cut across all services with no attribution to what's actually driving spend
  - Treats the fix as a one-time cleanup with no ongoing monitoring afterward
- follow-ups:
  - The single biggest driver turns out to be a team that loses a major feature if you cut their spend — what do you do?
  - Leadership now wants this to never happen again, not just fixed this once — what do you put in place?
- source: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/design-principles.html (retrieved 2026-09-24)
- source-type: answer
- evidence: "Measure the business output of the workload and the costs associated with delivery."

### PP13 The Expensive Standby Nobody Will Cut
- seat: principal-peer
- topic: cost-blowups
- type: strategic
- level: principal
- question: A platform team wants to keep an expensive redundant standby running "just in case", and finance wants it gone. How do you resolve that?
- strong answer contains:
  - Asks for the actual reliability target the standby is protecting, rather than accepting "just in case" as self-justifying
  - Weighs the standby's cost against a cheaper way to hit the same target — a colder standby, better automation, faster recovery — before defaulting to keeping it
  - Reframes the decision as a documented, owned trade-off rather than a stalemate between two teams
  - Puts a review cadence on the decision rather than settling it once and never revisiting it
- red flags:
  - Keeps or cuts the standby with no reliability target named
  - Treats it as a pure cost decision with no reliability consequence considered
- follow-ups:
  - Six months later there's an outage the standby would have prevented — how do you handle that conversation?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/redundancy (retrieved 2026-09-24)
- source-type: answer
- evidence: "More workload redundancy equates to more costs. Carefully consider adding redundancy and regularly review your architecture to ensure that you're managing costs"

### PP14 A Dependency You Don't Own Goes Down
- seat: principal-peer
- topic: reliability-failure-modes
- type: scenario
- level: both
- question: Walk me through how you'd design this platform's response to a dependency — a downstream API you don't own — going down for an hour.
- strong answer contains:
  - Distinguishes components on the critical path from ones that can run in a degraded state, and designs the degraded state on purpose
  - Names a concrete isolation mechanism — circuit breaker, timeout, bulkhead — so the downstream failure doesn't cascade into the rest of the system
  - Builds monitoring that detects the dependency failure and automates a response where possible, rather than relying on a human noticing first
  - Has actually tested this failure mode before it happened for real, not just designed it on paper
- red flags:
  - No distinction between critical and degradable components — one dependency failing takes everything down
  - Failure handling exists only in a design document, never tested
- follow-ups:
  - The dependency comes back but sends corrupted data for the first five minutes — does your design catch that too?
  - Now there's a compliance requirement to alert the regulator within 15 minutes of a customer-impacting failure — what changes operationally?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/principles (retrieved 2026-09-24)
- source-type: answer
- evidence: "Distinguish components that are on the critical path from those that can function in a degraded state."

### PP15 Depth Check: Running a Game Day
- seat: principal-peer
- topic: reliability-failure-modes
- type: technical
- level: principal
- question: Walk me through exactly how you'd run a game day to test this platform's failure handling, from planning it to the retro afterward.
- strong answer contains:
  - Tests specific, named scenarios and edge cases, not a vague "see what breaks"
  - Combines scheduled drills, so the team can learn the process, with unannounced ones, so the response is realistic — not only one kind
  - Runs the first attempts in non-production before ever running a drill against production
  - Feeds the results back into the design and the runbook — a drill that changes nothing afterward wasn't worth running
- red flags:
  - Runs the game day in production first, with no non-production rehearsal
  - No mechanism for turning drill findings into actual design or process changes
- follow-ups:
  - The drill just showed your own alerting missed the failure for 20 minutes — what does that change about the platform, not just the runbook?
- source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery (retrieved 2026-09-24)
- source-type: answer
- evidence: "Test multiple scenarios, including edge cases, and combine scheduled drills with surprise game days to see how systems and teams respond under pressure."

---

## Sources used

All fetched and read on 2026-09-24.

**Shaped the bank's scope** (what a Staff/Principal design round actually tests — see
`references/personas/principal-peer.md`):

1. System Design Primer (donnemartin): https://github.com/donnemartin/system-design-primer
2. staffeng.com — Staff-plus interview processes: https://staffeng.com/guides/staff-plus-interview-process/
3. staffeng.com — Interviewing for Staff-plus roles: https://staffeng.com/guides/interviewing-staff-plus-roles/

**Ground the rubrics** (what a strong answer contains):

4. AWS Well-Architected Framework — Reliability Pillar, design principles: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/design-principles.html
5. AWS Well-Architected Framework — Cost Optimization Pillar, design principles: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/design-principles.html
6. Google SRE Book — Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/
7. Google Cloud Architecture Framework — Reliability pillar: https://docs.cloud.google.com/architecture/framework/reliability
8. Microsoft Azure Well-Architected Framework — Reliability: design principles: https://learn.microsoft.com/en-us/azure/well-architected/reliability/principles
9. Microsoft Azure Well-Architected Framework — Reliability: redundancy: https://learn.microsoft.com/en-us/azure/well-architected/reliability/redundancy
10. Microsoft Azure Well-Architected Framework — Reliability: disaster recovery: https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery

Not sourced: PP07 (lift-and-shift vs re-architect ownership/decision-rights) is common engineering-management judgment, not tied to a single framework page — marked `source: none (common practice)` rather than stretching a citation to fit.
