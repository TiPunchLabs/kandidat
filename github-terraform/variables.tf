# =============================================================================
# GitHub Repository Variables
# =============================================================================
# These variables configure the GitHub repository managed by Terraform.
# Sensitive values should be passed via environment variables or tfvars files.
# =============================================================================

variable "github_token" {
  description = "GitHub Personal Access Token with repo scope. Set via TF_VAR_github_token environment variable."
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub organization or user that owns the repository."
  type        = string
  default     = "TiPunchLabs"
}

variable "repository_name" {
  description = "Name of the GitHub repository."
  type        = string
  default     = "kandidat"
}

variable "repository_description" {
  description = "Short description displayed on the repository page."
  type        = string
  default     = "A personal web interface to track and manage job applications — Flask, SQLite, vanilla CSS (mirror of GitLab)"
}

variable "visibility" {
  description = "Repository visibility: 'public' or 'private'."
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private"], var.visibility)
    error_message = "Visibility must be 'public' or 'private'."
  }
}
