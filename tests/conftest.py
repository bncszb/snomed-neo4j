import pytest
from neo4j import GraphDatabase
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    mock_driver = MagicMock(spec=GraphDatabase.driver)
    mock_session = MagicMock()
    mock_driver.session.return_value = mock_session
    
    # Configure the mock session to return a mock transaction
    mock_transaction = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.run.return_value = mock_transaction
    
    return mock_driver


@pytest.fixture
def mock_requests_session():
    """Mock requests session for testing."""
    with patch('requests.Session') as mock_session:
        mock_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.post.return_value = mock_response
        yield mock_instance
