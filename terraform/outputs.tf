output "service_url" {
  value = google_cloud_run_v2_service.default.uri
}

output "artifact_registry_repo_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}

output "db_name" {
  value = google_sql_database.database.name
}

output "db_password" {
  value = var.db_password
}

output "db_host" {
    value = google_sql_database_instance.master.public_ip_address
}

output "db_user" {
    value = google_sql_user.users.name
}
