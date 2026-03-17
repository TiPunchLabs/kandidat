# GitHub Provider Documentation:
# https://registry.terraform.io/providers/integrations/github/latest

terraform {
  required_version = ">= 1.11.0"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 4.0"
    }
  }
}

provider "github" {
  owner = var.github_owner
  token = var.github_token
}
