terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Generate random API key
resource "random_password" "api_key" {
  length  = 32
  special = true
}

# Enable necessary APIs
resource "google_project_service" "run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry Repository
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for Mink"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry_api]
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "default" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    gpu_zonal_redundancy_disabled = true

    node_selector {
      accelerator = "nvidia-l4"
    }

    containers {
      # This image/tag is a placeholder. You will need to build and push the image 
      # to this location before applying, or update this after the first push.
      # Format: region-docker.pkg.dev/project_id/repository_id/image:tag
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/mink:latest"

      command = [
        "python",
        "-m",
        "mink.main",
        "db=cloudsql",
        "cast.api_key=${var.anthropic_key != null ? var.anthropic_key : ""}",
        "server.auth.keys=extend_list(${random_password.api_key.result})"
      ]

      ports {
        container_port = 8000
      }

      env {
        name  = "DB_USER"
        value = google_sql_user.users.name
      }
      env {
        name  = "DB_PASS"
        value = google_sql_user.users.password
      }
      env {
        name  = "DB_NAME"
        value = google_sql_database.database.name
      }
      env {
        name  = "DB_HOST"
        value = google_sql_database_instance.master.public_ip_address
      }
      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.master.connection_name
      }
      # Local proxy or direct socket? usually cloud run uses socket at /cloudsql/CONNECTION_NAME
      # But with psycopg and python, we might need to adjust connection string. 
      # For now, let's assume valid pg config.

      # Example resource limits - adjust as needed
      resources {
        limits = {
          cpu              = "4"
          memory           = "16Gi"
          "nvidia.com/gpu" = "1"
        }
      }
    }
  }

  depends_on = [google_project_service.run_api]
}

# Allow unauthenticated invocations (or restrict as needed)
# Since we have API Key auth in the app, we might want to allow public invocation 
# so the app's middleware handles it, OR restrict to specific IAM users.
# Assuming public access to the URL is fine and app handles auth:
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.default.location
  service  = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
