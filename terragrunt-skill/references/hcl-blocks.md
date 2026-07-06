# Terragrunt HCL Block Reference

> Source: curated data harvested from omattsson/terragrunt-mcp-server, restructured for grep-based lookup.
> Verified against: Terragrunt 1.x (spot-checked vs docs.terragrunt.com; current stable v1.1.0, 2026-07-01); flag and avoid any pre-1.0 idioms.

Lookup: `grep -n '^## BLOCK:' hcl-blocks.md`

## Contents
- autoinclude (terragrunt.stack.hcl, v1.1.0+)
- dependencies
- dependency
- download_dir
- generate
- iam_assume_role_duration
- iam_assume_role_session_name
- iam_role
- iam_web_identity_token
- include
- inputs
- locals
- prevent_destroy
- remote_state
- retry_max_attempts
- retry_sleep_interval_sec
- retryable_errors
- skip
- stack (terragrunt.stack.hcl)
- terraform
- terraform_binary
- terraform_version_constraint
- unit (terragrunt.stack.hcl)

## BLOCK: dependencies

**Dependencies Block**  |  Category: modules

Shorthand for declaring multiple dependencies when you only need ordering (not outputs). Use this when you want Terragrunt to apply modules in a specific order but don't need to reference their outputs.

**Syntax:**
```hcl
dependencies { ... }
```

**Attributes:**
- `paths` (list, required): List of paths to dependency modules.

*Simple dependency ordering*
```hcl
dependencies {
  paths = ["../vpc", "../security-groups"]
}
```

*Combined with dependency block*
```hcl
# Use dependencies for ordering only
dependencies {
  paths = ["../iam"]
}

# Use dependency when you need outputs
dependency "vpc" {
  config_path = "../vpc"
}

inputs = {
  vpc_id = dependency.vpc.outputs.vpc_id
}
```

Related: dependency

## BLOCK: dependency

**Dependency Block**  |  Category: modules

Declares a dependency on another Terragrunt module, allowing access to its outputs. Terragrunt ensures dependencies are applied in the correct order when using `run --all`.

**Syntax:**
```hcl
dependency "<label>" { ... }
```

**Attributes:**
- `config_path` (string, required): Relative or absolute path to the dependency's terragrunt.hcl directory.
- `enabled` (boolean): Whether this dependency is enabled. Useful for conditional dependencies.
- `skip_outputs` (boolean): Skip fetching outputs from this dependency (useful for destroy operations).
- `mock_outputs` (map): Mock output values to use when the dependency hasn't been applied yet.
- `mock_outputs_allowed_terraform_commands` (list): Terraform commands for which `mock_outputs` are allowed. If the command being run is NOT in this list and the dependency has no real outputs yet, Terragrunt errors instead of using mocks. A common set is `["init", "validate", "plan", "destroy"]` — include `destroy` so teardown still works once a dependency has already been removed.
- `mock_outputs_merge_strategy_with_state` (string): how mock values combine with real state outputs. One of:
  - `"no_merge"` (default) — if the dependency has any real outputs, mocks are ignored entirely; mocks are used only when there are no outputs at all.
  - `"shallow"` — real state wins per top-level key, and mocks backfill keys the applied state doesn't have yet (e.g. a new output added to the module since its last apply, so `plan` doesn't fail on a missing key).
  - `"deep_map_only"` — like shallow but recurses into nested maps; lists are NOT merged.
  Replaces the deprecated boolean `mock_outputs_merge_with_state`.

Only `dependency.<name>.outputs` is available — the old `dependency.<name>.inputs`
accessor has been removed. A `dependency` block both creates a DAG ordering edge **and**
exposes outputs; use `dependencies` (below) when you need ordering without outputs.

*Simple dependency on VPC module*
```hcl
dependency "vpc" {
  config_path = "../vpc"
}

inputs = {
  vpc_id = dependency.vpc.outputs.vpc_id
}
```

*Dependency with mock outputs for plan/validate*
```hcl
dependency "vpc" {
  config_path = "../vpc"
  
  mock_outputs = {
    vpc_id            = "vpc-mock12345"
    private_subnet_ids = ["subnet-mock1", "subnet-mock2"]
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan"]
}
```

