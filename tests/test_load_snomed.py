import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add scripts directory to path so we can import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.load_snomed import find_rf2_files, setup_neo4j_schema


class TestLoadSnomed:
    """Tests for the load_snomed.py script."""
    
    def test_find_rf2_files(self, tmp_path):
        """Test finding RF2 files in a directory structure."""
        # Create a mock SNOMED CT directory structure
        snapshot_dir = tmp_path / "SnomedCT_Release" / "Snapshot"
        snapshot_dir.mkdir(parents=True)
        
        terminology_dir = snapshot_dir / "Terminology"
        terminology_dir.mkdir()
        
        # Create mock RF2 files
        concept_file = terminology_dir / "sct2_Concept_Snapshot_INT_20230131.txt"
        concept_file.write_text("Header line\nContent")
        
        description_file = terminology_dir / "sct2_Description_Snapshot_INT_20230131.txt"
        description_file.write_text("Header line\nContent")
        
        relationship_file = terminology_dir / "sct2_Relationship_Snapshot_INT_20230131.txt"
        relationship_file.write_text("Header line\nContent")
        
        # Test the function
        files = find_rf2_files(str(tmp_path))
        
        # Verify the results
        assert files["concept"] == str(concept_file)
        assert files["description"] == str(description_file)
        assert files["relationship"] == str(relationship_file)
    
    def test_find_rf2_files_missing(self, tmp_path):
        """Test finding RF2 files when some are missing."""
        # Create a mock SNOMED CT directory structure with missing files
        snapshot_dir = tmp_path / "SnomedCT_Release" / "Snapshot"
        snapshot_dir.mkdir(parents=True)
        
        # Test the function with missing files
        with pytest.raises(SystemExit):
            find_rf2_files(str(tmp_path))
    
    def test_setup_neo4j_schema(self, mock_neo4j_driver):
        """Test setting up Neo4j schema."""
        # Setup mock session
        mock_session = mock_neo4j_driver.session.return_value
        
        # Call the function
        setup_neo4j_schema(mock_session)
        
        # Verify that the session.run was called 3 times (for constraints and indexes)
        assert mock_session.run.call_count == 3
