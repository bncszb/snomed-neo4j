# SNOMED CT Neo4j Client

A Python client library for interacting with SNOMED CT data stored in a Neo4j database.

## Installation

```bash
pip install snomed-neo4j-client
```

## Features

- Connect to a Neo4j database containing SNOMED CT data
- Retrieve concepts, descriptions, and relationships
- Navigate the SNOMED CT hierarchy (parents, children, ancestors, descendants)
- Search for concepts by term
- Check subsumption relationships between concepts
- Full Pydantic model support for type safety

## Usage

```python
from snomed_neo4j_client import SnomedClient

# Initialize the client
client = SnomedClient(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Get a concept by ID
concept = client.get_concept("138875005")  # SNOMED CT Concept (root)
print(concept)

# Get a concept with all its details
concept_details = client.get_concept_with_details("73211009")  # Diabetes mellitus
print(f"Concept: {concept_details.id}")
print(f"Descriptions: {len(concept_details.descriptions)}")
print(f"Relationships: {len(concept_details.relationships)}")

# Get the preferred term for a concept
term = client.get_preferred_term("73211009")
print(f"Preferred term: {term}")

# Check if one concept is a subtype of another
is_subtype = client.is_a("73211009", "64572001")  # Is diabetes a disease?
print(f"Is subtype: {is_subtype}")

# Find concepts by term
results = client.find_concepts("diabetes")
for result in results:
    print(f"{result['id']}: {result['term']}")

# Close the connection when done
client.close()
```

## Requirements

- Python 3.9+
- Neo4j database with SNOMED CT data
- Neo4j Python driver
- Pydantic 2.0+

## License

MIT
