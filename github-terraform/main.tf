# =============================================================================
# GitHub Repository — Read-only mirror of GitLab
# =============================================================================
# This repository is a push mirror from GitLab. All development happens on
# GitLab (issues, MRs, CI/CD). GitHub is read-only for public visibility.
# =============================================================================

resource "github_repository" "mirror" {
  name        = var.repository_name
  description = var.repository_description
  visibility  = var.visibility

  # Project metadata
  homepage_url = "https://gitlab.com/tipunchlabs/kandidat"
  topics       = ["flask", "python", "job-tracker", "web-app", "pydantic", "jinja2", "mirror"]

  # Disable all collaboration features — GitLab is the source of truth
  has_issues      = false
  has_wiki        = false
  has_projects    = false
  # Archive protection
  archive_on_destroy = true

  # Vulnerability alerts (good practice even for mirrors)
  vulnerability_alerts = true
}
