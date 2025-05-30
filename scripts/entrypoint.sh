#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if SNOMED data source is valid
if [[ "$SNOMED_DATA_SOURCE" != "mount" && "$SNOMED_DATA_SOURCE" != "build_download" && "$SNOMED_DATA_SOURCE" != "startup_download" ]]; then
    log "ERROR: Invalid SNOMED_DATA_SOURCE. Must be 'mount', 'build_download', or 'startup_download'."
    exit 1
fi

# Handle data download if needed
if [[ "$SNOMED_DATA_SOURCE" == "startup_download" ]]; then
    log "Downloading SNOMED CT data using API credentials..."
    
    # Check if API credentials are provided
    if [[ -z "$SNOMED_API_KEY" || -z "$SNOMED_API_SECRET" ]]; then
        log "ERROR: SNOMED_API_KEY and SNOMED_API_SECRET must be provided for startup_download."
        exit 1
    fi
    
    # Download SNOMED CT data
    python3 /scripts/download_snomed.py \
        --api-key "$SNOMED_API_KEY" \
        --api-secret "$SNOMED_API_SECRET" \
        --edition "$SNOMED_EDITION" \
        --version "$SNOMED_VERSION" \
        --output-dir "/data/snomed"
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to download SNOMED CT data."
        exit 1
    fi
fi

# Check if SNOMED data exists
if [ ! "$(ls -A /data/snomed)" ]; then
    log "ERROR: No SNOMED CT data found in /data/snomed."
    log "Please either mount SNOMED CT data or use download options."
    exit 1
fi

# Start Neo4j in the background
log "Starting Neo4j database..."
/docker-entrypoint.sh neo4j &
NEO4J_PID=$!

# Wait for Neo4j to start
log "Waiting for Neo4j to start..."
until curl -s -o /dev/null http://localhost:7474; do
    sleep 1
done
log "Neo4j started successfully."

# Load SNOMED CT data
log "Loading SNOMED CT data into Neo4j..."
python3 /scripts/load_snomed.py --data-dir "/data/snomed"

# Create slim database if requested
if [[ "$SNOMED_SLIM_MODE" == "true" ]]; then
    log "Creating slim database..."
    python3 /scripts/create_slim_db.py \
        --relationships "$SNOMED_INCLUDE_RELATIONSHIPS" \
        --hierarchies "$SNOMED_INCLUDE_HIERARCHIES"
fi

log "SNOMED CT data loaded successfully."

# Wait for Neo4j process to finish
wait $NEO4J_PID
