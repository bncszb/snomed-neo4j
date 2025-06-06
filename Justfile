_:
    just --list

download:
    uv run --package snomed-neo4j-core download

load:
    uv run --package snomed-neo4j-core load

slim:
    uv run --package snomed-neo4j-core slim

