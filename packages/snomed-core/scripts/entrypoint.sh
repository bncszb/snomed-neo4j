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

# Function to extract zip files
extract_zip_files() {
    local data_dir="$1"
    log "Checking for zip files to extract in $data_dir..."
    
    # Find all zip files in the directory
    local zip_files=$(find "$data_dir" -name "*.zip" -type f)
    
    if [ -z "$zip_files" ]; then
        log "No zip files found to extract."
        return 0
    fi
    
    # Extract each zip file
    for zip_file in $zip_files; do
        log "Extracting: $(basename "$zip_file")"
        
        # Create extraction directory based on zip filename (without .zip extension)
        local extract_dir="${zip_file%.zip}"
        
        # Extract the zip file
        if unzip -q "$zip_file" -d "$extract_dir"; then
            log "Successfully extracted: $(basename "$zip_file")"
            
            # Optionally remove the zip file after successful extraction
            # Uncomment the next line if you want to delete zip files after extraction
            # rm "$zip_file"
        else
            log "ERROR: Failed to extract: $(basename "$zip_file")"
            return 1
        fi
    done
    
    log "All zip files extracted successfully."
    return 0
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
    
        # Check if API credentials are provided
        if [ -z "$SNOMED_API_KEY" ]; then
            log "ERROR: SNOMED_API_KEY must be provided for startup_download."
            exit 1
        fi
        
        # Create snomed directory if it doesn't exist
        mkdir -p /mnt/snomed
        
        # Download SNOMED CT data
        uv run python /scripts/download_snomed.py \
            --api-key "$SNOMED_API_KEY" \
            --edition "$SNOMED_EDITION" \
            --version "$SNOMED_VERSION" \
            --output-dir "/mnt/snomed"
        
        if [ $? -ne 0 ]; then
            log "ERROR: Failed to download SNOMED CT data."
            exit 1
        fi
        
        # Extract downloaded zip files
        extract_zip_files "/mnt/snomed"
        if [ $? -ne 0 ]; then
            log "ERROR: Failed to extract SNOMED CT data."
            exit 1
        fi
    else
        # Data directory exists but might contain zip files that need extraction
        log "SNOMED data directory exists. Checking for zip files to extract..."
        extract_zip_files "/mnt/snomed"
        if [ $? -ne 0 ]; then
            log "ERROR: Failed to extract existing zip files."
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