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
            count_result = session.run(f"MATCH (n:{label}) WHERE n.is_deleted IS NULL OR n.is_deleted = false RETURN count(n) as count")
            stats[f"{label}_count"] = count_result.single()["count"]
        
        # Count relationship types
        result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        rel_types = [record["relationshipType"] for record in result]
        
        for rel_type in rel_types:
            count_result = session.run(f"MATCH ()-[r:{rel_type}]->() WHERE r.is_deleted IS NULL OR r.is_deleted = false RETURN count(r) as count")
            stats[f"{rel_type}_count"] = count_result.single()["count"]
    
    return stats


def check_database_exists(driver):
    """Check if the database has any SNOMED CT data."""
    with driver.session() as session:
        result = session.run("MATCH (c:Concept) RETURN count(c) as count LIMIT 1")
        record = result.single()
        return record and record["count"] > 0


def check_database_health(driver):
    """Check the health of the Neo4j database."""
    health_info = {
        "status": "healthy",
        "issues": []
    }
    
    try:
        with driver.session() as session:
            # Check if database is responsive
            session.run("RETURN 1")
            
            # Check for orphaned descriptions
            result = session.run("""
                MATCH (d:Description)
                WHERE NOT (d)<-[:HAS_DESCRIPTION]-()
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                RETURN count(d) as count
            """)
            orphaned = result.single()["count"]
            if orphaned > 0:
                health_info["issues"].append(f"Found {orphaned} orphaned descriptions")
                
            # Check for missing IS_A relationships
            result = session.run("""
                MATCH (c:Concept)-[r:RELATIONSHIP {typeId: '116680003'}]->(d:Concept)
                WHERE NOT (c)-[:IS_A]->(d)
                  AND (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND (r.is_deleted IS NULL OR r.is_deleted = false)
                RETURN count(r) as count
            """)
            missing_is_a = result.single()["count"]
            if missing_is_a > 0:
                health_info["issues"].append(f"Found {missing_is_a} missing IS_A relationships")
                
    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["issues"].append(str(e))
    
    if health_info["issues"]:
        health_info["status"] = "issues_found"
        
    return health_info
