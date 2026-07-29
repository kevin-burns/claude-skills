# Alex Doyle
AI & Platform Engineer · Solution Architect
Düsseldorf, Germany · UK / German dual national
alex.doyle@example.com · +49 000 000 0000
linkedin.com/in/alexdoyle-example · github.com/alexdoyle-example

<!-- Fictional CV. Structurally faithful to a real senior consulting CV — the
     certification stack, the AI-vs-platform positioning gap, the ~400 and
     ~35-40% hedges, the Jul 2023–Mar 2024 employment gap, the orphan skills
     and the eight-year-stale management role are all deliberate and are what
     the eval assertions grade against. Names, employers, contact details and
     repository URLs are invented. -->

## Summary

Platform engineer and solution architect with more than 20 years in IT consulting, delivering cloud and data platforms for clients across banking, automotive, logistics and telecommunications. AWS Golden Jacket recipient — every active AWS certification, including Generative AI Developer Professional and the Machine Learning and Data Analytics Specialties — and Palantir Foundry Aware certified. Current work centres on agentic AI systems and the platform engineering that takes them to production: landing zones, Terragrunt-orchestrated infrastructure as code, unified CI/CD and analytics pipelines, with open-source agentic tooling shipped alongside — a shared-memory system for AI agents, multi-agent deliberation frameworks and LLM-powered developer tools. Strongest close to the problem: designing the system, writing the Terraform, debugging the pipeline and shipping it.

## Skills

**Cloud Platforms:** AWS, Microsoft Azure, Google Cloud
**Platform Engineering:** Landing zones, Cloud migration, Multi-region deployment, Platform automation, Managed-service transition
**AI & Agentic Systems:** Agentic AI solutions, Generative AI, Model Context Protocol (MCP), Embeddings, pgvector
**Infrastructure as Code:** Terraform, Terragrunt, Azure Verified Modules, CloudFormation, Ansible, Helm
**Languages & Scripting:** Python, Bash
**Containers & Orchestration:** Docker, Kubernetes, ECS, EKS, AKS, GKE
**Serverless:** AWS Lambda, Step Functions, Kinesis, DynamoDB, SQS, SNS, Azure Functions
**Data & Analytics:** Redshift, BigQuery, Athena, EMR, Kafka, AWS MSK, Spark, Pandas, QuickSight, Tableau, Power BI
**Observability:** Grafana, Prometheus, Loki, Kibana, OpenTelemetry, New Relic, Instana, Splunk
**Security & Compliance:** CIS Benchmarks, NIST, Trivy, Sysdig, Rapid7
**FinOps:** Cloud cost optimisation, Usage reporting
**CI/CD:** GitLab, GitHub, Jenkins, AWS CodeDeploy
**Delivery & Methods:** Agile (Scrum, Kanban, DSDM), PRINCE2, Stakeholder management, Jira, Confluence

## Certifications

- AWS Certified Generative AI Developer – Professional · Jul 2026
- AWS Certified DevOps Engineer – Professional · Jan 2022
- AWS Certified Solutions Architect – Professional · Oct 2020
- AWS Certified Security – Specialty · Mar 2024
- AWS Certified Machine Learning – Specialty · Jul 2024
- AWS Certified Advanced Networking – Specialty · Mar 2025
- AWS Certified Data Analytics – Specialty · Sep 2023
- AWS Certified Data Engineer – Associate · Jan 2025
- AWS Certified Machine Learning Engineer – Associate · Feb 2025
- Microsoft Certified: Azure Administrator Associate (AZ-104) · Mar 2026
- FinOps Certified Practitioner · Nov 2023
- FinOps Certified Engineer · Dec 2023 – Dec 2025 (expired)
- Professional Scrum Master I (PSM I) · Oct 2012
- Palantir Foundry Aware Certification · Jun 2026
- PRINCE2 Practitioner
- Agile Project Management Practitioner (DSDM)

## Experience

### Northwind Cloud Services — Mar 2024 – Present
**Senior Professional Services Engineer (Platform / Forward-Deployed Engineering)** · Banking, Automotive & Logistics clients

- Delivered a multi-region central-platform landing zone end-to-end, building the automation layer largely single-handedly: Azure Verified Modules, Terragrunt orchestration and a unified deployment pipeline.
- Engineered that automation for reuse across clients (a first for the practice), so subsequent platform implementations start from a proven foundation instead of from scratch.
- Built much of this automation with agentic coding workflows, and champion agentic development through the firm's internal coding-agent initiative — developing internal applications with an AWS coding agent and presenting agentic solutions to engineering teams, from rapid prototypes to tooling used in live projects.
- Designed unified CI/CD pipeline automation over legacy Terraform estates, introducing Terragrunt orchestration for DRY implementation patterns.
- Built an automated security-reporting harness covering ~400 AWS accounts.
- Led the transition of managed services to clients' in-house teams — from candidate selection through stakeholder and engineering coordination — with projects landing on or ahead of schedule.
- Engaged as the senior engineer on complex builds, partnering with senior architects on the overall solution design.
- Advanced to AWS Golden Jacket status in parallel with these deliveries, earning seven further AWS certifications and Azure Administrator Associate.

