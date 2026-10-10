#!/bin/bash

# Stop existing containers
docker-compose down -v

# Remove any leftover volumes
rm -rf neo4j_data neo4j_logs neo4j_import

# Build and start the application
docker-compose build && docker-compose up -d

# Verify the application is running
sleep 5
curl -s http://localhost:8080/health | grep -q "OK"
if [ $? -eq 0 ]; then
  echo "Application is running successfully!"
else
  echo "Application failed to start. Check logs for errors."
  docker-compose logs -f app
fi""