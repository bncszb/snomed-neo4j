import os
import sys
from pathlib import Path

import requests


def get_download_url() -> str:
    """Get release information for the specified edition and version."""
    api_url = "https://uts-ws.nlm.nih.gov/releases?releaseType=snomed-ct-international-edition&current=true"

    response = requests.get(api_url)
    if response.status_code != 200:
        print(f"Failed to get releases: {response.text}")
        sys.exit(1)

    releases = response.json()

    assert len(releases) == 1, "There should be one latest version exactly"

    return releases[0]["downloadUrl"]


def download_snomed_with_api_key(api_key: str, file_url: str, output_dir: Path) -> None:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, os.path.basename(file_url))
    download_url = f"https://uts-ws.nlm.nih.gov/download?url={file_url}&apiKey={api_key}"
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded to {output_path}")
    except Exception as e:
        print(f"Failed to download: {e}")


def download(api_key: str | None = None, output_dir: Path | None = None) -> None:
    api_key = api_key or os.environ["SNOMED_API_KEY"]
    output_dir = output_dir or Path(os.environ["SNOMED_DIR"])

    output_dir.mkdir(parents=True, exist_ok=True)

    url = get_download_url()
    download_snomed_with_api_key(api_key, url, output_dir)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    download()
