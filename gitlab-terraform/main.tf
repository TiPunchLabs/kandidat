resource "gitlab_project" "project" {
  name         = var.project_name
  namespace_id = var.gitlab_namespace_id
  description  = var.project_description

  visibility_level = var.visibility_level

  issues_access_level = "enabled"
  wiki_access_level   = "enabled"

  topics = ["flask", "sqlite", "python", "job-tracker", "web-app", "pydantic", "jinja2"]
}

# =============================================================================
# Branch Protection - Require CI to pass before merge
# =============================================================================
resource "gitlab_branch_protection" "main" {
  project            = gitlab_project.project.id
  branch             = "main"
  push_access_level  = "maintainer"
  merge_access_level = "maintainer"
  allow_force_push   = false
}
