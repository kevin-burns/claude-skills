# Terragrunt CLI Reference (1.0.x)

> Scope: Terragrunt 1.0.x ONLY. Never generate pre-1.0 command forms (run-all, hclfmt, plan-all,
> graph-dependencies, terragrunt- prefixed flags, etc.). Canonical docs: https://docs.terragrunt.com/reference/cli/
> Verified against the Terragrunt 1.0 CLI command tree (docs.terragrunt.com, June 2026).

Lookup: `grep -n '^## COMMAND:' cli-reference.md` | `grep -A 20 '^## COMMAND: stack run'`

## 1.0 command tree
`run` `exec` | `backend bootstrap|migrate|delete` | `stack generate|run|output|clean` | `catalog` `scaffold` | `find` `list` | `hcl fmt|validate` | `dag graph` | `render` | `info print|strict` | OpenTofu shortcuts (`plan`, `apply`, `destroy`, `output`, `init`, ...)

## FILTERS (--filter) — unit/stack targeting
The `--filter` flag is the single 1.0 mechanism for targeting units and stacks, replacing all pre-1.0 queue flags (`--queue-include-dir`, `--queue-exclude-dir`, etc., which remain only as aliases that translate into filter expressions).
Expression types: **name** (`name=web`), **path** (`./prod/**`), **attribute** (`reading=config/vars.tfvars`, `type=unit`), **graph** (dependency traversal), **git** (changed units). Combine expressions with a pipe: `--filter './prod/** | name=web'`. Reusable filter sets go in a filters file.
```bash
terragrunt find --filter './prod/** | name=web'
terragrunt run --all apply --filter 'name=vpc'
```
Docs: https://docs.terragrunt.com/features/filter/ (sub-pages: name, path, attributes, graph, git, combining, filters-file). For full expression syntax, fetch those pages or use C7 search.

## COMMAND: backend bootstrap

**Category:** backend

Create and configure the remote state backend (S3 bucket, DynamoDB table, etc.).

**Usage:** `terragrunt backend bootstrap [flags]`

Automatically creates the backend resources needed for remote state storage. 
For AWS, this includes the S3 bucket and DynamoDB table for state locking.
For GCP, this creates the GCS bucket. For Azure, it creates the storage account and container.

**Options:**
- `--terragrunt-config`: Path to the Terragrunt configuration file

*Bootstrap the backend defined in terragrunt.hcl*
```bash
terragrunt backend bootstrap
```

Docs: https://docs.terragrunt.com/reference/cli/commands/backend/bootstrap/

## COMMAND: backend delete

**Category:** backend

Delete the remote state backend resources.

**Usage:** `terragrunt backend delete [flags]`

Removes the backend resources created by Terragrunt. Use with caution as this 
will delete the state storage. Make sure to back up any important state files first.

**Options:**
- `--force`: Skip confirmation prompt

*Delete backend resources with confirmation*
```bash
terragrunt backend delete
```

*Force delete without confirmation*
```bash
terragrunt backend delete --force
```

Docs: https://docs.terragrunt.com/reference/cli/commands/backend/delete/

## COMMAND: backend migrate

**Category:** backend

Migrate state from one backend to another.

**Usage:** `terragrunt backend migrate [flags]`

Migrates Terraform state from the current backend to a new backend configuration.
This is useful when moving state between different storage backends or reconfiguring
backend settings.

**Options:**
- `--from`: Source backend configuration
- `--to`: Destination backend configuration

*Migrate state to new backend*
```bash
terragrunt backend migrate
```

Docs: https://docs.terragrunt.com/reference/cli/commands/backend/migrate/

## COMMAND: catalog

**Category:** catalog

Browse and interact with a catalog of Terraform modules.

**Usage:** `terragrunt catalog [flags]`

Opens an interactive browser for exploring Terraform module catalogs.
You can browse available modules, view their documentation, and scaffold
new projects using modules from the catalog.

**Options:**
- `--url`: URL of the catalog to browse

*Browse the default catalog*
```bash
terragrunt catalog
```

*Browse a custom catalog*
```bash
terragrunt catalog --url=https://example.com/catalog
```

Docs: https://docs.terragrunt.com/reference/cli/commands/catalog/

## COMMAND: scaffold

**Category:** catalog

Generate a new Terragrunt configuration from a module in the catalog.

**Usage:** `terragrunt scaffold [flags] [module-url]`

Creates a new Terragrunt configuration file by scaffolding from a module
in the catalog. This generates the necessary terragrunt.hcl with all inputs
and configuration pre-filled based on the module's interface.

