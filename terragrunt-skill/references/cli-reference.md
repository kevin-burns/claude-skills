# Terragrunt CLI Reference (1.0.x)

> Scope: Terragrunt 1.0.x ONLY. Never generate pre-1.0 command forms (run-all, hclfmt, plan-all,
> graph-dependencies, terragrunt- prefixed flags, etc.). Canonical docs: https://docs.terragrunt.com/reference/cli/
> Verified against the Terragrunt 1.0 CLI command tree (docs.terragrunt.com, June 2026).

Lookup: `grep -n '^## COMMAND:' cli-reference.md` | `grep -A 20 '^## COMMAND: stack run'`

## 1.0 command tree
`run` `exec` | `backend bootstrap|migrate|delete` | `stack generate|run|output|clean` | `catalog` `scaffold` | `find` `list` | `hcl fmt|validate` | `dag graph` | `render` | `info print|strict` | OpenTofu shortcuts (`plan`, `apply`, `destroy`, `output`, `init`, ...)

## FILTERS (--filter) — unit/stack targeting
The `--filter` flag is the single 1.0 mechanism for targeting units and stacks, replacing all pre-1.0 queue flags (`--queue-include-dir`, `--queue-exclude-dir`, etc., which remain only as aliases that translate into filter expressions).

**Expression types:**
- **name** — `app*` (glob) or `app1` (exact). Matches units/stacks by name.
- **path** — `./networking`, `./prod/**`, `/abs/path/**`.
- **attribute** — `type=unit`, `type=stack`, `external=true|false`, `reading=shared.hcl`.
- **negated (`!`)** — `'!./legacy'`, `'!name=legacy'`.
- **graph** — dependency traversal (see operators below).
- **git** — changed-since expressions, e.g. `'[main...HEAD]'`, `'[HEAD~1...HEAD]'`.

**Combining:** intersect/refine with a pipe `|` (`'./prod/** | type=unit'`); **union** by repeating the flag (`--filter app1 --filter app2` = OR).

**Exclude-by-default:** using *any* positive filter (one not starting with `!`) switches Terragrunt out of "include everything" mode — it then includes only what the positive filters match. Negative-only filters keep the include-all default and just subtract.

**Graph traversal operators** (trailing `...` walks toward **dependencies**, leading `...` toward **dependents**):
- `target...` — the target **and all its dependencies**.
- `...target` — the target **and everything that depends on it**.
- `...target...` — both directions.
- `^` — exclude the target itself, keep its related components (`...^vpc` = dependents of `vpc`, not `vpc`).
- depth limits: `service...1` (deps, 1 level), `1...vpc` (direct dependents), `1...db...2`. Depth applies per target.

**Git-affected helpers:**
- `--filter-affected` — shorthand that auto-detects the repo's default branch and diffs it against HEAD (≈ `--filter '[main...HEAD]'`).
- `--filter-allow-destroy` — required safeguard: git filters will not destroy units removed between two refs unless this flag is set. Git filters strongly assume remote state.

**Filters file:** name a filters file `.terragrunt-filters` and Terragrunt auto-loads it from the working directory; otherwise pass one with `--filters-file <path>` (one query per line, `#` comments).

```bash
terragrunt find --filter './prod/** | type=unit'
terragrunt run --all apply --filter 'name=vpc'
terragrunt run --all plan --filter-affected            # only git-changed units vs default branch
terragrunt run --all plan --filter '...vpc'            # vpc and everything downstream of it
```
Docs: https://docs.terragrunt.com/features/filter/ · graph: https://docs.terragrunt.com/features/filter/graph/ · git: https://docs.terragrunt.com/features/filter/git/. For full syntax, fetch those pages or use C7 search.

## COMMAND: backend bootstrap

**Category:** backend

Create and configure the remote state backend.

**Usage:** `terragrunt backend bootstrap [flags]`

Automatically provisions the backend resources needed for remote state storage —
**but only for the backends Terragrunt natively manages: S3 (bucket + optional
DynamoDB lock table + access-logging bucket) and GCS (bucket).**

> **Azure (azurerm) is NOT bootstrapped.** Azure support is gated behind the
> `azure-backend` experiment, which currently does not change behavior — Terragrunt
> does **not** create, migrate, or delete Azure storage accounts/containers. The
> `azurerm` backend is passed through to OpenTofu/Terraform as-is, so the storage
> account and blob container must already exist (create them with `az`, Bicep, or a
> separate bootstrap unit). Do not tell users `backend bootstrap` provisions Azure
> state. Ref: references/azure-backend.md ·
> https://docs.terragrunt.com/reference/experiments/active

**Options:**
- `--config`: Path to the Terragrunt configuration file

*Bootstrap the backend defined in terragrunt.hcl*
```bash
terragrunt backend bootstrap
```

Docs: https://docs.terragrunt.com/reference/cli/commands/backend/bootstrap/

## COMMAND: backend delete

**Category:** backend

Delete the backend state for a unit.

**Usage:** `terragrunt backend delete [flags]`

