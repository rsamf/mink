# Enable SQL Admin API
resource "google_project_service" "sqladmin_api" {
  service = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

# CloudSQL Instance
resource "google_sql_database_instance" "master" {
  name             = "${var.service_name}-db"
  database_version = "POSTGRES_18"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    # Open for public access. This is for MCP use and for my working demo.
    ip_configuration {
        ipv4_enabled = true
        authorized_networks {
          name  = "all"
          value = "0.0.0.0/0"
        }
    }
  }

  deletion_protection  = false # Set to true for production

  depends_on = [google_project_service.sqladmin_api]
}

# Database
resource "google_sql_database" "database" {
  name     = "mink"
  instance = google_sql_database_instance.master.name
}

# User
resource "google_sql_user" "users" {
  name     = "mink-user"
  instance = google_sql_database_instance.master.name
  password = var.db_password
}

output "db_connection_name" {
  value = google_sql_database_instance.master.connection_name
}