*Mocks across more commands, backfilling newly-added outputs from state*
```hcl
dependency "vpc" {
  config_path = "../vpc"

  mock_outputs = {
    vpc_id             = "vpc-mock12345"
    private_subnet_ids = ["subnet-mock1", "subnet-mock2"]
  }
  # Allow mocks for these commands; if the running command isn't listed AND there
  # are no real outputs yet, Terragrunt errors instead of mocking. `destroy` is
  # included so teardown still works once the dependency is already gone.
  mock_outputs_allowed_terraform_commands = ["init", "validate", "plan", "destroy"]
  # "shallow": prefer real state per key, let mocks backfill any key the applied
  # state lacks (e.g. an output added to the module since the last apply).
  mock_outputs_merge_strategy_with_state = "shallow"
}
```

Related: dependencies, inputs

## BLOCK: download_dir

**Download Directory Attribute**  |  Category: terraform

Custom directory where Terragrunt downloads and caches Terraform modules. Defaults to a temporary directory.

**Syntax:**
```hcl
download_dir = "<path>"
```

**Attributes:**
- `download_dir` (string): Path to download directory.

*Use custom cache directory*
```hcl
download_dir = "${get_env("HOME")}/.terragrunt-cache"
```

Related: terraform

## BLOCK: generate

**Generate Block**  |  Category: generation

Generates a file in the Terraform working directory before Terraform runs. Commonly used to generate provider configurations, backend blocks, or shared variable files.

**Syntax:**
```hcl
generate "<label>" { ... }
```

**Attributes:**
- `path` (string, required): Path to the file to generate (relative to the Terraform working directory).
- `if_exists` (string): What to do if the file already exists — `overwrite`, `overwrite_terragrunt`, `skip`, or `error`.
- `if_disabled` (string): What to do with an existing generated file when `disable = true` — `remove`, `remove_terragrunt`, or `skip` (default `skip`).
- `contents` (string, required): The content to write to the file. Supports heredoc syntax.
- `comment_prefix` (string): Prefix for the auto-generated comment (default `#`). Empty string disables the comment.
- `disable_signature` (boolean, default `false`): Disable the "Generated by Terragrunt" signature in the file.
- `hcl_fmt` (boolean, default `true`): When `false`, skip HCL formatting of generated `.tf`/`.hcl`/`.tofu` files.
- `disable` (boolean): Disable this generate block.

*Generate AWS provider*
```hcl
generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
provider "aws" {
  region = "${local.region}"
  
  default_tags {
    tags = {
      Environment = "${local.environment}"
      ManagedBy   = "Terragrunt"
    }
  }
}
EOF
}
```

*Generate required providers*
```hcl
generate "versions" {
  path      = "versions.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
EOF
}
```

Related: terraform, remote_state

## BLOCK: iam_assume_role_duration

**IAM Assume Role Duration Attribute**  |  Category: iam

Duration in seconds for the assumed IAM role session. Defaults to 3600 (1 hour).

**Syntax:**
```hcl
iam_assume_role_duration = <number>
```

**Attributes:**
- `iam_assume_role_duration` (number): Session duration in seconds.

*Extend session duration*
```hcl
iam_assume_role_duration = 7200  # 2 hours
```

Related: iam_role, iam_assume_role_session_name

## BLOCK: iam_assume_role_session_name

**IAM Assume Role Session Name Attribute**  |  Category: iam

Session name for the assumed IAM role. Useful for CloudTrail auditing.

**Syntax:**
```hcl
iam_assume_role_session_name = "<session_name>"
```

**Attributes:**
- `iam_assume_role_session_name` (string): Session name for IAM role assumption.

*Set session name for auditing*
```hcl
iam_assume_role_session_name = "terragrunt-${local.environment}-deploy"
```

Related: iam_role, iam_assume_role_duration

## BLOCK: iam_role

**IAM Role Attribute**  |  Category: iam

AWS IAM role ARN that Terragrunt will assume before running Terraform. Useful for cross-account deployments.

**Syntax:**
```hcl
iam_role = "<role_arn>"
```

**Attributes:**
- `iam_role` (string): IAM role ARN to assume.

*Assume role for deployment*
```hcl
iam_role = "arn:aws:iam::${local.account_id}:role/TerraformDeployRole"
```

Related: iam_assume_role_duration, iam_assume_role_session_name

## BLOCK: iam_web_identity_token

**IAM Web Identity Token Attribute**  |  Category: iam

Path to a web identity token file for OIDC-based authentication. Used in CI/CD environments like GitHub Actions with AWS.

