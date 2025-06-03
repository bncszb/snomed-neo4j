#!/usr/bin/env python3
"""
Script to create a slim SNOMED CT database by filtering relationships and hierarchies.
Improved version with better error handling, progress tracking, and performance optimizations.
"""

import logging
import os
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, LiteralString

from neo4j import Driver, Session
from neo4j.exceptions import Neo4jError
from snomed_neo4j_core.client import get_driver
from snomed_neo4j_core.utils import optional_env_int


class SNOMEDSlimmer:
    """Main class for SNOMED CT database slimming operations."""

    def __init__(self, batch_size: int = 1000, max_depth: int = 20) -> None:
        self.batch_size = batch_size
        self.max_depth = max_depth
        self.logger = logging.getLogger(__name__)
        self._driver: Driver | None = None

    @contextmanager
    def get_driver(self) -> Generator:
        """Context manager for Neo4j driver connection."""
        try:
            self._driver = get_driver()
            # Test connection
            self._driver.verify_connectivity()
            self.logger.info("Successfully connected to Neo4j")
            yield self._driver
        except Neo4jError as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise
        finally:
            if self._driver:
                self._driver.close()
                self.logger.info("Neo4j connection closed")

    def execute_batched_operation(self, session: Session, match_query: str, action_query: str, parameters: dict[str, Any] | None = None) -> int:
        """Execute a batched operation using APOC and return the count of affected items."""
        try:
            result = session.run(
                """
                CALL apoc.periodic.iterate(
                    $match_query,
                    $action_query,
                    {batchSize: $batch_size, parallel: false, retries: 3}
                )
                """,
                {"match_query": match_query, "action_query": action_query, "batch_size": self.batch_size, **(parameters or {})},
            )

            record = result.single()
            if not record:
                self.logger.warning("No result returned from batched operation")
                return 0

            # Calculate total affected items
            total = record.get("batches", 0) * self.batch_size
            total += record.get("failedBatches", 0) * self.batch_size
            total += record.get("failedOperations", 0)

            if record.get("errorMessages"):
                self.logger.warning(f"Operation had errors: {record['errorMessages']}")

            return total

        except Neo4jError as e:
            self.logger.error(f"Error executing batched operation: {e}")
            raise

    def get_count(self, session: Session, query: LiteralString, parameters: dict[str, Any] | None = None) -> int:
        """Get count from a query safely."""
        try:
            # assert isinstance(query, LiteralString)
            result = session.run(query, parameters or {})
            record = result.single()
            return record[0] if record else 0
        except Neo4jError as e:
            self.logger.error(f"Error getting count: {e}")
            return 0

    def filter_by_relationship_types(self, session: Session, relationship_types: list[str], soft_delete: bool = False, dry_run: bool = False) -> None:
        """Filter database to keep only specified relationship types."""
        self.logger.info(f"Filtering relationships to types: {relationship_types}")

        # Count relationships to be affected
        count_query = """
            MATCH ()-[r:RELATIONSHIP]->()
            WHERE NOT r.typeId IN $types
            RETURN count(r) as count
        """

        to_affect = self.get_count(session, count_query, {"types": relationship_types})
        self.logger.info(f"Found {to_affect} relationships to {'mark as deleted' if soft_delete else 'delete'}")

        if dry_run:
            self.logger.info("DRY RUN: Would affect the above relationships")
            return

        if to_affect == 0:
            self.logger.info("No relationships to process")
            return

        if soft_delete:
            action_query = "SET r.is_deleted = true RETURN count(*)"
            self.logger.info("Marking relationships as deleted...")
        else:
            action_query = "DELETE r RETURN count(*)"
            self.logger.info("Deleting relationships...")

        try:
            result = session.run(
                """
                CALL apoc.periodic.iterate(
                    "MATCH ()-[r:RELATIONSHIP]->() WHERE NOT r.typeId IN $types RETURN r",
                    $action_query,
                    {batchSize: $batch_size, parallel: false, retries: 3, params: {types: $types}}
                )
                """,
                {
                    "types": relationship_types,
                    "action_query": action_query,
                    "batch_size": self.batch_size,
                },
            )
            record = result.single()

            if not record:
                affected = 0
            else:
                # Calculate total affected items
                total = record.get("batches", 0) * self.batch_size
                total += record.get("failedBatches", 0) * self.batch_size
                total += record.get("failedOperations", 0)

                if record.get("errorMessages"):
                    self.logger.warning(f"Operation had errors: {record['errorMessages']}")

                affected = total

        except Neo4jError as e:
            self.logger.error(f"Error executing batched operation: {e}")
            raise
        action_word = "marked" if soft_delete else "deleted"
        self.logger.info(f"Successfully {action_word} {affected} relationships")

    def filter_by_hierarchies(self, session: Session, parent_ids: list[str], soft_delete: bool = False, dry_run: bool = False) -> None:
        """Filter database to keep only concepts in specified hierarchies."""
        self.logger.info(f"Filtering concepts to hierarchies under: {parent_ids}")

        try:
            # Validate that parent concepts exist
            existing_parents = session.run("MATCH (c:Concept) WHERE c.id IN $parentIds RETURN c.id as id", {"parentIds": parent_ids}).data()

            existing_ids = [record["id"] for record in existing_parents]
            missing_ids = set(parent_ids) - set(existing_ids)

            if missing_ids:
                self.logger.warning(f"Parent concepts not found: {missing_ids}")

            if not existing_ids:
                self.logger.error("None of the specified parent concepts exist in the database")
                return

            self.logger.info(f"Using existing parent concepts: {existing_ids}")

            # Clear any existing keep flags
            session.run("MATCH (c:Concept) WHERE c.keep IS NOT NULL REMOVE c.keep")

            # Mark parent concepts to keep
            session.run("MATCH (c:Concept) WHERE c.id IN $parentIds SET c.keep = true", {"parentIds": existing_ids})
            self.logger.info(f"Marked {len(existing_ids)} parent concepts to keep")

            # Mark descendants in batches to avoid memory issues
            self.logger.info("Marking descendants to keep (this may take a while)...")

            descendants_marked = self.execute_batched_operation(
                session,
                "MATCH (parent:Concept {keep: true}) RETURN parent",
                f"""MATCH (parent)<-[:IS_A*1..{self.max_depth}]-(descendant:Concept)
                   WHERE descendant.keep IS NULL
                   SET descendant.keep = true
                   RETURN count(*)""",
            )

            self.logger.info(f"Marked {descendants_marked} descendants to keep")

            # Count concepts to be affected
            to_delete = self.get_count(session, "MATCH (c:Concept) WHERE c.keep IS NULL RETURN count(c)")
            total_concepts = self.get_count(session, "MATCH (c:Concept) RETURN count(c)")
            to_keep = total_concepts - to_delete

            self.logger.info(f"Concepts summary: {total_concepts} total, {to_keep} to keep, {to_delete} to remove")

            if dry_run:
                self.logger.info("DRY RUN: Would affect the above concepts and their relationships/descriptions")
                return

            if to_delete == 0:
                self.logger.info("No concepts to process")
                return

            # Process concepts, relationships, and descriptions
            self._process_hierarchy_deletions(session, soft_delete)

        finally:
            # Always clean up temporary properties
            self.logger.info("Cleaning up temporary properties...")
            session.run(
                """
                CALL apoc.periodic.iterate(
                    "MATCH (c:Concept) WHERE c.keep IS NOT NULL RETURN c",
                    "REMOVE c.keep RETURN count(*)",
                    {batchSize: $batch_size, parallel: false}
                )
            """,
                {"batch_size": self.batch_size},
            )

    def _process_hierarchy_deletions(self, session: Session, soft_delete: bool) -> None:
        """Process the actual deletions/markings for hierarchy filtering."""
        action_word = "Marking" if soft_delete else "Deleting"
        action_suffix = "is_deleted = true" if soft_delete else ""

        # Process relationships
        self.logger.info(f"{action_word} relationships...")
        match_query = "MATCH (c:Concept)-[r]-(other) WHERE c.keep IS NULL RETURN r"
        action_query = f"SET r.{action_suffix} RETURN count(*)" if soft_delete else "DELETE r RETURN count(*)"

        affected_rels = self.execute_batched_operation(session, match_query, action_query)
        self.logger.info(f"Processed {affected_rels} relationships")

        # Process descriptions
        self.logger.info(f"{action_word} descriptions...")
        match_query = "MATCH (c:Concept)-[:HAS_DESCRIPTION]->(d:Description) WHERE c.keep IS NULL RETURN d"
        action_query = f"SET d.{action_suffix} RETURN count(*)" if soft_delete else "DELETE d RETURN count(*)"

        affected_descs = self.execute_batched_operation(session, match_query, action_query)
        self.logger.info(f"Processed {affected_descs} descriptions")

        # Process concepts
        self.logger.info(f"{action_word} concepts...")
        match_query = "MATCH (c:Concept) WHERE c.keep IS NULL RETURN c"
        action_query = f"SET c.{action_suffix} RETURN count(*)" if soft_delete else "DELETE c RETURN count(*)"

        affected_concepts = self.execute_batched_operation(session, match_query, action_query)
        self.logger.info(f"Processed {affected_concepts} concepts")

        # Handle orphaned descriptions
        self.logger.info(f"{action_word} orphaned descriptions...")
        match_query = "MATCH (d:Description) WHERE NOT (d)<-[:HAS_DESCRIPTION]-() RETURN d"
        action_query = f"SET d.{action_suffix} RETURN count(*)" if soft_delete else "DELETE d RETURN count(*)"

        orphaned_descs = self.execute_batched_operation(session, match_query, action_query)
        self.logger.info(f"Processed {orphaned_descs} orphaned descriptions")

    def reset_soft_deletions(self, session: Session) -> None:
        self.logger.info("Resetting is deleted fields")
        match_query = "MATCH (c:Concept) RETURN c"
        action_query = "SET c.is_deleted = false RETURN count(*)"
        self.execute_batched_operation(session, match_query, action_query)

        match_query = "MATCH ()-[r:RELATIONSHIP]-() RETURN r"
        action_query = "SET r.is_deleted = false RETURN count(*)"
        self.execute_batched_operation(session, match_query, action_query)