**Options:**
- `--output`: Output directory for the scaffolded configuration
- `--var`: Set input variables for the scaffold

*Scaffold a VPC module*
```bash
terragrunt scaffold github.com/gruntwork-io/terraform-aws-vpc//modules/vpc
```

*Scaffold with variables*
```bash
terragrunt scaffold --var=env=prod github.com/example/module
```

Docs: https://docs.terragrunt.com/reference/cli/commands/scaffold/

## COMMAND: dag graph

**Category:** configuration

Generate a visual dependency graph of Terragrunt modules.

**Usage:** `terragrunt dag graph [flags]`

Generates a DOT format graph showing the dependencies between Terragrunt
modules. The output can be rendered using Graphviz or other DOT viewers.
Useful for understanding and documenting infrastructure dependencies.

**Options:**
- `--format`: Output format (dot, json, mermaid)
- `--output`: Output file path

Docs: https://docs.terragrunt.com/reference/cli/commands/dag/graph/

## COMMAND: hcl fmt

**Category:** configuration

Format Terragrunt HCL configuration files.

**Usage:** `terragrunt hcl fmt [flags] [path]`

Formats Terragrunt configuration files (terragrunt.hcl) to a canonical format.
Similar to terraform fmt but for Terragrunt-specific HCL syntax. Can be run
recursively to format all files in a directory tree.

**Options:**
- `--check`: Check if files are formatted (exit 1 if not)
- `--diff`: Show diff of formatting changes
- `--recursive`: Recursively format files in subdirectories
- `--write`: Write formatted output to files

*Format all Terragrunt files*
```bash
terragrunt hcl fmt
```

*Check formatting without changing files*
```bash
terragrunt hcl fmt --check
```

*Show what would change*
```bash
terragrunt hcl fmt --check --diff
```

Docs: https://docs.terragrunt.com/reference/cli/commands/hcl/fmt/

## COMMAND: hcl validate

**Category:** configuration

Validate the syntax of Terragrunt HCL configuration files.

**Usage:** `terragrunt hcl validate [flags] [path]`

Validates that Terragrunt configuration files have correct HCL syntax.
This checks for parsing errors, unknown blocks, and invalid attribute references.
Does not validate Terraform configurations.

**Options:**
- `--json`: Output validation results in JSON format
- `--strict`: Enable strict validation (treat warnings as errors)

*Validate all Terragrunt files*
```bash
terragrunt hcl validate
```

*Validate with strict mode*
```bash
terragrunt hcl validate --strict
```

*Output validation results as JSON*
```bash
terragrunt hcl validate --json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/hcl/validate/

## COMMAND: info print

**Category:** configuration

Print information about the Terragrunt configuration and environment.

**Usage:** `terragrunt info print [flags]`

Displays detailed information about the current Terragrunt configuration,
including paths, versions, environment variables, and resolved configuration values.

**Options:**
- `--json`: Output in JSON format

*Print configuration info*
```bash
terragrunt info print
```

*Print info as JSON*
```bash
terragrunt info print --json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/info/print/

## COMMAND: render

**Category:** configuration

Render the final Terragrunt configuration after all processing.

**Usage:** `terragrunt render [flags]`

Outputs the final, merged Terragrunt configuration after processing all
includes, dependencies, and function calls. This is useful for debugging
configuration issues and understanding the effective configuration.

**Options:**
- `--json`: Output as JSON (default is HCL)
- `--with-metadata`: Include metadata about where values came from

*Render configuration as HCL*
```bash
terragrunt render
```

*Render configuration as JSON*
```bash
terragrunt render --json
```

*Render with source metadata*
```bash
terragrunt render --with-metadata
```

Docs: https://docs.terragrunt.com/reference/cli/commands/render/

## COMMAND: find

**Category:** discovery

Find Terragrunt modules in a directory tree.

**Usage:** `terragrunt find [flags] [path]`

Searches for all Terragrunt configuration files (terragrunt.hcl) in the 
specified directory tree. This is useful for discovering all modules in
a large infrastructure repository.

**Options:**
- `--json`: Output results in JSON format
- `--hidden`: Include hidden directories

*Find all modules in current directory*
```bash
terragrunt find
```

*Find modules in a specific path*
```bash
terragrunt find ./infrastructure
```

