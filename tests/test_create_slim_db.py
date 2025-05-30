import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add scripts directory to path so we can import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.create_slim_db import filter_by_relationship_types, filter_by_hierarchies


class TestCreateSlimDb:
    """Tests for the create_slim_db.py script."""
    
    def test_filter_by_relationship_types(self, mock_neo4j_driver):
        """Test filtering by relationship types."""
        # Setup mock session and result
        mock_session = mock_neo4j_driver.session.return_value
        mock_result = MagicMock()
        mock_record = MagicMock()
        mock_record["deleted"] = 1500
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        # Call the function
        relationship_types = ["116680003", "363698007"]  # IS_A and Finding site
        filter_by_relationship_types(mock_session, relationship_types)
        
        # Verify the query was called with correct parameters
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert call_args[1]["types"] == relationship_types
    
    def test_filter_by_hierarchies(self, mock_neo4j_driver):
        """Test filtering by hierarchies."""
        # Setup mock session and results
        mock_session = mock_neo4j_driver.session.return_value
        
        # Mock results for each query
        mock_results = [
            MagicMock(),  # For marking parent concepts
            MagicMock(),  # For marking descendants
            MagicMock(),  # For counting concepts to delete
            MagicMock(),  # For deleting relationships
            MagicMock(),  # For deleting descriptions
            MagicMock(),  # For deleting concepts
            MagicMock(),  # For removing temporary property
        ]
        
        # Configure the count result
        mock_count_record = MagicMock()
        mock_count_record["toDelete"] = 5000
        mock_results[2].single.return_value = mock_count_record
        
        # Configure the deleted relationships result
        mock_rel_record = MagicMock()
        mock_rel_record["deleted"] = 10000
        mock_results[3].single.return_value = mock_rel_record
        
        # Configure the deleted descriptions result
        mock_desc_record = MagicMock()
        mock_desc_record["deleted"] = 15000
        mock_results[4].single.return_value = mock_desc_record
        
        # Configure the deleted concepts result
        mock_concept_record = MagicMock()
        mock_concept_record["deleted"] = 5000
        mock_results[5].single.return_value = mock_concept_record
        
        # Set up the session.run to return different results for each call
        mock_session.run.side_effect = mock_results
        
        # Call the function
        parent_ids = ["404684003", "71388002"]  # Clinical finding and Procedure
        filter_by_hierarchies(mock_session, parent_ids)
        
        # Verify the first query was called with correct parameters
        assert mock_session.run.call_count == 7
        first_call_args = mock_session.run.call_args_list[0]
        assert first_call_args[1]["parentIds"] == parent_ids
