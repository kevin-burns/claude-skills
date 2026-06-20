# Template: Azure Blob Storage Remote State Backend
# Configure Azure Blob Storage backend with Azure AD authentication
# Variables:
#   {{subscription_id}} (required): Azure subscription ID
#   {{resource_group_name}} (required): Resource group containing storage account
#   {{storage_account_name}} (required): Storage account name
#   {{container_name}} (required): Blob container name
#   {{key}} (required): Path to state file within container

# NOTE (Terragrunt 1.0.x): remote_state backend "azurerm" passes through to the
# native OpenTofu/Terraform azurerm backend. Terragrunt does NOT bootstrap/migrate/
# delete Azure storage (azure-backend is a no-op experiment) — unlike S3/GCS, the
# storage account + container must already exist before init. use_azuread_auth=true is
# Microsoft-recommended (avoids storage shared keys, often disabled by policy); the
# deploying identity then needs the "Storage Blob Data Contributor" data-plane role.
# Full detail + gotchas: references/azure-backend.md
# Ref: https://docs.terragrunt.com/reference/experiments/active

remote_state {
  backend = "azurerm"
  config = {
    subscription_id      = "{{subscription_id}}"
    resource_group_name  = "{{resource_group_name}}"
    storage_account_name = "{{storage_account_name}}"
    container_name       = "{{container_name}}"
    key                  = "{{key}}"
    use_azuread_auth     = true
  }
}