*Output as JSON*
```bash
terragrunt find --json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/find/

## COMMAND: list

**Category:** discovery

List all Terragrunt modules with their status and dependencies.

**Usage:** `terragrunt list [flags]`

Lists all Terragrunt modules in the current stack with information about
their status, dependencies, and configuration. More detailed than 'find'.

**Options:**
- `--json`: Output in JSON format
- `--tree`: Show as dependency tree

*List all modules*
```bash
terragrunt list
```

*Show dependency tree*
```bash
terragrunt list --tree
```

Docs: https://docs.terragrunt.com/reference/cli/commands/list/

## COMMAND: exec

**Category:** main

Execute an arbitrary shell command with Terragrunt environment variables.

**Usage:** `terragrunt exec [flags] -- [command]`

The exec command runs an arbitrary shell command while setting up the Terragrunt 
environment variables and context. This is useful for running custom scripts that need access 
to Terragrunt's resolved configuration values.

**Options:**
- `--terragrunt-config`: Path to the Terragrunt configuration file
- `--terragrunt-working-dir`: Directory to run the command in

*Run a custom script with Terragrunt context*
```bash
terragrunt exec -- ./scripts/deploy.sh
```

*Echo resolved configuration values*
```bash
terragrunt exec -- echo $TF_VAR_environment
```

Docs: https://docs.terragrunt.com/reference/cli/commands/exec/

## COMMAND: run

**Category:** main

Run one or more Terraform/OpenTofu commands against a single unit or a stack of units.

**Usage:** `terragrunt run [flags] -- [terraform command]`

The run command is the primary way to execute Terraform/OpenTofu commands through Terragrunt. 
It can operate on a single module (unit) or across multiple modules (stack) using the --all flag.

When running against a stack, Terragrunt automatically determines the correct execution order based on 
dependencies defined in terragrunt.hcl files.

**Options:**
- `--all`: Run the command against all modules in the stack (directory tree)
- `--graph`: Generate a visual dependency graph instead of running the command
- `--filter`: Filter which modules to include (comma-separated list of module names or paths)
- `--exclude`: Exclude specific modules (comma-separated list)
- `--parallelism`: Maximum number of modules to process in parallel
- `--ignore-dependency-errors`: Continue processing even if a dependency fails
- `--ignore-external-dependencies`: Ignore external dependencies (modules outside current tree)
- `--include-external-dependencies`: Include external dependencies when running
- `--terragrunt-config`: Path to the Terragrunt configuration file
- `--terragrunt-working-dir`: Directory to run Terragrunt in
- `--terragrunt-source`: Override the source URL for the module
- `--terragrunt-source-update`: Delete the cached source and re-download
- `--terragrunt-no-auto-init`: Disable automatic terraform init
- `--terragrunt-no-auto-retry`: Disable automatic retry on retryable errors
- `--terragrunt-non-interactive`: Run in non-interactive mode (no prompts)
- `--terragrunt-log-level`: Set the log level (trace, debug, info, warn, error)

*Run terraform plan on current module*
```bash
terragrunt run -- plan
```

*Run terraform apply on all modules in dependency order*
```bash
terragrunt run --all -- apply
```

*Run terraform apply with auto-approve on all modules*
```bash
terragrunt run --all -- apply -auto-approve
```

Docs: https://docs.terragrunt.com/reference/cli/commands/run/

## COMMAND: apply

**Category:** shortcut

Shortcut for running terraform apply through Terragrunt.

**Usage:** `terragrunt apply [flags] [plan-file]`

A convenience shortcut equivalent to 'terragrunt run -- apply'.
Applies Terraform changes with all Terragrunt configuration applied.
Can apply a saved plan file or run interactively.

**Options:**
- `--all`: Apply on all modules in the stack
- `-auto-approve`: Skip interactive approval
- `-target`: Target specific resources
- `-var`: Set a variable
- `-parallelism`: Limit concurrent operations

*Apply changes interactively*
```bash
terragrunt apply
```

*Apply without confirmation*
```bash
terragrunt apply -auto-approve
```

*Apply all modules*
```bash
terragrunt apply --all -auto-approve
```

Docs: https://docs.terragrunt.com/reference/cli/commands/opentofu-shortcuts/

## COMMAND: destroy

**Category:** shortcut

Shortcut for running terraform destroy through Terragrunt.

**Usage:** `terragrunt destroy [flags]`

A convenience shortcut equivalent to 'terragrunt run -- destroy'.
Destroys all resources managed by Terraform in the module.
Use with extreme caution as this is destructive.

**Options:**
- `--all`: Destroy all modules in the stack
- `-auto-approve`: Skip interactive approval
- `-target`: Target specific resources

*Destroy resources interactively*
```bash
terragrunt destroy
```

*Force destroy without confirmation*
```bash
terragrunt destroy -auto-approve
```

*Destroy all modules (reverse dependency order)*
```bash
terragrunt destroy --all -auto-approve
```

Docs: https://docs.terragrunt.com/reference/cli/commands/opentofu-shortcuts/

## COMMAND: init

**Category:** shortcut

Shortcut for running terraform init through Terragrunt.

**Usage:** `terragrunt init [flags]`

A convenience shortcut equivalent to 'terragrunt run -- init'.
Initializes the Terraform working directory, downloading providers
and configuring the backend.

**Options:**
- `-upgrade`: Upgrade provider versions
- `-reconfigure`: Reconfigure backend, ignoring saved configuration
- `-migrate-state`: Migrate state from one backend to another

*Initialize the module*
```bash
terragrunt init
```

*Upgrade providers*
```bash
terragrunt init -upgrade
```

*Reconfigure backend*
```bash
terragrunt init -reconfigure
```

Docs: https://docs.terragrunt.com/reference/cli/commands/opentofu-shortcuts/

## COMMAND: output

**Category:** shortcut

Shortcut for running terraform output through Terragrunt.

**Usage:** `terragrunt output [flags] [name]`

A convenience shortcut equivalent to 'terragrunt run -- output'.
Shows the outputs from the Terraform state for the current module.

**Options:**
- `-json`: Output in JSON format
- `-raw`: Output raw value (for single output)

*Show all outputs*
```bash
terragrunt output
```

*Show specific output*
```bash
terragrunt output vpc_id
```

*Get output as JSON*
```bash
terragrunt output -json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/opentofu-shortcuts/

