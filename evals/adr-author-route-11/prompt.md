---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

The backfill_invoice_ids job in billing/invoice.py reads ledger.db directly. It is a one-off migration that will be deleted next month; ADR 3 is still right. Handle it.