Deletes the backend state object (e.g. the state file) for the current unit. Use with
caution; `--force` is dangerous — deleting unversioned state is irreversible, so back up
first. Documented for S3 (and applies to the natively-managed backends); **for `azurerm`
Terragrunt does not delete Azure resources** (the `azure-backend` experiment is a no-op).

**Options:**
- `--all`: Delete state for all units in the stack
- `--config`: Path to the Terragrunt configuration file
- `--download-dir`: Custom download directory
- `--force`: Skip confirmation prompt (dangerous — irreversible for unversioned state)

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

Migrate state between two units.

**Usage:** `terragrunt backend migrate [flags] <src-unit> <dest-unit>`

Moves state from one unit to another — commonly needed when a unit is renamed/moved and
its state key (e.g. a `path_relative_to_include()` key) changes. When **both** source and
destination use the same natively-supported backend (both S3, or both GCS), Terragrunt
moves state with the cloud SDK transparently. Otherwise — including any **`azurerm`**
unit, since Terragrunt does not natively migrate Azure state — it falls back to the
OpenTofu/Terraform CLI to perform the migration.

**Options:**
- `--config`: Path to the Terragrunt configuration file
- `--download-dir`: Custom download directory
- `--force`: Skip confirmation prompt

*Migrate state after renaming a unit*
```bash
terragrunt backend migrate ./old-name ./new-name
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

## COMMAND: stack generate

**Category:** stack

Materialize a stack from a `terragrunt.stack.hcl` file.

**Usage:** `terragrunt stack generate [flags]`

Reads the `unit`/`stack` blocks in `terragrunt.stack.hcl` and **generates the
`.terragrunt-stack/` directory** — one subdirectory per block at its `path`, each holding
the unit's `terragrunt.hcl` (and a `terragrunt.values.hcl` when the block sets `values`).
It discovers all `terragrunt.stack.hcl` files in the tree and processes them in parallel.
This is *not* a reverse-engineer-from-modules command — it expands the stack definition you
authored.

> **Regeneration is not a clean replace by default** — stale files (including stale
> `terragrunt.values.hcl`) are left in place. Use `--source-update` to refresh sources and
> regenerate clean, or run `terragrunt stack clean` first.

**Options:**
- `--source-update`: Refresh unit/stack sources and regenerate cleanly
- `--no-stack-validate`: Skip directory/config validation of the generated stack
- `--parallelism`: Maximum parallel operations
- `--filter`: Target a subset (needs `type=stack` to select stacks)
- `--no-cas` / `--cas-clone-depth`: CAS controls (experimental; `--no-cas` errors if any block sets `update_source_with_cas = true`)

*Materialize the stack into `.terragrunt-stack/`*
```bash
terragrunt stack generate
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/generate/

## COMMAND: stack run

**Category:** stack

Run an OpenTofu/Terraform command across all units in a stack.

**Usage:** `terragrunt stack run <command> [flags]`

Runs a command against every unit in the stack, respecting dependency order (it
auto-regenerates `.terragrunt-stack/` first unless told not to). Effectively `run --all`
scoped to the generated stack, so it inherits the `run` flags (`--parallelism`, `--filter`,
the queue flags, etc.).

**Options:**
- `--no-stack-generate`: Skip automatic stack regeneration before running (env `TG_NO_STACK_GENERATE`)
- `--parallelism`: Maximum parallel operations
- `--no-cas` / `--cas-clone-depth`: CAS controls (experimental)

*Plan all units in the stack*
```bash
terragrunt stack run plan
```

*Apply with limited parallelism*
```bash
terragrunt stack run apply --parallelism=3
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/run/

## COMMAND: stack output

**Category:** stack

Show consolidated outputs from all units in a stack.

**Usage:** `terragrunt stack output [flags]`

Retrieves and aggregates the outputs of every unit in the stack into a single view.

**Options:**
- `--format`: Output format — `default` (HCL), `json`, or `raw` (env `TG_FORMAT`)
- `--json`: Equivalent to `--format json` (env `TG_JSON`)
- `--raw`: Equivalent to `--format raw` (env `TG_RAW`)
- `--no-stack-generate`: Skip automatic stack regeneration first (env `TG_NO_STACK_GENERATE`)

*Show all stack outputs (HCL)*
```bash
terragrunt stack output
```

*Show outputs as JSON*
```bash
terragrunt stack output --json
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/output/

## COMMAND: stack clean

**Category:** stack

Remove the generated `.terragrunt-stack/` directory.

**Usage:** `terragrunt stack clean`

Deletes the `.terragrunt-stack/` directory produced by `stack generate` / `stack run`.
Use it before regenerating to guarantee no stale generated files remain. (No flags
documented.)

*Remove the generated stack*
```bash
terragrunt stack clean
```

Docs: https://docs.terragrunt.com/reference/cli/commands/stack/clean/

## COMMAND: info strict

**Category:** configuration

List and inspect strict controls (opt-in controls that turn deprecation warnings into errors).

**Usage:** `terragrunt info strict`

Docs: https://docs.terragrunt.com/reference/cli/commands/info/strict/
