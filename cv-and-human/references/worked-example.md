# Worked example (reference)

A self-contained before/after using **fake data** (candidate "Jordan Reyes",
applying for a Senior Platform Engineer role). It shows the three things this skill
does that generic resume tools don't: surface *real* metrics, refuse to invent
*missing* ones (placeholders), and de-slop without stripping referential keywords.
Use it as the pattern to imitate; do not copy its content.

## The raw input (what the candidate gave us)

> Summary: "Results-driven, passionate software engineer with a proven track record
> of leveraging cutting-edge technologies to deliver transformative, scalable
> solutions and drive impactful business outcomes."
>
> - "Was responsible for spearheading the migration of our CI/CD pipeline, a pivotal
>   initiative that dramatically improved build times and drove significant
>   efficiency gains, ensuring scalability and reliability across the org."
>   *(candidate mentioned in passing: builds went from ~40 min to ~6 min)*
> - "Helped with Kubernetes stuff and worked on observability, leveraging various
>   tools to optimize performance." *(no figure given)*
> - "Played an instrumental role in reducing cloud costs." *(never measured)*

## The tailored, de-slopped output

> **Summary** — Platform engineer with 6 years building CI/CD, Kubernetes, and
> observability tooling in Go. Cut a 40-minute build pipeline to 6 minutes and runs
> production on-call for a 30-service estate.
>
> - Migrated the CI/CD pipeline to GitHub Actions, cutting build time from 40 minutes to 6.
> - Built Kubernetes deployment automation and Prometheus/Grafana observability for [ADD: # services / clusters].
> - Reduced monthly cloud spend by [ADD REAL %/FIGURE] through rightsizing and autoscaling.

## Why each change was made

**The summary.** Every word of the original is empty booster — "results-driven,
passionate, proven track record, leveraging, transformative, drive impactful
outcomes" are all on the cut-list, and none point at anything real. The rewrite
leads with a concrete specific (the 40→6 build win), states the role and stack
plainly, and carries no boosters. This is the one line where `hook-and-human`'s
"lead with a real specific" applies.

**Bullet 1 — surface the real number.** The fact was *in* the input, buried under
"dramatically improved … drove significant efficiency gains, ensuring scalability
and reliability." We cut the inflation and the `-ing` tail and stated the measured
result: 40 minutes to 6. Nothing invented — the number was the candidate's.

**Bullet 2 — placeholder, not invention.** No scale figure was given, so we did
**not** write "for 50+ services." We left `[ADD: # services / clusters]` for the
candidate to fill. Note the keyword guard: "Kubernetes", "Prometheus", "Grafana"
stayed (referential — real tools, likely JD keywords), while "leveraging various
tools to optimize performance" was cut (empty).

**Bullet 3 — the hardest case, handled honestly.** "Played an instrumental role in
reducing cloud costs" is exactly where a generic tool invents a number (e.g. "by
30%"). It was never measured, so the metric is a placeholder, not a guess. If the
candidate can't recover a real figure, the bullet ships without one rather than
with a fabricated one.

## A filled gap-report fragment

```
## Coverage against job description
| JD requirement / keyword | Status            | Action taken |
|--------------------------|-------------------|--------------|
| CI/CD                    | Present & strong  | Surfaced the 40→6 build result |
| Kubernetes               | Present but buried| Pulled out of "Kubernetes stuff" into a concrete bullet |
| Observability            | Present but weak  | Named the real stack (Prometheus/Grafana) |
| Go                       | Present & strong  | Kept in summary and skills |
| SLOs / on-call           | Present but weak  | Surfaced "30-service on-call" from the candidate's notes |

## Real gaps (candidate decision needed)
- Cloud-cost reduction figure — never measured; recover a real number or drop the metric.
- Service/cluster count for the K8s bullet — fill the placeholder.
```

## A red-team triage fragment (Truth lens)

```
### Truth Red Team
> Verdict: revise
> Top concern: two metrics rest on placeholders, not measured values.
> Blocker before sending? no

- "40 minutes to 6" is defensible (candidate-stated) — keep.
- Cloud-cost bullet: do not fill with an estimate. If asked "by how much?" in an
  interview and there's no real figure, the claim collapses. Placeholder stays until
  the candidate supplies a measured number.
```
