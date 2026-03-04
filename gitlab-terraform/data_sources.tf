data "gitlab_project" "existing_project" {
  path_with_namespace = "${var.gitlab_namespace_path}/${var.project_name}"

  count = 0 # Set to 1 to enable lookup of an existing project
}

locals {
  project_exists = length(data.gitlab_project.existing_project) > 0
}
