variable "gcp_project" {
  type        = string
  description = "GCP Project ID"
  default     = "dev-graphrag-gcp"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "europe-west9"
}

variable "env" {
  type        = string
  description = "Environment name (dev, staging, prod)"
  default     = "dev"
}

variable "pipeline_mode" {
  type        = string
  description = "Pipeline execution mode (off, shadow, live)"
  default     = "shadow"
}

variable "min_instances" {
  type        = number
  description = "Minimum Cloud Run instances"
  default     = 1
}

variable "image" {
  type        = string
  description = "Container image URI"
  default     = "europe-west9-docker.pkg.dev/dev-graphrag-gcp/app/jev-graphrag:latest"
}
