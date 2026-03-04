# =============================================================================
# GitLab Project Variables
# =============================================================================
# These variables configure the GitLab project managed by Terraform.
# Sensitive values should be passed via environment variables or tfvars files.
# =============================================================================

variable "gitlab_token" {
  description = "GitLab Personal Access Token with api scope. Set via TF_VAR_gitlab_token environment variable."
  type        = string
  sensitive   = true
}

variable "gitlab_namespace_id" {
  description = "GitLab namespace (group or user) ID where the project will be created."
  type        = number
}

variable "gitlab_namespace_path" {
  description = "GitLab namespace path (e.g. 'xgueret' or 'mygroup/subgroup'). Used for data source lookups."
  type        = string
}

variable "project_name" {
  description = "Name of the GitLab project."
  type        = string
  default     = "kandidat"
}

variable "project_description" {
  description = "Short description displayed on the project page."
  type        = string
  default     = "A personal web interface to track and manage job applications — Flask, SQLite, vanilla CSS"
}

variable "visibility_level" {
  description = "Project visibility: 'public', 'internal', or 'private'."
  type        = string
  default     = "private"

  validation {
    condition     = contains(["public", "internal", "private"], var.visibility_level)
    error_message = "Visibility must be 'public', 'internal', or 'private'."
  }
}
