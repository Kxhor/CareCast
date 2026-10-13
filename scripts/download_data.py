#!/usr/bin/env python3
"""Download the official CDC NHSN respiratory surveillance dataset into data/raw/.

Source: Centers for Disease Control and Prevention (CDC)
Dataset: Weekly Hospital Respiratory Data (HRD) Metrics by Jurisdiction (ua7e-t2fy)
License: Public Domain (Attribution requested)
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

CDC_DATASET_URL = "https://data.cdc.gov/api/views/ua7e-t2fy/rows.csv?accessType=DOWNLOAD"
TARGET_PATH = Path("data/raw/ua7e-t2fy.csv")


def main() -> int:
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("==================================================")
    print("CareCast Dataset Acquisition")
    print("==================================================")
    print(f"Source URL  : {CDC_DATASET_URL}")
    print(f"Destination : {TARGET_PATH}")
    print("--> Downloading dataset (approx. 24 MB)...")

    try:
        urllib.request.urlretrieve(CDC_DATASET_URL, TARGET_PATH)
        size_bytes = TARGET_PATH.stat().st_size
        print(f"[OK] Download complete: {size_bytes:,} bytes saved.")
        print("\nNext step: Run 'python -m carecast.pipeline rebuild' to build database and train models.")
        return 0
    except Exception as err:
        print(f"[FAIL] Download failed: {err}", file=sys.stderr)
        print(
            f"Alternative manual command:\n  curl -o data/raw/ua7e-t2fy.csv '{CDC_DATASET_URL}'",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
