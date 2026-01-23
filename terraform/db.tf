# Enable SQL Admin API
resource "google_project_service" "sqladmin_api" {
  service = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

# CloudSQL Instance
resource "google_sql_database_instance" "master" {
  name             = "${var.service_name}-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    # Enable public IP for simplicity, but consider private IP for production
    ip_configuration {
        ipv4_enabled = true
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
}

output "db_connection_name" {
  value = google_sql_database_instance.master.connection_name
}