def slim(
    relationships: str,
    hierarchies: str,
    soft_delete: bool,
    dry_run: bool,
    batch_size: int,
    max_depth: int,
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting SNOMED CT database slimming process")

    if not hierarchies and not relationships:
        logger.warning("No slimming strategy given. Returning without change.")
        return

    # Parse input parameters
    relationship_types = None
    if relationships:
        relationship_types = [r.strip() for r in relationships.split(",") if r.strip()]
        logger.info(f"Relationship types to keep: {relationship_types}")

    parent_ids = None
    if hierarchies:
        parent_ids = [p.strip() for p in hierarchies.split(",") if p.strip()]
        logger.info(f"Hierarchy parents to keep: {parent_ids}")

    deletion_mode = "soft" if soft_delete else "hard"
    logger.info(f"Using {deletion_mode} deletion mode")

    if dry_run:
        logger.info("DRY RUN MODE: No actual changes will be made")

    # Initialize slimmer
    slimmer = SNOMEDSlimmer(batch_size=batch_size, max_depth=max_depth)

    start_time = time.time()

    try:
        with slimmer.get_driver() as driver:
            with driver.session() as session:
                if soft_delete:
                    slimmer.reset_soft_deletions(session)

                # Filter by relationship types if specified
                if relationship_types:
                    slimmer.filter_by_relationship_types(session, relationship_types, soft_delete, dry_run)

                # Filter by hierarchies if specified
                if parent_ids:
                    slimmer.filter_by_hierarchies(session, parent_ids, soft_delete, dry_run)

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Slimming process completed successfully in {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Slimming process failed: {e}")
        sys.exit(1)


def main() -> None:
    from dotenv import load_dotenv
    from snomed_neo4j_core.logging import setup_logging
    from snomed_neo4j_core.utils import env_bool

    load_dotenv()
    setup_logging()

    relationships = os.environ["SNOMED_SLIM_RELATIONSHIPS"]
    hierarchies = os.environ["SNOMED_SLIM_HIERARCHIES"]
    soft_delete = env_bool("SNOMED_SLIM_SOFT_DELETE")
    dry_run = env_bool("SNOMED_SLIM_DRY_RUN")
    batch_size = optional_env_int("SNOMED_IMPORT_BATCH") or 1000
    max_depth = optional_env_int("SNOMED_SLIM_MAX_DEPTH") or 20

    slim(
        relationships,
        hierarchies,
        soft_delete,
        dry_run,
        batch_size,
        max_depth,
    )
