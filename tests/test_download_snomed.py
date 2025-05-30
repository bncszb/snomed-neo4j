import pytest
import tempfile
from unittest.mock import MagicMock, patch
import os
import sys
import zipfile
from pathlib import Path

# Add scripts directory to path so we can import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.download_snomed import authenticate, get_release_info, download_release


class TestDownloadSnomed:
    """Tests for the download_snomed.py script."""
    
    def test_authenticate_success(self):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test-token"}
        
        with patch('requests.post', return_value=mock_response):
            token = authenticate("test-key", "test-secret")
            assert token == "test-token"
    
    def test_authenticate_failure(self):
        """Test authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(SystemExit):
                authenticate("invalid-key", "invalid-secret")
    
    def test_get_release_info_latest(self):
        """Test getting latest release info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "edition": "international",
                "version": "20230131",
                "effectiveTime": "20230131",
                "rf2DistributionUrl": "https://example.com/snomed.zip"
            },
            {
                "edition": "international",
                "version": "20220731",
                "effectiveTime": "20220731",
                "rf2DistributionUrl": "https://example.com/snomed-old.zip"
            }
        ]
        
        with patch('requests.get', return_value=mock_response):
            release = get_release_info("test-token", "international", "latest")
            assert release["version"] == "20230131"
            assert release["rf2DistributionUrl"] == "https://example.com/snomed.zip"
    
    def test_get_release_info_specific_version(self):
        """Test getting specific version release info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "edition": "international",
                "version": "20230131",
                "effectiveTime": "20230131",
                "rf2DistributionUrl": "https://example.com/snomed.zip"
            },
            {
                "edition": "international",
                "version": "20220731",
                "effectiveTime": "20220731",
                "rf2DistributionUrl": "https://example.com/snomed-old.zip"
            }
        ]
        
        with patch('requests.get', return_value=mock_response):
            release = get_release_info("test-token", "international", "20220731")
            assert release["version"] == "20220731"
            assert release["rf2DistributionUrl"] == "https://example.com/snomed-old.zip"
    
    def test_download_release(self, tmp_path):
        """Test downloading a release."""
        # Create a test zip file
        test_zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(test_zip_path, 'w') as test_zip:
            test_zip.writestr('test.txt', 'Test content')
        
        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers.get.return_value = str(os.path.getsize(test_zip_path))
        
        # Mock the response content to return the test zip file content
        with open(test_zip_path, 'rb') as f:
            mock_response.iter_content.return_value = [f.read()]
        
        # Create a temporary output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock the release info
        release = {
            "edition": "international",
            "version": "20230131",
            "rf2DistributionUrl": "https://example.com/snomed.zip"
        }
        
        # Test the download_release function
        with patch('requests.get', return_value=mock_response):
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                # Configure the mock temporary file
                mock_temp_instance = MagicMock()
                mock_temp.return_value.__enter__.return_value = mock_temp_instance
                mock_temp_instance.name = str(test_zip_path)
                
                # Call the function
                download_release("test-token", release, str(output_dir))
                
                # Check that the file was extracted
                assert (output_dir / "test.txt").exists()
                assert (output_dir / "test.txt").read_text() == "Test content"
