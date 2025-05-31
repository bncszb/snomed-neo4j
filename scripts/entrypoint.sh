#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if Neo4j has data
check_neo4j_data() {
    local count=$(cypher-shell -a bolt://neo4j:7687 -u neo4j -p ${NEO4J_PASSWORD} "MATCH (n) RETURN count(n) AS nodeCount" --format plain 2>/dev/null | tail -n 1 | tr -d ' ' || echo "0")
    echo "$count"
}

# Function to wait for Neo4j to be ready
wait_for_neo4j() {
    log "Waiting for Neo4j to be ready..."
    local max_attempts=60
    local attempt=0
    
    until curl -s -o /dev/null http://neo4j:7474 || [ $attempt -eq $max_attempts ]; do
        sleep 1
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log "ERROR: Neo4j is not accessible after $max_attempts seconds"
        exit 1
    fi
    
    log "Neo4j is accessible."
    
    # Wait a bit more for Neo4j to be fully ready for queries
    sleep 5
}

# Wait for Neo4j to be ready
wait_for_neo4j

# Check if database already has data
log "Checking if database contains data..."
node_count=$(check_neo4j_data)

if [[ "$node_count" -gt 0 ]]; then
    log "Database contains $node_count nodes. Service is running fine."
    log "Import skipped - data already exists."
else
    log "Database is empty. Checking for SNOMED data..."
    
    # Check if SNOMED data exists in /mnt/snomed
    if [ ! -d "/mnt/snomed" ] || [ ! "$(ls -A /mnt/snomed)" ]; then
        log "No SNOMED data found in /mnt/snomed. Attempting download..."
        
        # Handle data download
        if [[ "$SNOMED_DATA_SOURCE" == "startup_download" ]]; then
            log "Downloading SNOMED CT data using API credentials..."
            
            # Check if API credentials are provided
            if [[ -z "$SNOMED_API_KEY" || -z "$SNOMED_API_SECRET" ]]; then
                log "ERROR: SNOMED_API_KEY and SNOMED_API_SECRET must be provided for startup_download."
                exit 1
            fi
            
            # Create snomed directory if it doesn't exist
            mkdir -p /mnt/snomed
            
            # Download SNOMED CT data
            uv run python /scripts/download_snomed.py \
                --api-key "$SNOMED_API_KEY" \
                --api-secret "$SNOMED_API_SECRET" \
                --edition "$SNOMED_EDITION" \
                --version "$SNOMED_VERSION" \
                --output-dir "/mnt/snomed"
            
            if [ $? -ne 0 ]; then
                log "ERROR: Failed to download SNOMED CT data."
                exit 1
            fi
        else
            log "ERROR: No SNOMED CT data found in /mnt/snomed and download not configured."
            log "Please either mount SNOMED CT data to /mnt/snomed or set SNOMED_DATA_SOURCE=startup_download with API credentials."
            exit 1
        fi
    fi
    
    # Load SNOMED CT data
    log "Loading SNOMED CT data into Neo4j..."
    uv run python /scripts/load_snomed.py \
        --data-dir "/mnt/snomed" \
        --neo4j-uri "bolt://neo4j:7687" \
        --neo4j-user "neo4j" \
        --neo4j-password "${NEO4J_PASSWORD}"
    
    # Create slim database if requested
    if [[ "$SNOMED_SLIM_MODE" == "true" ]]; then
        log "Creating slim database..."
        uv run python /scripts/create_slim_db.py \
            --relationships "$SNOMED_INCLUDE_RELATIONSHIPS" \
            --hierarchies "$SNOMED_INCLUDE_HIERARCHIES" \
            --neo4j-uri "bolt://neo4j:7687" \
            --neo4j-user "neo4j" \
            --neo4j-password "${NEO4J_PASSWORD}"
    fi
    
    log "SNOMED CT data loaded successfully."
fi

log "Import process completed."