**Syntax:**
```hcl
iam_web_identity_token = "<path_to_token>"
```

**Attributes:**
- `iam_web_identity_token` (string): Path to OIDC web identity token file.

*Use OIDC token for AWS authentication*
```hcl
iam_web_identity_token = get_env("AWS_WEB_IDENTITY_TOKEN_FILE", "")
```

Related: iam_role

## BLOCK: include

**Include Block**  |  Category: modules

Includes configuration from another terragrunt.hcl file, enabling DRY (Don't Repeat Yourself) configuration patterns. Commonly used to include a root configuration with shared remote state and provider settings.

**Syntax:**
```hcl
include "<label>" { ... }
```

**Attributes:**
- `path` (string, required): Path to the terragrunt.hcl file to include. Use find_in_parent_folders("root.hcl") — bare find_in_parent_folders("root.hcl") targets a legacy root terragrunt.hcl; do not generate it.
- `expose` (boolean): When true, exposes the included config's locals and inputs for access via include.<label>.
- `merge_strategy` (string): How to merge the included configuration with the current one.

*Include root configuration*
```hcl
include "root" {
  path = find_in_parent_folders("root.hcl")
}
```

*Include with exposed locals*
```hcl
include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

locals {
  # Access exposed variables from included config
  account_id = include.root.locals.account_id
}
```

Related: locals, terraform, remote_state

## BLOCK: inputs

**Inputs Block**  |  Category: core

Specifies the input variables to pass to the Terraform module. These values are automatically converted to TF_VAR_* environment variables when Terraform is executed.

**Syntax:**
```hcl
inputs = { ... }
```

**Attributes:**
- `<variable_name>` (any): Key-value pairs matching the Terraform module's input variables.

*Basic inputs from locals*
```hcl
inputs = {
  instance_type = local.instance_type
  environment   = local.environment
  tags          = local.tags
}
```

*Merge inputs from dependency outputs*
```hcl
inputs = merge(
  local.common_vars,
  {
    vpc_id     = dependency.vpc.outputs.vpc_id
    subnet_ids = dependency.vpc.outputs.private_subnet_ids
  }
)
```

Related: locals, dependency

## BLOCK: locals

**Locals Block**  |  Category: core

Defines local variables that can be referenced elsewhere in the Terragrunt configuration. Locals are evaluated lazily and can reference other locals, inputs, and built-in functions.

**Syntax:**
```hcl
locals { ... }
```

**Attributes:**
- `<variable_name>` (any): Any valid HCL expression. Variables defined here can be referenced as local.<variable_name>.

*Define reusable local variables*
```hcl
locals {
  environment = "production"
  region      = "us-east-1"
  
  # Computed values
  name_prefix = "${local.environment}-app"
  
  # Load from files
  account_vars = read_terragrunt_config(find_in_parent_folders("account.hcl"))
  account_id   = local.account_vars.locals.account_id
}
```

*Complex local with conditionals*
```hcl
locals {
  is_prod = local.environment == "production"
  
  instance_type = local.is_prod ? "m5.xlarge" : "t3.micro"
  
  tags = {
    Environment = local.environment
    ManagedBy   = "Terragrunt"
  }
}
```

Related: inputs, include

## BLOCK: prevent_destroy

**Prevent Destroy Attribute**  |  Category: execution

When set to true, Terragrunt will prevent any destroy operations on this module. This is a safety mechanism to protect critical infrastructure.

**Syntax:**
```hcl
prevent_destroy = <boolean>
```

**Attributes:**
- `prevent_destroy` (boolean): Whether to prevent destroy operations.

*Protect production database*
```hcl
prevent_destroy = local.environment == "production"
```

*Always prevent destroy*
```hcl
# Critical infrastructure - never destroy
prevent_destroy = true
```

Related: skip

## BLOCK: remote_state

**Remote State Block**  |  Category: core

Configures the OpenTofu/Terraform remote state backend. For the backends Terragrunt
**natively manages — `s3` and `gcs` — it auto-provisions the state resources** (S3
bucket + optional lock table; GCS bucket) if they don't exist. For **all other backends,
including `azurerm`, `remote_state` behaves like `generate`**: it writes the backend
config but does **not** create any cloud resources — the storage account/container must
already exist. (Azure auto-management is gated behind the no-op `azure-backend`
experiment.) See references/azure-backend.md.

**Syntax:**
```hcl
remote_state { ... }
```

**Attributes:**
- `backend` (string, required): The backend type — one of the backends OpenTofu/Terraform supports (`s3`, `gcs`, `azurerm`, ...).
- `config` (map, required): An arbitrary map used to fill in the backend configuration in OpenTofu/Terraform. For `azurerm`, every key is a pure pass-through to the native backend (see references/azure-backend.md for the key list).
- `generate` (object): Generate a backend file. Keys: `path` and `if_exists` (`overwrite`, `overwrite_terragrunt`, `skip`, `error`).
- `disable_init` (boolean): When `true`, skip Terragrunt's automatic creation/management of remote state resources (S3 buckets, lock tables, GCS buckets) while still letting OpenTofu/Terraform initialize an already-provisioned backend. (No effect for `azurerm`, which is never auto-created.)
- `disable_dependency_optimization` (boolean): Disable the optimized dependency-output fetching for modules using this block.
- `encryption` (map): Configures OpenTofu state/plan encryption; transformed into an `encryption` block. Cloud-agnostic (OpenTofu only).

*S3 backend with DynamoDB locking*
```hcl
remote_state {
  backend = "s3"
  config = {
    bucket         = "my-terraform-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}
```

*GCS backend*
```hcl
remote_state {
  backend = "gcs"
  config = {
    bucket   = "my-terraform-state"
    prefix   = "${path_relative_to_include()}"
    project  = "my-gcp-project"
    location = "us"
  }
}
```

*Azure (azurerm) backend — Entra ID auth, pure pass-through (storage must pre-exist)*
```hcl
remote_state {
  backend = "azurerm"
  config = {
    storage_account_name = "myterragruntstate"
    container_name       = "tfstate"
    key                  = "${path_relative_to_include()}/terraform.tfstate"
    resource_group_name  = "terraform-rg"
    subscription_id      = "00000000-0000-0000-0000-000000000000"
    use_azuread_auth     = true # Microsoft-recommended; avoids storage shared keys
  }
}
```
The keys above are passed straight to the native `azurerm` backend; Terragrunt does not
create the storage account/container. For the full key list, auth methods, and gotchas
(shared-key-disabled storage, RBAC roles, provider v4 `subscription_id`), see
references/azure-backend.md.

Related: terraform, generate

## BLOCK: retry_max_attempts

**Retry Max Attempts Attribute**  |  Category: execution

Maximum number of retry attempts for retryable errors. Works in conjunction with retryable_errors.

**Syntax:**
```hcl
retry_max_attempts = <number>
```

**Attributes:**
- `retry_max_attempts` (number): Maximum number of retry attempts.

*Set maximum retry attempts*
```hcl
retry_max_attempts = 5
```

Related: retryable_errors, retry_sleep_interval_sec

## BLOCK: retry_sleep_interval_sec

**Retry Sleep Interval Attribute**  |  Category: execution

Number of seconds to wait between retry attempts. Works in conjunction with retryable_errors.

**Syntax:**
```hcl
retry_sleep_interval_sec = <number>
```

**Attributes:**
- `retry_sleep_interval_sec` (number): Seconds to wait between retries.

*Configure retry interval*
```hcl
retry_sleep_interval_sec = 30
```

Related: retryable_errors, retry_max_attempts

## BLOCK: retryable_errors

**Retryable Errors Attribute**  |  Category: execution

List of regex patterns for errors that should trigger automatic retry. Useful for handling transient errors like rate limiting or network issues.

**Syntax:**
```hcl
retryable_errors = [...]
```

**Attributes:**
- `retryable_errors` (list): Regex patterns for errors that should be retried.

*Retry AWS rate limiting errors*
```hcl
retryable_errors = [
  ".*RequestLimitExceeded.*",
  ".*Throttling.*",
  ".*rate exceeded.*"
]
```

Related: retry_max_attempts, retry_sleep_interval_sec

## BLOCK: skip

**Skip Attribute**  |  Category: execution

When set to true, Terragrunt will skip this module during run --all commands. Useful for temporarily disabling modules or for modules that should only run under certain conditions.

**Syntax:**
```hcl
skip = <boolean>
```

**Attributes:**
- `skip` (boolean): Whether to skip this module.

*Conditionally skip based on environment*
```hcl
skip = local.environment == "development"
```

*Skip deprecated module*
```hcl
# This module is deprecated, skip it
skip = true
```

Related: prevent_destroy

## BLOCK: terraform

**Terraform Block**  |  Category: core

Specifies the Terraform source code to use and allows configuration of how Terragrunt interacts with Terraform. This is the primary block for defining what Terraform module to deploy.

**Syntax:**
```hcl
terraform { ... }
```

**Attributes:**
- `source` (string, required): The source URL for the Terraform module. Supports local paths, Git URLs, S3, GCS, and Terraform Registry.
- `include_in_copy` (list): List of glob patterns for additional files to copy to the Terraform working directory.
- `extra_arguments` (block): Nested block to pass additional CLI arguments to specific Terraform commands.
- `before_hook` (block): Nested block to execute commands before Terraform runs.
- `after_hook` (block): Nested block to execute commands after Terraform runs.
- `error_hook` (block): Nested block to execute commands when Terraform encounters an error.

*Basic Terraform source from Git*
```hcl
terraform {
  source = "git::https://github.com/gruntwork-io/terragrunt.git//modules/vpc?ref=v0.1.0"
}
```

*Local module with extra arguments*
```hcl
terraform {
  source = "../modules/vpc"
  
  extra_arguments "common_vars" {
    commands = ["apply", "plan", "import", "push", "refresh"]
    arguments = ["-var-file=${get_terragrunt_dir()}/common.tfvars"]
  }
}
```

Related: remote_state, include, dependency

## BLOCK: terraform_binary

**Terraform Binary Attribute**  |  Category: terraform

Path to a custom Terraform binary. Useful when you need to use a specific version or a wrapper like Terraform Enterprise CLI.

**Syntax:**
```hcl
terraform_binary = "<path>"
```

**Attributes:**
- `terraform_binary` (string): Path to Terraform binary.

*Use specific Terraform version*
```hcl
terraform_binary = "/usr/local/bin/terraform-1.5.7"
```

*Use tfenv-managed version*
```hcl
terraform_binary = "~/.tfenv/bin/terraform"
```

Related: terraform_version_constraint

## BLOCK: terraform_version_constraint

**Terraform Version Constraint Attribute**  |  Category: terraform

Specifies the required Terraform version. Terragrunt will check this before running and fail if the version doesn't match.

**Syntax:**
```hcl
terraform_version_constraint = "<constraint>"
```

**Attributes:**
- `terraform_version_constraint` (string): Terraform version constraint (uses same syntax as Terraform).

*Require minimum version*
```hcl
terraform_version_constraint = ">= 1.0"
```

*Pin to specific minor version*
```hcl
terraform_version_constraint = "~> 1.5.0"
```

Related: terraform_binary

## BLOCK: unit

**Unit Block (terragrunt.stack.hcl)**  |  Category: stacks

Declares one unit to materialize when `terragrunt stack generate` expands a
`terragrunt.stack.hcl` file. Each `unit` becomes a directory under `.terragrunt-stack/`
containing a generated `terragrunt.hcl` (plus a `terragrunt.values.hcl` if `values` is
set). Lives **only** in `terragrunt.stack.hcl`, not in a unit's own `terragrunt.hcl`.

**Syntax:**
```hcl
unit "<name>" { ... }
```

**Attributes:**
- `<name>` (label, required): unique identifier for the unit within the stack; also its referenceable name. Each unit must have a unique name **and** `path`.
- `source` (string, required): where to fetch the unit's config from — same syntax as the `terraform` block `source`: local path, `git::…?ref=…`, `tfr://` registry, or an OCI image reference. Overridable with `--source-map`.
- `path` (string, required): relative path where the unit is deployed inside `.terragrunt-stack/`.
- `values` (map, optional): values passed to the unit; written to a generated `terragrunt.values.hcl` next to the unit's `terragrunt.hcl` and read inside it as `values.<key>`.
- `no_dot_terragrunt_stack` (boolean, optional): generate the unit in the same directory as `terragrunt.stack.hcl` instead of under `.terragrunt-stack/`. Intended for soft adoption / state migration (keeps `path_relative_to_include()` stable), not the recommended end state.
- `no_validation` (boolean, optional): skip Terragrunt's validation of this unit's configuration.
- **v1.1.0+ only** (GA in v1.1.0, 2026-07-01 — do NOT emit for repos pinned to ≤1.0.x): `autoinclude` (block; generates a `terragrunt.autoinclude.hcl` merged into the unit, e.g. to declare a `dependency` using `unit.<name>.path` — see `## BLOCK: autoinclude`), `update_source_with_cas` (boolean, default `false`; on `stack generate`, rewrites a **relative, literal** `source` within the same repo to a `cas::sha1:…` reference so the generated tree is self-contained — set by catalog authors, not consumers; errors if `--no-cas` is set), `mutable` (boolean, default `false`; `false` hard-links CAS content read-only, `true` copies it so the working tree is editable). These graduated from the `stack-dependencies` / `cas` experiments. `dependency` targeting a stack directory is supported **via an `autoinclude` block** (units may depend on stacks; stacks cannot depend on stacks or units). `include` blocks in stack files: the v1.1.0 changelog says they now work, but the Stacks "Limitations" doc still lists them unsupported — docs lag, verify against the pinned version first.

*Unit pulling a catalog module, with values*
```hcl
unit "rds" {
  source = "${local.infra_root}/catalog/units/rds"
  path   = "rds"
  values = {
    instance_class = "db.t3.medium"
    environment    = "prod"
  }
}
```
Inside `catalog/units/rds/terragrunt.hcl` those are read as `values.instance_class`, `values.environment`.

Related: stack, terraform

## BLOCK: stack

**Stack Block (terragrunt.stack.hcl)**  |  Category: stacks

Declares a **nested stack** inside a `terragrunt.stack.hcl`. Identical attributes and
semantics to `unit`, except the `source` must point at a directory containing its own
`terragrunt.stack.hcl`; generation produces a nested `terragrunt.stack.hcl` under the given
`path` (which is then itself expanded). Use it to compose stacks of stacks.

**Syntax:**
```hcl
stack "<name>" { ... }
```

**Attributes:** same as `unit` — `<name>` (label, required), `source` (required), `path`
(required), `values`, `no_dot_terragrunt_stack`, `no_validation`, and the same v1.1.0+
additions (`autoinclude` with `stack.<name>.path` refs, `update_source_with_cas`, `mutable`).

*Nested stack instantiated per region*
```hcl
stack "networking" {
  source = "${local.infra_root}/catalog/stacks/networking"
  path   = "networking"
  values = { region = "eastus" }
}
```

Related: unit, terraform

## BLOCK: autoinclude

**Autoinclude Block (terragrunt.stack.hcl)**  |  Category: stacks  |  **v1.1.0+ only**

Nested inside a `unit` or `stack` block. On `terragrunt stack generate`, its body is
written to a `terragrunt.autoinclude.hcl` file next to the generated `terragrunt.hcl` (or
`terragrunt.stack.hcl`) and **merged into that unit/stack when it is parsed** — the catalog
source itself is never modified. This is how a stack wires its own units together and patches
catalog components with config they don't ship. GA in v1.1.0 (was the `stack-dependencies`
experiment). Requires **v1.1.0+** — do NOT emit for repos pinned to ≤1.0.x.

