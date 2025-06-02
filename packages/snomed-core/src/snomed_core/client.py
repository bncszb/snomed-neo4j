import os

from neo4j import Driver, GraphDatabase


def get_driver(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> Driver:
    uri = uri or os.environ["NEO4J_URI"]
    user = user or os.environ["NEO4J_USER"]
    password = password or os.environ["NEO4J_PASSWORD"]

    return GraphDatabase.driver(uri, auth=(user, password))
