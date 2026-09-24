#!/usr/bin/env python3
"""
Setup script to download PhoBERT models from external hosting.
Run this after cloning the repository:
    python setup_models.py --url "https://your-link-here/models.tar.gz"
"""
import argparse
import os
import sys
import tarfile
import zipfile
import hashlib
import json
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

try:
    from tqdm import tqdm
except ImportError:
    print("Installing tqdm...")
    os.system(f"{sys.executable} -m pip install tqdm -q")
    from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.resolve()
MODEL_DIR = PROJECT_ROOT / "backend" / "model"
EXPECTED_FILES = [
    "phobert_models/sentiment_classification/final_model/config.json",
    "phobert_models/sentiment_classification/label_mapping.json",
    "phobert_models/aspect_classification/final_model/config.json",
    "phobert_models/aspect_classification/label_mapping.json",
]


def check_existing():
    """Check if models already exist."""
    missing = []
    for rel_path in EXPECTED_FILES:
        if not (MODEL_DIR / rel_path).exists():
            missing.append(rel_path)
    return missing


def download_file(url, dest, chunk_size=1024 * 1024):
    """Download file with progress bar."""
    print(f"Downloading from: {url}")
    print(f"Saving to: {dest}")

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    temp_path = str(dest) + ".tmp"

    with open(temp_path, "wb") as f, tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Downloading",
    ) as pbar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

    os.replace(temp_path, dest)
    print(f"Downloaded: {dest}")


def extract_archive(archive_path, extract_to):
    """Extract tar.gz or zip archive."""
    print(f"Extracting {archive_path.name} ...")
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_to)
    elif suffix in (".tar.gz", ".tgz", ".tar"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(extract_to)
    else:
        raise ValueError(f"Unsupported archive format: {suffix}")
    print(f"Extracted to: {extract_to}")


def verify_models():
    """Verify all expected model files are present."""
    print("Verifying model files...")
    missing = []
    for rel_path in EXPECTED_FILES:
        full_path = MODEL_DIR / rel_path
        if not full_path.exists():
            missing.append(rel_path)
        else:
            print(f"  [OK] {rel_path}")

    if missing:
        print(f"\n[WARN] Missing files after setup:")
        for p in missing:
            print(f"  - {p}")
        return False
    print("\nAll model files verified!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download and setup PhoBERT models for the project."
    )
    parser.add_argument(
        "--url",
        type=str,
        required=False,
        help=(
            "Direct download URL for models archive (tar.gz or zip). "
            "Upload backend/model/ to Google Drive/Dropbox and share a direct link."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite existing models.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PhoBERT Model Setup")
    print("=" * 60)

    # Check if models already exist
    if not args.force:
        missing = check_existing()
        if not missing:
            print("Models already exist. Use --force to re-download.")
            verify_models()
            return

    # Show missing files
    print("\nMissing model files:")
    for p in (check_existing() or ["None"]):
        print(f"  - {p}")

    # Download
    if not args.url:
        print("\nPlease download models from:")
        print(
            "1. Upload backend/model/ to Google Drive/Dropbox/HuggingFace"
        )
        print("2. Get a direct download link")
        print("3. Run: python setup_models.py --url <your-link>")
        sys.exit(1)

    archive_name = "models_phobert.tar.gz"
    archive_path = PROJECT_ROOT / archive_name

    download_file(args.url, archive_path)

    # Extract
    extract_archive(archive_path, PROJECT_ROOT)

    # Cleanup
    if archive_path.exists():
        archive_path.unlink()
        print(f"Cleaned up: {archive_path}")

    # Verify
    verify_models()


if __name__ == "__main__":
    main()
