A mid-sized SaaS company runs a customer-facing reporting feature. Today each report is
generated on demand: the web request fans out to four internal services, joins the results
in the API layer, and renders. p50 is 1.4s, p99 is 22s, and the p99 has been getting worse
for two quarters. Roughly 8% of report loads time out at the 30s gateway limit.

The proposal on the table is to precompute reports nightly into a denormalised store, serve
reads from that store, and fall back to the live path when a report is missing or stale.
The team estimates six weeks. Reports would be up to 24 hours out of date; the product
manager believes this is acceptable for most customers but has not asked any of them.

Should they do it?
