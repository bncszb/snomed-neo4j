#!/usr/bin/env python3
"""
SNOMED CT Data Import Script
Converts the bash script to Python for better cross-platform compatibility
"""

import logging
import os
import sys
import time
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv
from snomed_neo4j_core.client import get_driver, get_neo4j_http_uri
from snomed_neo4j_core.download import main as download_main
from snomed_neo4j_core.loader import main as load_main
from snomed_neo4j_core.logging import setup_logging
from snomed_neo4j_core.slim import main as slim_main

load_dotenv()
setup_logging()


def check_neo4j_data() -> int:
    """Check if Neo4j has data by counting nodes"""
    try:
        driver = get_driver()

        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS nodeCount")
            record = result.single()
            count = record["nodeCount"] if record else 0

        driver.close()
        return count

    except Exception as e:
        logging.info(f"Error checking Neo4j data: {e}")
        return 0


def wait_for_neo4j() -> None:
    """Wait for Neo4j to be ready"""
    logging.info("Waiting for Neo4j to be ready...")
    max_attempts = 60
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(get_neo4j_http_uri(), timeout=5)
            if response.status_code < 500:  # Accept any non-server error status
                break
        except requests.RequestException:
            pass

        time.sleep(1)
        attempt += 1

    if attempt >= max_attempts:
        logging.info(f"ERROR: Neo4j is not accessible after {max_attempts} seconds")
        sys.exit(1)

    logging.info("Neo4j is accessible.")

    # Wait a bit more for Neo4j to be fully ready for queries
    time.sleep(5)


def extract_zip_files(data_dir: str) -> bool:
    """Extract zip files in the given directory"""
    data_path = Path(data_dir)
    logging.info(f"Checking for zip files to extract in {data_dir}...")

    # Find all zip files in the directory
    zip_files = list(data_path.glob("*.zip"))

    if not zip_files:
        logging.info("No zip files found to extract.")
        return True

    # Extract each zip file
    for zip_file in zip_files:
        logging.info(f"Extracting: {zip_file.name}")

        # Create extraction directory based on zip filename (without .zip extension)
        extract_dir = zip_file.with_suffix("")

        try:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                # Create extraction directory if it doesn't exist
                extract_dir.mkdir(exist_ok=True)
                zip_ref.extractall(extract_dir)

            logging.info(f"Successfully extracted: {zip_file.name}")

            # Optionally remove the zip file after successful extraction
            # Uncomment the next line if you want to delete zip files after extraction
            # zip_file.unlink()

        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError) as e:
            logging.info(f"ERROR: Failed to extract {zip_file.name}: {e}")
            return False

    logging.info("All zip files extracted successfully.")
    return True


def download_snomed_data() -> bool:
    """Download SNOMED CT data"""
    try:
        download_main()
        return True
    except Exception as e:
        logging.info(f"ERROR: Failed to download SNOMED data: {e}")
        return False


def load_snomed_data() -> bool:
    """Load SNOMED CT data into Neo4j"""
    try:
        load_main()
        return True

    except Exception as e:
        logging.error(f"Failed to load SNOMED data: {e}")
        return False


def create_slim_database() -> bool:
    """Create slim database if requested"""
    try:
        slim_main()
        return True

    except Exception as e:
        logging.error(f"Failed to create slim database: {e}")
        return False


def main() -> None:
    """Main function"""
    try:
        # Wait for Neo4j to be ready
        wait_for_neo4j()

        # Check if database already has data
        logging.info("Checking if database contains data...")
        node_count = check_neo4j_data()

        if node_count > 0:
            logging.info(f"Database contains {node_count} nodes. Service is running fine.")
            logging.info("Import skipped - data already exists.")
        else:
            logging.info("Database is empty. Checking for SNOMED data...")

            snomed_dir = Path("/mnt/snomed")

            # Check if SNOMED data exists in /mnt/snomed
            if not snomed_dir.exists() or not any(snomed_dir.iterdir()):
                logging.info("No SNOMED data found in /mnt/snomed. Attempting download...")

                if not download_snomed_data():
                    logging.error("Failed to download SNOMED CT data.")
                    sys.exit(1)

                # Extract downloaded zip files
                if not extract_zip_files("/mnt/snomed"):
                    logging.error("Failed to extract SNOMED CT data.")
                    sys.exit(1)
            else:
                # Data directory exists but might contain zip files that need extraction
                logging.info("SNOMED data directory exists. Checking for zip files to extract...")
                if not extract_zip_files("/mnt/snomed"):
                    logging.error("Failed to extract existing zip files.")
                    sys.exit(1)

            # Load SNOMED CT data
            logging.info("Loading SNOMED CT data into Neo4j...")
            if not load_snomed_data():
                logging.error("Failed to load SNOMED CT data.")
                sys.exit(1)

            # Create slim database if requested
            snomed_slim_mode = os.getenv("SNOMED_SLIM_HIERARCHIES") or os.getenv("SNOMED_SLIM_RELATIONSHIPS")
            if snomed_slim_mode:
                logging.info("Creating slim database...")
                if not create_slim_database():
                    logging.error("Failed to create slim database.")
                    sys.exit(1)

            logging.info("SNOMED CT data loaded successfully.")

        logging.info("Import process completed.")

    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logging.info(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
