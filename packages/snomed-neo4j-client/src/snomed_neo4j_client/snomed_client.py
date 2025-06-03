"""
SNOMED CT Neo4j Client

A Python client for interacting with SNOMED CT data stored in a Neo4j database.
"""

from neo4j import GraphDatabase
from snomed_neo4j_core.models import Concept, ConceptWithDetails, Description, DescriptionTypeEnum, Relationship


class SnomedClient:
    """Client for interacting with SNOMED CT data in Neo4j."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        """Initialize the client with Neo4j connection details."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        """Close the Neo4j driver."""
        self.driver.close()

    def get_concept(self, concept_id: str) -> Concept | None:
        """Get a concept by ID."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept {id: $id})
                WHERE c.is_deleted IS NULL OR c.is_deleted = false
                RETURN properties(c) as concept
            """,
                {"id": concept_id},
            )

            record = result.single()
            if record:
                return Concept(**record["concept"])

            return None

    def get_concept_with_details(self, concept_id: str) -> ConceptWithDetails | None:
        """Get a concept with its descriptions and relationships."""
        concept = self.get_concept(concept_id)
        if not concept:
            return None

        # Create ConceptWithDetails from the base concept
        concept_with_details = ConceptWithDetails.from_concept(concept)

        # Add descriptions
        with self.driver.session() as session:
            desc_result = session.run(
                """
                MATCH (c:Concept {id: $id})-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (d.is_deleted IS NULL OR d.is_deleted = false)
                RETURN properties(d) as description
                """,
                {"id": concept_id},
            )

            for record in desc_result:
                concept_with_details.descriptions.append(Description(**record["description"]))

        # Add outgoing relationships
        with self.driver.session() as session:
            rel_result = session.run(
                """
                MATCH (:Concept {id: $id})<-[r:RELATIONSHIP]-(:Concept)
                WHERE (r.is_deleted IS NULL OR r.is_deleted = false)
                RETURN properties(r) as relationship
                """,
                {"id": concept_id},
            )

            for record in rel_result:
                concept_with_details.relationships.append(Relationship(**record["relationship"]))

        # Add incoming relationships
        with self.driver.session() as session:
            parent_rel_result = session.run(
                """
                MATCH (:Concept)<-[r:RELATIONSHIP]-(:Concept {id: $id})
                WHERE (r.is_deleted IS NULL OR r.is_deleted = false)
                RETURN properties(r) as relationship
                """,
                {"id": concept_id},
            )

            for record in parent_rel_result:
                concept_with_details.parent_relationships.append(Relationship(**record["relationship"]))

        return concept_with_details

    def get_preferred_term(self, concept_id: str, language_code: str = "en") -> str | None:
        """Get the preferred term for a concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept {id: $id})-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND d.typeId = $typeId AND d.active = true
                  AND d.languageCode = $languageCode
                RETURN d.term as term
            """,
                {"id": concept_id, "languageCode": language_code, "typeId": DescriptionTypeEnum.SYNONYM},
            )

            record = result.single()
            return record["term"] if record else None

    def get_children(self, concept_id: str) -> list[str]:
        """Get direct children of a concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (parent:Concept {id: $id})<-[:IS_A]-(child:Concept)
                WHERE (parent.is_deleted IS NULL OR parent.is_deleted = false)
                  AND (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND child.active = true
                RETURN child.id as id
            """,
                {"id": concept_id},
            )

            return [record["id"] for record in result]

    def get_parents(self, concept_id: str) -> list[str]:
        """Get direct parents of a concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (child:Concept {id: $id})-[:IS_A]->(parent:Concept)
                WHERE (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND (parent.is_deleted IS NULL OR parent.is_deleted = false)
                  AND parent.active = true
                RETURN parent.id as id
            """,
                {"id": concept_id},
            )

            return [record["id"] for record in result]

    def get_ancestors(self, concept_id: str) -> list[str]:
        """Get all ancestors of a concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (child:Concept {id: $id})-[:IS_A*]->(ancestor:Concept)
                WHERE (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND (ancestor.is_deleted IS NULL OR ancestor.is_deleted = false)
                  AND ancestor.active = true
                RETURN DISTINCT ancestor.id as id
            """,
                {"id": concept_id},
            )

            return [record["id"] for record in result]

    def get_descendants(self, concept_id: str) -> list[str]:
        """Get all descendants of a concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (ancestor:Concept {id: $id})<-[:IS_A*]-(descendant:Concept)
                WHERE (ancestor.is_deleted IS NULL OR ancestor.is_deleted = false)
                  AND (descendant.is_deleted IS NULL OR descendant.is_deleted = false)
                  AND descendant.active = true
                RETURN DISTINCT descendant.id as id
            """,
                {"id": concept_id},
            )

            return [record["id"] for record in result]

    def is_a(self, source_id: str, target_id: str) -> bool:
        """Check if source concept is a subtype of target concept."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (source:Concept {id: $sourceId})
                MATCH (target:Concept {id: $targetId})
                WHERE (source.is_deleted IS NULL OR source.is_deleted = false)
                  AND (target.is_deleted IS NULL OR target.is_deleted = false)
                RETURN (source)-[:IS_A*]->(target) as isA
            """,
                {"sourceId": source_id, "targetId": target_id},
            )

            record = result.single()
            return bool(record and record["isA"])

    def find_concepts(self, term: str, limit: int = 10) -> list[dict[str, str]]:
        """Find concepts by term."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept)-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND d.term CONTAINS $term AND c.active = true AND d.active = true
                RETURN DISTINCT c.id as id, d.term as matchedTerm
                LIMIT $limit
            """,
                {"term": term, "limit": limit},
            )

            return [{"id": record["id"], "term": record["matchedTerm"]} for record in result]

    def get_relationships(self, concept_id: str, relationship_type_id: str | None = None) -> list[dict[str, str]]:
        """Get relationships for a concept."""
        with self.driver.session() as session:
            params = {"id": concept_id}
            query = """
                MATCH (c:Concept {id: $id})-[r:RELATIONSHIP]->(target:Concept)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (target.is_deleted IS NULL OR target.is_deleted = false)
                  AND (r.is_deleted IS NULL OR r.is_deleted = false)
                  AND c.active = true AND target.active = true
            """

            if relationship_type_id:
                query += " AND r.typeId = $typeId"
                params["typeId"] = relationship_type_id

            query += """
                RETURN r.typeId as typeId, target.id as targetId
            """

            result = session.run(query, params)

            return [{"typeId": record["typeId"], "targetId": record["targetId"]} for record in result]

    def get_relationships_as_models(self, concept_id: str, relationship_type_id: str | None = None) -> list[Relationship]:
        """Get relationships for a concept as Relationship models."""
        with self.driver.session() as session:
            params = {"id": concept_id}
            query = """
                MATCH (c:Concept {id: $id})-[r:RELATIONSHIP]->(target:Concept)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (target.is_deleted IS NULL OR target.is_deleted = false)
                  AND (r.is_deleted IS NULL OR r.is_deleted = false)
                  AND c.active = true AND target.active = true
            """

            if relationship_type_id:
                query += " AND r.typeId = $typeId"
                params["typeId"] = relationship_type_id

            query += """
                RETURN properties(r) as relationship
            """

            result = session.run(query, params)
            return [Relationship(**record["relationship"]) for record in result]


if __name__ == "__main__":
    # Example usage
    concept_id = "138875005"  # SNOMED CT root concept

    client = SnomedClient("bolt://localhost:7687", "neo4j", "password")
    try:
        concept = client.get_concept(concept_id)
        print(f"Concept:\n{concept}\n")

        preferred_term = client.get_preferred_term(concept_id)
        print(f"Preferred term: {preferred_term}\n")

        children = client.get_children(concept_id)
        print(f"Children count: {len(children)}\n")
    finally:
        client.close()
