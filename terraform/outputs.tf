output "service_url" {
  value = google_cloud_run_v2_service.default.uri
}

output "artifact_registry_repo_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}

output "db_connection_name" {
  value = google_sql_database_instance.master.connection_name
}