## COMMAND: plan

**Category:** shortcut

Shortcut for running terraform plan through Terragrunt.

**Usage:** `terragrunt plan [flags]`

A convenience shortcut equivalent to 'terragrunt run -- plan'. 
Runs terraform plan with all Terragrunt configuration applied, including
input variables, backend configuration, and any before/after hooks.

**Options:**
- `--all`: Run plan on all modules in the stack
- `-out`: Save the plan to a file
- `-target`: Target specific resources
- `-var`: Set a variable
- `-var-file`: Load variables from a file

*Run plan on current module*
```bash
terragrunt plan
```

*Plan all modules*
```bash
terragrunt plan --all
```

*Save plan to file*
```bash
terragrunt plan -out=tfplan
```

Docs: https://docs.terragrunt.com/reference/cli/commands/opentofu-shortcuts/

## COMMAND: stack clean

**Category:** stack

Clean Terragrunt cache and generated files from the stack.

**Usage:** `terragrunt stack clean [flags]`

Removes Terragrunt cache directories (.terragrunt-cache) and optionally
other generated files from all modules in the stack.

**Options:**
- `--all`: Clean all generated files, not just cache

*Clean cache from all modules*
```bash
terragrunt stack clean
```

*Clean all generated files*
```bash
terragrunt stack clean --all
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/clean/

## COMMAND: stack generate

**Category:** stack

Generate a stack configuration from existing Terragrunt modules.

**Usage:** `terragrunt stack generate [flags]`

Scans the directory tree for Terragrunt modules and generates a stack 
configuration file (terragrunt.stack.hcl) that defines the relationships
between modules.

**Options:**
- `--output`: Output file path

*Generate stack configuration*
```bash
terragrunt stack generate
```

*Generate to custom file*
```bash
terragrunt stack generate -o my-stack.hcl
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/generate/

## COMMAND: stack output

**Category:** stack

Show outputs from all modules in a stack.

**Usage:** `terragrunt stack output [flags]`

Displays the Terraform outputs from all modules in the stack. Useful for 
getting a summary of all resources and their outputs across the entire infrastructure.

**Options:**
- `--json`: Output in JSON format

*Show all stack outputs*
```bash
terragrunt stack output
```

*Show outputs in JSON format*
```bash
terragrunt stack output --json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/output/

## COMMAND: stack run

**Category:** stack

Run a Terraform command across all modules in a stack.

**Usage:** `terragrunt stack run [flags] -- [terraform command]`

Execute Terraform commands across all modules defined in a stack configuration.
The stack run command respects dependency ordering and can run modules in parallel.

**Options:**
- `--parallelism`: Maximum parallel operations
- `--ignore-dependency-errors`: Continue even if dependencies fail

*Plan all modules in the stack*
```bash
terragrunt stack run -- plan
```

*Apply all modules with limited parallelism*
```bash
terragrunt stack run --parallelism=3 -- apply -auto-approve
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/run/

## COMMAND: info strict

**Category:** configuration

List and inspect strict controls (opt-in controls that turn deprecation warnings into errors).

**Usage:** `terragrunt info strict`

Docs: https://docs.terragrunt.com/reference/cli/commands/info/strict/