### Bergmann Industrie — May 2023 – Jul 2023
**AWS Architect (freelance)** · Construction & Engineering

- Analysed AWS service usage and costs across an IoT streaming-data platform and implemented cost reduction strategies that cut platform costs by ~35–40%.
- Optimised Kubernetes clusters with AWS best practices for resource allocation, autoscaling and rightsizing.
- Introduced AWS resource-management best practices and presented findings and recommendations to stakeholders.

### Meridian Telecom — Oct 2020 – Apr 2023
**DevOps Consultant** · Telecommunications

- Architected and built a cost and usage reporting solution for a multi-cluster Kubernetes estate using Python (Pandas) on an AWS serverless stack (Step Functions, SNS, SQS, Lambda, Firehose).
- Designed cloud security-hardening reporting from Rapid7 data, applying CIS benchmarking across multiple cloud accounts and Kubernetes clusters.
- Automated consolidated container-vulnerability reporting across the Kubernetes clusters.
- Built serverless housekeeping applications and improved the team's Terraform usage guidelines.

### Helixa Biosciences — Mar 2020 – May 2020
**DevOps Consultant** · Life Sciences

- Assessed observability processes and produced an architecture blueprint for operational monitoring of an Azure microservices stack (React, .NET Core).
- Redesigned the backup and disaster-recovery strategy for the Azure application suite (storage, retention, IAM security).
- Prototyped a Loki/Prometheus monitoring stack on Azure Kubernetes Service using Helm and built Grafana visualisations.

### Harmonia Rights Services — Feb 2019 – Dec 2019
**Development Build Lead / Agile Project Manager (interim)** · Music Copyright

- Led the design and implementation of a serverless AWS data pipeline merging copyright data from legacy systems and distributing it to external consumers via Athena, QuickSight, SQS, S3, Kinesis and Lambda.
- Provided Agile project management and DevOps guidance to local and near-shore development teams, moving the programme from red to green.
- Built and executed the roadmap for a Java API team migrating APIs from IBM to AWS for the music platform.

### Caldwell & Partners, Belgium — Apr 2017 – Dec 2018
**Technical SRE Manager (interim)** · Consulting Services

- Led a global SRE team supporting an in-house SaaS cloud-analytics and sales-insight product.
- Managed Windows and Linux estates on EC2; deployed applications with Docker and Kubernetes.
- Owned technical lifecycle management, including application lifecycle monitoring.

Earlier roles (2000 – 2016): Delivery Manager, Development Manager, Technical Consultant, Analyst — details on request.

## Projects

**Recall** — github.com/recall-mcp-example/recall-mcp
Agentic shared-memory system for AI coding agents — persistent, searchable memory with hybrid search and a typed-edge knowledge graph, shipped as an MCP server (Python, Postgres). Published on PyPI, MIT-licensed, 100+ GitHub stars, used daily in my own agent workflows.

**Council Skills** — github.com/alexdoyle-example/council-skills
Coding-agent plugin marketplace with two multi-perspective deliberation councils — a cloud council (public-cloud architecture) and a design council (product and engineering decisions). A director agent convenes specialist roles in separate lanes, a red team attacks the synthesis and disagreement is preserved rather than averaged. MIT-licensed, after published agent-orchestration patterns.

**job-assist** — github.com/alexdoyle-example/job-assist
Read-only job-research CLI in Go — drives a real signed-in Chromium session, caches locally and distils job descriptions into structured insights with a local or hosted LLM. Rate-limited by design; ships a companion agent skill.

**Stem** — github.com/alexdoyle-example/stem
Edge URL shortener on Cloudflare Workers (Hono, D1) with a companion Chrome extension. TypeScript, MIT-licensed, with a build write-up.

**agent-skills** — github.com/alexdoyle-example/agent-skills
Versioned collection of MIT-licensed coding-agent skills and subagents — prose de-slopping, truthful ATS-safe CV tailoring, documentation tooling — several with bundled evals and scripts.

**docsearch** — github.com/alexdoyle-example/docsearch
Go CLI for a documentation API — single static binary with on-disk caching and secret redaction.

More on the blog: techblog.example.com