**Syntax:**
```hcl
unit "app" {
  source = "../catalog/units/app"
  path   = "app"

  autoinclude {
    dependency "vpc" {
      config_path  = unit.vpc.path      # resolves to the generated dir of the "vpc" unit
      mock_outputs = { vpc_id = "vpc-mock" }
    }

    inputs = {
      vpc_id = dependency.vpc.outputs.vpc_id
    }
  }
}
```

- **Body:** anything valid in a unit configuration — `dependency`, `inputs`, `errors`
  (e.g. `retry`), etc. It is merged, so it adds to / overrides the catalog unit's config.
- **`unit.<name>.path` / `stack.<name>.path`:** resolve to the generated path of a sibling
  block, so dependency wiring never hardcodes `.terragrunt-stack/…` paths.
- **Dependency on a stack:** a `dependency` declared in an `autoinclude` block *may* set
  `config_path` to a stack directory and read its aggregated outputs — this is the supported
  way to depend on a stack. A plain top-level `dependency` block cannot target a stack dir.
  Relationship is one-way: units depend on stacks; stacks cannot depend on stacks or units.
- The generated `terragrunt.autoinclude.hcl` is stack output — gitignore `.terragrunt-stack/`.

Docs: https://docs.terragrunt.com/features/stacks/explicit/ (Declaring Dependencies Between
Units) · https://docs.terragrunt.com/reference/hcl/blocks#autoinclude

Related: unit, stack, dependency, include
