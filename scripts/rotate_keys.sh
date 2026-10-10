#!/usr/bin/env bash
set -euo pipefail

# Key rotation script for Secret Manager secrets

PROJECT_ID=${1:-"dev-graphrag-gcp"}
SECRET_NAME=${2:-"typesafe-api-key"}
NEW_SECRET_VALUE=${3:-""}

if [ -z "$NEW_SECRET_VALUE" ]; then
  echo "Usage: ./rotate_keys.sh <project_id> <secret_name> <new_secret_value>"
  exit 1
fi

echo "Adding new secret version for ${SECRET_NAME} in project ${PROJECT_ID}..."
echo -n "${NEW_SECRET_VALUE}" | gcloud secrets versions add "${SECRET_NAME}" --project="${PROJECT_ID}" --data-file=-

echo "Key rotation completed successfully."
