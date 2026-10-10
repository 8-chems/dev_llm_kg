terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.region
}

# Service Account for API service
resource "google_service_account" "api" {
  account_id   = "sa-jev-graphrag-api"
  display_name = "Jev GraphRAG API Service Account"
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "typesafe" {
  secret_id = "typesafe-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "anthropic" {
  secret_id = "anthropic-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "neo4j_password" {
  secret_id = "neo4j-password"
  replication {
    auto {}
  }
}

# Secret Accessor IAM bindings
resource "google_secret_manager_secret_iam_member" "typesafe_access" {
  secret_id = google_secret_manager_secret.typesafe.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "anthropic_access" {
  secret_id = google_secret_manager_secret.anthropic.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "neo4j_access" {
  secret_id = google_secret_manager_secret.neo4j_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

# Pub/Sub Topic for Escalations
resource "google_pubsub_topic" "escalations" {
  name = var.pubsub_topic_name
}

resource "google_pubsub_topic_iam_member" "publisher" {
  topic  = google_pubsub_topic.escalations.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.api.email}"
}

# BigQuery Dataset & Decision Log Table
resource "google_bigquery_dataset" "decisions" {
  dataset_id                 = var.bq_dataset_name
  location                   = var.region
  delete_contents_on_destroy = false
}

resource "google_bigquery_table" "decision_log" {
  dataset_id = google_bigquery_dataset.decisions.dataset_id
  table_id   = "decision_log"

  time_partitioning {
    type  = "DAY"
    field = "ts"
  }

  expiration_ms = 7776000000 # 90 days TTL

  schema = <<EOF
[
  {"name": "ts", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "request_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "decision", "type": "STRING", "mode": "REQUIRED"},
  {"name": "label_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "p", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "probs", "type": "JSON", "mode": "NULLABLE"},
  {"name": "model_version", "type": "STRING", "mode": "REQUIRED"},
  {"name": "latency_ms", "type": "INTEGER", "mode": "REQUIRED"},
  {"name": "mode", "type": "STRING", "mode": "REQUIRED"},
  {"name": "tau", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "outcome", "type": "STRING", "mode": "REQUIRED"},
  {"name": "escalated_to", "type": "STRING", "mode": "REQUIRED"},
  {"name": "env", "type": "STRING", "mode": "REQUIRED"}
]
EOF
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "api" {
  name     = "jev-graphrag-api"
  location = var.region

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = 20
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name  = "PIPELINE_MODE"
        value = var.pipeline_mode
      }
      env {
        name  = "JEV_MODEL"
        value = "jev-1.13"
      }
      env {
        name = "TYPESAFE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.typesafe.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NEO4J_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.neo4j_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

variable "pubsub_topic_name" {
  type    = string
  default = "escalations"
}

variable "bq_dataset_name" {
  type    = string
  default = "decisions"
}
