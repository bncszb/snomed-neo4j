import os

from neo4j import Driver, GraphDatabase


def get_neo4j_bolt_uri() -> str:
    return f"bolt://{os.environ['SNOMED_NEO4J_HOST']}:7687"


def get_neo4j_http_uri() -> str:
    return f"http://{os.environ['SNOMED_NEO4J_HOST']}:7474"


def get_driver(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> Driver:
    uri = uri or get_neo4j_bolt_uri()
    user = user or os.environ["SNOMED_NEO4J_USER"]
    password = password or os.environ["SNOMED_NEO4J_PASSWORD"]

    return GraphDatabase.driver(uri, auth=(user, password))
