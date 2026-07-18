"""
Dataset downloader
"""

import requests
from pathlib import Path

from check_structure import check_existing_file


def download_raw_data(
        year: int = 2021,
        datasets_api: str = "https://www.data.gouv.fr/api/1/datasets/",
        dataset_slug: str =  "bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024/",
        raw_data_dir: str = "./data/raw"
        ) -> None:
    """Download the 4 raw datasets for a given year."""
    # API endpoint and output directory
    dataset_url = datasets_api + dataset_slug
    output_dir = Path(raw_data_dir)

    # Get dataset metadata
    response = requests.get(dataset_url)

    # Stop if API request was not successful
    if response.status_code != 200:
        raise Exception(f"Dataset API request failed ({response.status_code})")
    
    # Extract the list of resource metadata
    dataset = response.json()
    resources = dataset["resources"]

    # Search for the CSV files corresponding to the requested year
    for resource in resources:
        title = resource.get("title", "")
        url = resource.get("url", "")

        # Skip files that are non csv / from another year / are BAAC archives
        if not title.endswith(".csv") or str(year) not in title or "baac" in title:
            continue

        output_path = output_dir / title

        # Skip files that already exist after user confirmation
        if not check_existing_file(output_path):
            continue

        # Download file in chunks
        print(f"Downloading {title}...")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)


if __name__ == "__main__":

    # Config
    YEAR = 2021
    RAW_DATA_DIR = "../../data/raw"

    # Run download
    download_raw_data(
        year=YEAR,
        raw_data_dir=RAW_DATA_DIR
    )