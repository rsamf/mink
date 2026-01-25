output "service_url" {
  value = google_cloud_run_v2_service.default.uri
}

output "api_key" {
  value     = random_password.api_key.result
  description = "Generated API key for Mink service"
  sensitive = true
}

output "artifact_registry_url" {
  value = local.image_name
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
