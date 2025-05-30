FROM neo4j:5.13.0

LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="Neo4j database with SNOMED CT data"

# Install Python and required packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

# Create directories
RUN mkdir -p /data/snomed /scripts /config

# Copy scripts and configuration
COPY scripts/ /scripts/
COPY config/ /config/

# Set permissions
RUN chmod +x /scripts/entrypoint.sh

# Environment variables with defaults
ENV SNOMED_DATA_SOURCE=mount \
    SNOMED_SLIM_MODE=false \
    SNOMED_EDITION=international \
    NEO4J_dbms_memory_heap_initial__size=2G \
    NEO4J_dbms_memory_heap_max__size=4G \
    NEO4J_dbms_memory_pagecache_size=2G

# Expose Neo4j ports
EXPOSE 7474 7473 7687

# Set entrypoint
ENTRYPOINT ["/scripts/entrypoint.sh"]
