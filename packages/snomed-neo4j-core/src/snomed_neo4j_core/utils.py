import logging
import os
import zipfile
from pathlib import Path


def env_bool(name: str) -> bool:
    return os.environ[name].lower() in ["1", "true"]


def optional_env_int(name: str) -> int | None:
    value = os.getenv(name)
    return None if value is None else int(value)


def extract_zip_files(data_dir: str, delete_zip: bool = False) -> None:
    """Extract zip files in the given directory"""
    data_path = Path(data_dir)
    logging.info(f"Checking for zip files to extract in {data_dir}...")

    zip_files = list(data_path.glob("*.zip"))

    if not zip_files:
        logging.info("No zip files found to extract.")
        return

    for zip_file in zip_files:
        logging.info(f"Extracting: {zip_file.name}")

        extract_dir = zip_file.with_suffix("")

        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            extract_dir.mkdir(exist_ok=True)
            zip_ref.extractall(extract_dir)

        logging.info(f"Successfully extracted: {zip_file.name}")

        if delete_zip:
            zip_file.unlink()

    logging.info("All zip files extracted successfully.")
    return
