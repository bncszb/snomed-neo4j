import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add scripts directory to path so we can import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.utils.neo4j_utils import (
    get_neo4j_connection,
    execute_query,
    create_index,
    create_constraint,
    get_database_statistics
)


class TestNeo4jUtils:
    """Tests for the neo4j_utils.py module."""
    
    def test_get_neo4j_connection(self):
        """Test creating a Neo4j connection."""
        with patch('neo4j.GraphDatabase.driver') as mock_driver:
            connection = get_neo4j_connection("bolt://localhost:7687", "neo4j", "password")
            mock_driver.assert_called_once_with("bolt://localhost:7687", auth=("neo4j", "password"))
    
    def test_execute_query(self, mock_neo4j_driver):
        """Test executing a Cypher query."""
        # Setup mock session and result
        mock_session = mock_neo4j_driver.session.return_value
        mock_result = [{"name": "test1"}, {"name": "test2"}]
        mock_session.__enter__.return_value.run.return_value = mock_result
        
        # Call the function
        result = execute_query(mock_neo4j_driver, "MATCH (n) RETURN n.name as name", {"param": "value"})
        
        # Verify the result
        assert result == mock_result
        
        # Verify the query was called with correct parameters
        mock_session.__enter__.return_value.run.assert_called_once_with(
            "MATCH (n) RETURN n.name as name", {"param": "value"}
        )
    
    def test_create_index(self, mock_neo4j_driver):
        """Test creating an index."""
        # Setup mock session
        mock_session = mock_neo4j_driver.session.return_value
        
        # Call the function
        create_index(mock_neo4j_driver, "Concept", "id")
        
        # Verify the query was called correctly
        mock_session.run.assert_called_once_with(
            "CREATE INDEX IF NOT EXISTS FOR (n:Concept) ON (n.id)"
        )
    
    def test_create_constraint(self, mock_neo4j_driver):
        """Test creating a constraint."""
        # Setup mock session
        mock_session = mock_neo4j_driver.session.return_value
        
        # Call the function
        create_constraint(mock_neo4j_driver, "Concept", "id")
        
        # Verify the query was called correctly
        mock_session.run.assert_called_once_with(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE"
        )
    
    def test_get_database_statistics(self, mock_neo4j_driver):
        """Test getting database statistics."""
        # Setup mock session and results
        mock_session = mock_neo4j_driver.session.return_value
        
        # Mock results for labels query
        mock_labels_result = [
            MagicMock(label="Concept"),
            MagicMock(label="Description")
        ]
        mock_labels_result[0]["label"] = "Concept"
        mock_labels_result[1]["label"] = "Description"
        
        # Mock results for relationship types query
        mock_rel_types_result = [
            MagicMock(relationshipType="RELATIONSHIP"),
            MagicMock(relationshipType="HAS_DESCRIPTION")
        ]
        mock_rel_types_result[0]["relationshipType"] = "RELATIONSHIP"
        mock_rel_types_result[1]["relationshipType"] = "HAS_DESCRIPTION"
        
        # Mock count results
        mock_concept_count = MagicMock()
        mock_concept_count["count"] = 500000
        
        mock_description_count = MagicMock()
        mock_description_count["count"] = 1500000
        
        mock_relationship_count = MagicMock()
        mock_relationship_count["count"] = 2000000
        
        mock_has_description_count = MagicMock()
        mock_has_description_count["count"] = 1500000
        
        # Configure the session.run to return different results for each call
        mock_session.run.side_effect = [
            mock_labels_result,
            MagicMock(single=lambda: mock_concept_count),
            MagicMock(single=lambda: mock_description_count),
            mock_rel_types_result,
            MagicMock(single=lambda: mock_relationship_count),
            MagicMock(single=lambda: mock_has_description_count)
        ]
        
        # Call the function
        stats = get_database_statistics(mock_neo4j_driver)
        
        # Verify the results
        assert stats["Concept_count"] == 500000
        assert stats["Description_count"] == 1500000
        assert stats["RELATIONSHIP_count"] == 2000000
        assert stats["HAS_DESCRIPTION_count"] == 1500000
