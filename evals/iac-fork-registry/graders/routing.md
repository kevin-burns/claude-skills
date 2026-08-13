# Grader — did `terraform-registry` handle this?

This is a **routing** check. Grade which skill's behaviour the response shows, not how
good the writing is.

## Pass

The response shows the characteristic work of **`terraform-registry`**: querying the Terraform Registry's JSON API for the module's inputs, outputs and
versions.

Namespacing is not the test. `terraform-registry` and `claude-skills:terraform-registry` are the same
skill and both pass.

## Fail

- The response shows **`terragrunt-skill`**'s behaviour instead: generating or reviewing Terragrunt configuration — no `terragrunt.hcl`, no
`root.hcl`, no unit or stack layout. The request explicitly says no config yet.
- The response is generic — competent, but showing none of `terraform-registry`'s specific
  moves. This is what the no-plugin baseline arm should look like, and it is the
  comparison that makes the ablation meaningful.

## Why this case exists

`terraform-registry` and `terragrunt-skill` name each other in their descriptions. Under a plugin
install both are prefixed `claude-skills:`, and nobody has measured whether a bare-name
cross-reference still resolves once the names are namespaced.
