#!/usr/bin/env python3
"""
Script to create a slim SNOMED CT database by filtering relationships and hierarchies.
"""

import argparse
import time

from neo4j import GraphDatabase, Record, Session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a slim SNOMED CT database")
    parser.add_argument("--relationships", help="Comma-separated list of relationship type IDs to include")
    parser.add_argument("--hierarchies", help="Comma-separated list of parent concept IDs to include")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--neo4j-user", default="neo4j", help="Neo4j username")
    parser.add_argument("--neo4j-password", default="neo4jneo4j", help="Neo4j password")
    return parser.parse_args()


def filter_by_relationship_types(session: Session, relationship_types: list[str]) -> None:
    """Filter database to keep only specified relationship types."""
    print(f"Filtering relationships to types: {relationship_types}")

    # Delete relationships not in the specified list using APOC for batching
    result = session.run(
        """
        CALL apoc.periodic.iterate(
            "MATCH ()-[r:RELATIONSHIP]->() WHERE NOT r.typeId IN $types RETURN r",
            "DELETE r RETURN count(*)",
            {batchSize: 1000, parallel: false}
        )
        """,
        {"types": relationship_types},
    )

    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    deleted = 1000 * record["batchSize"] + record["failedBatches"] * 1000 + record["failedOperations"]
    print(f"Deleted approximately {deleted} relationships.")


def filter_by_hierarchies(session: Session, parent_ids: list[str]) -> None:
    """Filter database to keep only concepts in specified hierarchies."""
    print(f"Filtering concepts to hierarchies under: {parent_ids}")

    # Mark concepts to keep (those in the specified hierarchies)
    session.run(
        """
        MATCH (c:Concept)
        WHERE c.id IN $parentIds
        SET c.keep = true
    """,
        {"parentIds": parent_ids},
    )

    # Mark all descendants of the specified parents using APOC with batching
    print("Marking descendants to keep (this may take a while)...")
    session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (parent:Concept {keep: true}) RETURN parent",
            "MATCH (parent)<-[:IS_A*1..20]-(descendant:Concept)
             WHERE descendant.keep IS NULL
             SET descendant.keep = true
             RETURN count(*)",
            {batchSize: 100, parallel: false}
        )
    """)

    # Count concepts to delete
    result = session.run("""
        MATCH (c:Concept)
        WHERE c.keep IS NULL
        RETURN count(c) as toDelete
    """)

    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    to_delete = record["toDelete"]
    print(f"Will delete {to_delete} concepts.")

    # Delete relationships to/from concepts that will be deleted using APOC
    print("Deleting relationships (this may take a while)...")
    result = session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (c:Concept)-[r]-(other) WHERE c.keep IS NULL RETURN r",
            "DELETE r RETURN count(*)",
            {batchSize: 1000, parallel: false}
        )
    """)
    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    deleted_rels = record["batches"] * 1000 + record["failedBatches"] * 1000 + record["failedOperations"]
    print(f"Deleted approximately {deleted_rels} relationships.")

    # Delete descriptions of concepts that will be deleted using APOC
    print("Deleting descriptions (this may take a while)...")
    result = session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (c:Concept)-[:HAS_DESCRIPTION]->(d:Description) WHERE c.keep IS NULL RETURN d",
            "DELETE d RETURN count(*)",
            {batchSize: 1000, parallel: false}
        )
    """)
    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    deleted_descs = record["batches"] * 1000 + record["failedBatches"] * 1000 + record["failedOperations"]
    print(f"Deleted approximately {deleted_descs} descriptions.")

    # Delete concepts that are not in the hierarchies using APOC
    print("Deleting concepts (this may take a while)...")
    result = session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (c:Concept) WHERE c.keep IS NULL RETURN c",
            "DELETE c RETURN count(*)",
            {batchSize: 1000, parallel: false}
        )
    """)
    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    deleted_concepts = record["batches"] * 1000 + record["failedBatches"] * 1000 + record["failedOperations"]
    print(f"Deleted approximately {deleted_concepts} concepts.")

    # Delete orphaned descriptions (descriptions with no HAS_DESCRIPTION edges)
    print("Deleting orphaned descriptions...")
    result = session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (d:Description) WHERE NOT (d)<-[:HAS_DESCRIPTION]-() RETURN d",
            "DELETE d RETURN count(*)",
            {batchSize: 1000, parallel: false}
        )
    """)
    record = result.single()
    assert isinstance(record, Record), "None result is not acceptable"
    deleted_orphans = record["batches"] * 1000 + record["failedBatches"] * 1000 + record["failedOperations"]
    print(f"Deleted approximately {deleted_orphans} orphaned descriptions.")

    # Remove the temporary property using APOC
    print("Cleaning up temporary properties...")
    session.run("""
        CALL apoc.periodic.iterate(
            "MATCH (c:Concept) WHERE c.keep IS NOT NULL RETURN c",
            "REMOVE c.keep RETURN count(*)",
            {batchSize: 5000, parallel: false}
        )
    """)


def main() -> None:
    args = parse_args()

    # Connect to Neo4j
    driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password))

    start_time = time.time()

    with driver.session() as session:
        # Filter by relationship types if specified
        if args.relationships:
            relationship_types = [r.strip() for r in args.relationships.split(",")]
            filter_by_relationship_types(session, relationship_types)

        # Filter by hierarchies if specified
        if args.hierarchies:
            parent_ids = [p.strip() for p in args.hierarchies.split(",")]
            filter_by_hierarchies(session, parent_ids)

    end_time = time.time()
    print(f"Slim database creation completed in {end_time - start_time:.2f} seconds.")

    driver.close()


if __name__ == "__main__":
    main()
