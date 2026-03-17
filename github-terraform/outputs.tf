output "repository_url" {
  description = "GitHub repository URL"
  value       = github_repository.mirror.html_url
}

output "repository_full_name" {
  description = "GitHub repository full name (owner/repo)"
  value       = github_repository.mirror.full_name
}

output "clone_url" {
  description = "GitHub HTTPS clone URL (used by GitLab push mirror)"
  value       = github_repository.mirror.http_clone_url
}
