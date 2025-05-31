#!/usr/bin/env python3
"""
SNOMED CT Neo4j client for Python applications.
"""

from neo4j import GraphDatabase


class SnomedClient:
    """Client for interacting with SNOMED CT data in Neo4j."""
    
    def __init__(self, uri, user, password):
        """Initialize the client with Neo4j connection details."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()
    
    def get_concept(self, concept_id):
        """Get a concept by ID."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Concept {id: $id})
                WHERE c.is_deleted IS NULL OR c.is_deleted = false
                OPTIONAL MATCH (c)-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND d.typeId = '900000000000003001' AND d.active = true
                RETURN c.id as id, c.active as active, d.term as fsn
            """, {"id": concept_id})
            
            record = result.single()
            if record:
                return {
                    "id": record["id"],
                    "active": record["active"],
                    "fsn": record["fsn"]
                }
            return None
    
    def get_preferred_term(self, concept_id, language_code="en"):
        """Get the preferred term for a concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Concept {id: $id})-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND d.typeId = '900000000000013009' AND d.active = true
                  AND d.languageCode = $languageCode
                RETURN d.term as term
            """, {"id": concept_id, "languageCode": language_code})
            
            record = result.single()
            return record["term"] if record else None
    
    def get_children(self, concept_id):
        """Get direct children of a concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (parent:Concept {id: $id})<-[:IS_A]-(child:Concept)
                WHERE (parent.is_deleted IS NULL OR parent.is_deleted = false)
                  AND (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND child.active = true
                RETURN child.id as id
            """, {"id": concept_id})
            
            return [record["id"] for record in result]
    
    def get_parents(self, concept_id):
        """Get direct parents of a concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (child:Concept {id: $id})-[:IS_A]->(parent:Concept)
                WHERE (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND (parent.is_deleted IS NULL OR parent.is_deleted = false)
                  AND parent.active = true
                RETURN parent.id as id
            """, {"id": concept_id})
            
            return [record["id"] for record in result]
    
    def get_ancestors(self, concept_id):
        """Get all ancestors of a concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (child:Concept {id: $id})-[:IS_A*]->(ancestor:Concept)
                WHERE (child.is_deleted IS NULL OR child.is_deleted = false)
                  AND (ancestor.is_deleted IS NULL OR ancestor.is_deleted = false)
                  AND ancestor.active = true
                RETURN DISTINCT ancestor.id as id
            """, {"id": concept_id})
            
            return [record["id"] for record in result]
    
    def get_descendants(self, concept_id):
        """Get all descendants of a concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ancestor:Concept {id: $id})<-[:IS_A*]-(descendant:Concept)
                WHERE (ancestor.is_deleted IS NULL OR ancestor.is_deleted = false)
                  AND (descendant.is_deleted IS NULL OR descendant.is_deleted = false)
                  AND descendant.active = true
                RETURN DISTINCT descendant.id as id
            """, {"id": concept_id})
            
            return [record["id"] for record in result]
    
    def is_a(self, source_id, target_id):
        """Check if source concept is a subtype of target concept."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (source:Concept {id: $sourceId})
                MATCH (target:Concept {id: $targetId})
                WHERE (source.is_deleted IS NULL OR source.is_deleted = false)
                  AND (target.is_deleted IS NULL OR target.is_deleted = false)
                RETURN (source)-[:IS_A*]->(target) as isA
            """, {"sourceId": source_id, "targetId": target_id})
            
            record = result.single()
            return record and record["isA"]
    
    def find_concepts(self, term, limit=10):
        """Find concepts by term."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Concept)-[:HAS_DESCRIPTION]->(d:Description)
                WHERE (c.is_deleted IS NULL OR c.is_deleted = false)
                  AND (d.is_deleted IS NULL OR d.is_deleted = false)
                  AND d.term CONTAINS $term AND c.active = true AND d.active = true
                RETURN DISTINCT c.id as id, d.term as matchedTerm
                LIMIT $limit
            """, {"term": term, "limit": limit})
            
            return [{"id": record["id"], "term": record["matchedTerm"]} for record in result]
    
    def get_relationships(self, concept_id, relationship_type_id=None):
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


# Example usage
if __name__ == "__main__":
    # Example connection to a local Neo4j instance
    client = SnomedClient("bolt://localhost:7687", "neo4j", "password")
    
    try:
        # Example: Get information about "Clinical finding" concept
        concept = client.get_concept("404684003")
        print(f"Concept: {concept}")
        
        # Example: Get children of "Clinical finding"
        children = client.get_children("404684003")
        print(f"Children count: {len(children)}")
        
        # Example: Find concepts containing "diabetes"
        diabetes_concepts = client.find_concepts("diabetes")
        for concept in diabetes_concepts:
            print(f"Found: {concept['id']} - {concept['term']}")
    
    finally:
        client.close()
