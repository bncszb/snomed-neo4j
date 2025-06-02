# SNOMED CT Neo4j Docker Image

> **DISCLAIMER**: This project is currently under active development and is not a finished product. Features are being added as needed for other projects. Use at your own risk and expect changes to the API and functionality.

A Docker image that provides a Neo4j database pre-configured for SNOMED CT terminology. This project allows users to easily deploy a graph database containing SNOMED CT data for healthcare applications, research, and development.

## Overview

This Docker image packages Neo4j with scripts to load and configure SNOMED CT data. The image is designed to be compliant with SNOMED International's licensing requirements by not distributing the SNOMED CT data directly.

## Features

- **Neo4j Database**: Pre-configured Neo4j database optimized for SNOMED CT graph structure
- **Data Loading**: Scripts to load SNOMED CT data from user-provided sources
- **Customizable**: Options to create slim databases by filtering specific relationship types or concept hierarchies
- **Secure**: Supports authentication via environment variables
- **Flexible Data Sourcing**: Multiple options for providing SNOMED CT data:
  - Mount local SNOMED CT files (user-provided)
  - Download during build using API keys (requires SNOMED International credentials)
  - Download during container startup using API keys (requires SNOMED International credentials)

## Requirements

- Docker
- Valid SNOMED International license and API credentials (for download options)
- SNOMED CT RF2 release files (for mount option)

## Usage

### Environment Variables

| Variable                       | Description                                                        | Default         | Required             |
| ------------------------------ | ------------------------------------------------------------------ | --------------- | -------------------- |
| `SNOMED_API_KEY`               | SNOMED International API key                                       | -               | For download options |
| `SNOMED_API_SECRET`            | SNOMED International API secret                                    | -               | For download options |
| `SNOMED_EDITION`               | SNOMED edition to download (e.g., 'international', 'us')           | 'international' | No                   |
| `SNOMED_VERSION`               | SNOMED version to download (e.g., '20230131')                      | latest          | No                   |
| `SNOMED_DATA_SOURCE`           | Data source method ('mount', 'build_download', 'startup_download') | 'mount'         | Yes                  |
| `SNOMED_SLIM_MODE`             | Enable slim database creation                                      | 'false'         | No                   |
| `SNOMED_INCLUDE_RELATIONSHIPS` | Comma-separated list of relationship types to include              | all             | With slim mode       |
| `SNOMED_INCLUDE_HIERARCHIES`   | Comma-separated list of parent concept IDs to include              | all             | With slim mode       |
| `SNOMED_NEO4J_AUTH`            | Neo4j authentication credentials                                   | neo4j/neo4j     | No                   |

### Docker Run Examples

**Using mounted SNOMED CT files:**

```bash
docker run -d \
  -p 7474:7474 -p 7687:7687 \
  -v /path/to/snomed/files:/data/snomed \
  -e SNOMED_DATA_SOURCE=mount \
  -e SNOMED_NEO4J_AUTH=neo4j/password \
  snomed-neo4j
```

**Downloading during startup:**

```bash
docker run -d \
  -p 7474:7474 -p 7687:7687 \
  -e SNOMED_DATA_SOURCE=startup_download \
  -e SNOMED_API_KEY=your_api_key \
  -e SNOMED_API_SECRET=your_api_secret \
  -e SNOMED_EDITION=international \
  -e SNOMED_NEO4J_AUTH=neo4j/password \
  snomed-neo4j
```

**Creating a slim database:**

```bash
docker run -d \
  -p 7474:7474 -p 7687:7687 \
  -v /path/to/snomed/files:/data/snomed \
  -e SNOMED_DATA_SOURCE=mount \
  -e SNOMED_SLIM_MODE=true \
  -e SNOMED_INCLUDE_RELATIONSHIPS=116680003,363698007 \
  -e SNOMED_INCLUDE_HIERARCHIES=404684003,71388002 \
  -e SNOMED_NEO4J_AUTH=neo4j/password \
  snomed-neo4j
```

## Project Structure

```
snomed-neo4j/
├── Dockerfile
├── docker-compose.yml
├── scripts/
│   ├── entrypoint.sh
│   ├── download_snomed.py
│   ├── load_snomed.py
│   ├── create_slim_db.py
│   └── utils/
│       ├── __init__.py
│       ├── neo4j_utils.py
│       └── snomed_utils.py
├── config/
│   └── neo4j.conf
└── client/
    ├── __init__.py
    └── snomed_client.py
```

## Technical Details

### Data Loading Process

1. The container checks the `SNOMED_DATA_SOURCE` environment variable
2. Based on the source setting:
   - `mount`: Uses SNOMED CT files mounted at `/data/snomed`
   - `build_download`: Downloads files during image build (requires build args)
   - `startup_download`: Downloads files when container starts
3. Loads the RF2 files into Neo4j using optimized Cypher queries
4. If `SNOMED_SLIM_MODE` is enabled, filters the database according to specified parameters

### Neo4j Configuration

The Neo4j database is configured with:

- Appropriate memory settings for SNOMED CT data
- Indexes on commonly queried fields
- Optimized cache settings for terminology queries

### Python Client

A Python client library is included to simplify interaction with the SNOMED CT Neo4j database:

- Connection management
- Common SNOMED CT queries
- Utility functions for concept navigation and subsumption testing

## Legal Considerations

This project does not distribute SNOMED CT data. Users must have a valid license from SNOMED International to use SNOMED CT content. The scripts provided facilitate loading user-provided or user-authenticated downloads of SNOMED CT.

## Future Enhancements

- Support for multiple SNOMED CT extensions
- Advanced filtering options for slim database creation
- Performance optimizations for large-scale deployments
- Integration with terminology servers

## License

[MIT License](LICENSE)
