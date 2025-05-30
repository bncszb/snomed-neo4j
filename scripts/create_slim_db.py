#!/usr/bin/env python3
"""
Script to create a slim SNOMED CT database by filtering relationships and hierarchies.
"""

import argparse
import time
from neo4j import GraphDatabase


def parse_args():
    parser = argparse.ArgumentParser(description='Create a slim SNOMED CT database')
    parser.add_argument('--relationships', help='Comma-separated list of relationship type IDs to include')
    parser.add_argument('--hierarchies', help='Comma-separated list of parent concept IDs to include')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--neo4j-user', default='neo4j', help='Neo4j username')
    parser.add_argument('--neo4j-password', default='neo4j', help='Neo4j password')
    return parser.parse_args()


def filter_by_relationship_types(session, relationship_types):
    """Filter database to keep only specified relationship types."""
    print(f"Filtering relationships to types: {relationship_types}")
    
    # Delete relationships not in the specified list
    result = session.run("""
        MATCH ()-[r:RELATIONSHIP]->()
        WHERE NOT r.typeId IN $types
        DELETE r
        RETURN count(r) as deleted
    """, {"types": relationship_types})
    
    deleted = result.single()["deleted"]
    print(f"Deleted {deleted} relationships.")


def filter_by_hierarchies(session, parent_ids):
    """Filter database to keep only concepts in specified hierarchies."""
    print(f"Filtering concepts to hierarchies under: {parent_ids}")
    
    # Mark concepts to keep (those in the specified hierarchies)
    session.run("""
        MATCH (c:Concept)
        WHERE c.id IN $parentIds
        SET c.keep = true
    """, {"parentIds": parent_ids})
    
    # Mark all descendants of the specified parents
    session.run("""
        MATCH (parent:Concept {keep: true})<-[:IS_A*]-(descendant:Concept)
        SET descendant.keep = true
    """)
    
    # Count concepts to delete
    result = session.run("""
        MATCH (c:Concept)
        WHERE c.keep IS NULL
        RETURN count(c) as toDelete
    """)
    
    to_delete = result.single()["toDelete"]
    print(f"Will delete {to_delete} concepts.")
    
    # Delete relationships to/from concepts that will be deleted
    result = session.run("""
        MATCH (c:Concept)-[r]-(other)
        WHERE c.keep IS NULL
        DELETE r
        RETURN count(r) as deleted
    """)
    
    deleted_rels = result.single()["deleted"]
    print(f"Deleted {deleted_rels} relationships.")
    
    # Delete descriptions of concepts that will be deleted
    result = session.run("""
        MATCH (c:Concept)-[:HAS_DESCRIPTION]->(d:Description)
        WHERE c.keep IS NULL
        DELETE d
        RETURN count(d) as deleted
    """)
    
    deleted_descs = result.single()["deleted"]
    print(f"Deleted {deleted_descs} descriptions.")
    
    # Delete concepts that are not in the hierarchies
    result = session.run("""
        MATCH (c:Concept)
        WHERE c.keep IS NULL
        DELETE c
        RETURN count(c) as deleted
    """)
    
    deleted_concepts = result.single()["deleted"]
    print(f"Deleted {deleted_concepts} concepts.")
    
    # Remove the temporary property
    session.run("""
        MATCH (c:Concept)
        REMOVE c.keep
    """)


def main():
    args = parse_args()
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password)
    )
    
    start_time = time.time()
    
    with driver.session() as session:
        # Filter by relationship types if specified
        if args.relationships:
            relationship_types = [r.strip() for r in args.relationships.split(',')]
            filter_by_relationship_types(session, relationship_types)
        
        # Filter by hierarchies if specified
        if args.hierarchies:
            parent_ids = [p.strip() for p in args.hierarchies.split(',')]
            filter_by_hierarchies(session, parent_ids)
    
    end_time = time.time()
    print(f"Slim database creation completed in {end_time - start_time:.2f} seconds.")
    
    driver.close()


if __name__ == "__main__":
    main()
