#!/usr/bin/env python3
"""
Script to download SNOMED CT data using SNOMED International API.
"""

import os
import sys
import argparse
import requests
import zipfile
import tempfile
from tqdm import tqdm
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Download SNOMED CT data')
    parser.add_argument('--api-key', required=True, help='SNOMED API key')
    parser.add_argument('--api-secret', required=True, help='SNOMED API secret')
    parser.add_argument('--edition', default='international', help='SNOMED edition')
    parser.add_argument('--version', default='latest', help='SNOMED version')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    return parser.parse_args()


def authenticate(api_key, api_secret):
    """Authenticate with SNOMED API and get access token."""
    auth_url = "https://ims.snomed.org/oauth2/token"
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": api_secret
    }
    
    response = requests.post(auth_url, data=auth_data)
    if response.status_code != 200:
        print(f"Authentication failed: {response.text}")
        sys.exit(1)
    
    return response.json()["access_token"]


def get_release_info(token, edition, version):
    """Get release information for the specified edition and version."""
    api_url = "https://api.snomed.org/v1/releases"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to get releases: {response.text}")
        sys.exit(1)
    
    releases = response.json()
    
    # Filter by edition
    edition_releases = [r for r in releases if r["edition"] == edition]
    if not edition_releases:
        print(f"No releases found for edition: {edition}")
        sys.exit(1)
    
    # Get specific version or latest
    if version == "latest":
        # Sort by date and get the latest
        release = sorted(edition_releases, key=lambda x: x["effectiveTime"], reverse=True)[0]
    else:
        release = next((r for r in edition_releases if r["version"] == version), None)
        if not release:
            print(f"Version {version} not found for edition {edition}")
            sys.exit(1)
    
    return release


def download_release(token, release, output_dir):
    """Download the release file."""
    download_url = release["rf2DistributionUrl"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Downloading SNOMED CT {release['edition']} {release['version']}...")
    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        response = requests.get(download_url, headers=headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with tqdm(total=total_size, unit='B', unit_scale=True) as progress_bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    progress_bar.update(len(chunk))
    
    # Extract the downloaded file
    print(f"Extracting files to {output_dir}...")
    with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    
    # Clean up the temporary file
    os.unlink(temp_file.name)
    print("Download and extraction complete.")


def main():
    args = parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Authenticate
    token = authenticate(args.api_key, args.api_secret)
    
    # Get release information
    release = get_release_info(token, args.edition, args.version)
    
    # Download the release
    download_release(token, release, args.output_dir)


if __name__ == "__main__":
    main()
