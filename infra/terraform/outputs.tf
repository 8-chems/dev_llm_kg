output "api_service_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "The URL of the deployed GraphRAG FastAPI Cloud Run service"
}

output "pubsub_topic_id" {
  value       = google_pubsub_topic.escalations.id
  description = "Pub/Sub escalations topic ID"
}

output "bigquery_dataset_id" {
  value       = google_bigquery_dataset.decisions.dataset_id
  description = "BigQuery dataset ID for decisions logging"
}
