variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy to"
  type        = string
}

variable "db_password" {
  description = "The password for the Cloud SQL user"
  type        = string
}

variable "anthropic_key" {
  description = "The API key for Anthropic"
  type        = string
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "mink-server"
}

variable "repository_id" {
  description = "The ID of the Artifact Registry repository"
  type        = string
  default     = "mink-repo"
}
