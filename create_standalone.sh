#!/bin/bash
set -e

# Script to create a standalone SNOMED Neo4j image

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if API credentials are provided
if [[ -z "$SNOMED_API_KEY" || -z "$SNOMED_API_SECRET" ]]; then
    log "ERROR: Please set SNOMED_API_KEY and SNOMED_API_SECRET environment variables"
    exit 1
fi

IMAGE_NAME=${1:-"snomed-neo4j:standalone"}
TEMP_COMPOSE="docker-compose.temp.yml"

log "Creating standalone SNOMED Neo4j image: $IMAGE_NAME"

# Create temporary compose file for building
cat > $TEMP_COMPOSE << EOF
services:
  neo4j-temp:
    image: neo4j:5.13.0
    environment:
      - NEO4J_AUTH=neo4j/neo4jneo4j
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=2G
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_memory_pagecache_size=2G
    volumes:
      - temp_neo4j_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  importer-temp:
    build:
      context: .
      dockerfile: Dockerfile.importer
    environment:
      - NEO4J_PASSWORD=neo4jneo4j
      - SNOMED_SLIM_MODE=\${SNOMED_SLIM_MODE:-false}
      - SNOMED_DATA_SOURCE=startup_download
      - SNOMED_API_KEY=$SNOMED_API_KEY
      - SNOMED_API_SECRET=$SNOMED_API_SECRET
      - SNOMED_EDITION=\${SNOMED_EDITION:-international}
      - SNOMED_VERSION=\${SNOMED_VERSION:-latest}
    volumes:
      - ./data/snomed:/mnt/snomed
    depends_on:
      neo4j-temp:
        condition: service_healthy

volumes:
  temp_neo4j_data:
EOF

# Start Neo4j and run importer
log "Starting Neo4j and importing data..."
docker-compose -f $TEMP_COMPOSE up --build --exit-code-from importer-temp importer-temp

# Get the Neo4j container ID
NEO4J_CONTAINER=$(docker-compose -f $TEMP_COMPOSE ps -q neo4j-temp)

# Commit the Neo4j container as a new image
log "Creating standalone image..."
docker commit $NEO4J_CONTAINER $IMAGE_NAME

# Cleanup
log "Cleaning up..."
docker-compose -f $TEMP_COMPOSE down -v
rm $TEMP_COMPOSE

log "Standalone image created: $IMAGE_NAME"
log "To run: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/neo4jneo4j $IMAGE_NAME"