import pytest
import sys
import os

# Add scripts directory to path so we can import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.utils.snomed_utils import (
    get_concept_hierarchy,
    get_relationship_types,
    format_concept_id,
    parse_concept_id
)


class TestSnomedUtils:
    """Tests for the snomed_utils.py module."""
    
    def test_get_concept_hierarchy(self):
        """Test getting concept hierarchy."""
        hierarchy = get_concept_hierarchy()
        
        # Verify some key concepts are present
        assert hierarchy["root"] == "138875005"
        assert hierarchy["clinical_finding"] == "404684003"
        assert hierarchy["procedure"] == "71388002"
        assert len(hierarchy) >= 10  # Should have at least 10 top-level concepts
    
    def test_get_relationship_types(self):
        """Test getting relationship types."""
        relationship_types = get_relationship_types()
        
        # Verify some key relationship types are present
        assert relationship_types["is_a"] == "116680003"
        assert relationship_types["finding_site"] == "363698007"
        assert len(relationship_types) >= 8  # Should have at least 8 relationship types
    
    def test_format_concept_id(self):
        """Test formatting concept IDs."""
        # Test with different length IDs
        assert format_concept_id("123") == "123"
        assert format_concept_id("123456") == "123 456"
        assert format_concept_id("123456789") == "123 456 789"
        
        # Test with empty or None input
        assert format_concept_id("") == ""
        assert format_concept_id(None) == ""
        
        # Test with numeric input
        assert format_concept_id(123456) == "123 456"
    
    def test_parse_concept_id(self):
        """Test parsing formatted concept IDs."""
        # Test with different formatted IDs
        assert parse_concept_id("123 456") == "123456"
        assert parse_concept_id("123 456 789") == "123456789"
        
        # Test with already unformatted ID
        assert parse_concept_id("123456") == "123456"
        
        # Test with empty or None input
        assert parse_concept_id("") == ""
        assert parse_concept_id(None) == ""
