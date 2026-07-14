"""
Download the Goodreads-10k dataset from Kaggle.

Requirements:
  - Kaggle account + API key
  - pip install kaggle
  - Place kaggle.json in C:/Users/<YourName>/.kaggle/kaggle.json  (Windows)

Dataset: https://www.kaggle.com/datasets/jealousleopard/goodreadsbooks
Files downloaded to: ./data/
"""

import subprocess
import sys
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATASET = "jealousleopard/goodreadsbooks"


def download():
    DATA_DIR.mkdir(exist_ok=True)

    print(f"Downloading dataset '{DATASET}' to {DATA_DIR} ...")
    result = subprocess.run(
        [
            sys.executable, "-m", "kaggle", "datasets", "download",
            "-d", DATASET,
            "-p", str(DATA_DIR),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("ERROR downloading dataset:")
        print(result.stderr)
        print("\nMake sure you have:")
        print("  1. pip install kaggle")
        print("  2. Kaggle API key at C:/Users/<YourName>/.kaggle/kaggle.json")
        print("  3. Accepted the dataset terms on Kaggle website")
        sys.exit(1)

    # Unzip
    zip_files = list(DATA_DIR.glob("*.zip"))
    for z in zip_files:
        print(f"Unzipping {z.name} ...")
        with zipfile.ZipFile(z, "r") as zf:
            zf.extractall(DATA_DIR)
        z.unlink()

    print("\nDownloaded files:")
    for f in DATA_DIR.iterdir():
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")

    print("\nDone! Run `python scripts/preprocess.py` next.")


if __name__ == "__main__":
    download()
