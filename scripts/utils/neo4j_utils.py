"""
Utility functions for working with Neo4j.
"""

from neo4j import GraphDatabase


def get_neo4j_connection(uri, user, password):
    """Create a Neo4j driver connection."""
    return GraphDatabase.driver(uri, auth=(user, password))


def execute_query(driver, query, params=None):
    """Execute a Cypher query and return the results."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record for record in result]


def create_index(driver, label, property_name):
    """Create an index on a label and property."""
    with driver.session() as session:
        session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.{property_name})")


def create_constraint(driver, label, property_name):
    """Create a uniqueness constraint on a label and property."""
    with driver.session() as session:
        session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE")


def get_database_statistics(driver):
    """Get basic statistics about the database."""
    stats = {}
    
    with driver.session() as session:
        # Count nodes by label
        result = session.run("CALL db.labels() YIELD label RETURN label")
        labels = [record["label"] for record in result]
        
        for label in labels:
            count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            stats[f"{label}_count"] = count_result.single()["count"]
        
        # Count relationship types
        result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        rel_types = [record["relationshipType"] for record in result]
        
        for rel_type in rel_types:
            count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
            stats[f"{rel_type}_count"] = count_result.single()["count"]
    
    return stats
