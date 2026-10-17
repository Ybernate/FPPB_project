"""Download script for LOTUS and COCONUT bulk database dumps.

Downloads:
1. LOTUS frozen metadata snapshot (Zenodo record 19360665)
   File: 260413_frozen_metadata.csv.gz (~86 MB compressed, ~953k rows)
2. COCONUT full natural products archive (Uni-Jena S3 release 2026-10)
   File: coconut_csv-10-2026.zip (~236 MB compressed, ~738k compounds)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOTUS_ZENODO_RECORD = "19360665"
LOTUS_FILENAME = "260413_frozen_metadata.csv.gz"
LOTUS_URL = f"https://zenodo.org/api/records/{LOTUS_ZENODO_RECORD}/files/{LOTUS_FILENAME}/content"

COCONUT_FILENAME = "coconut_csv-10-2026.zip"
COCONUT_URL = f"https://coconut.s3.uni-jena.de/prod/downloads/2026-10/{COCONUT_FILENAME}"

DEFAULT_USER_AGENT = "ConoceTuPlanta/1.0 (academic research tool)"
CHUNK_SIZE = 1024 * 1024  # 1 MB chunk


def download_file(
    url: str,
    dest_path: Path,
    expected_size: int | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries: int = 3,
    force: bool = False,
) -> bool:
    """Downloads a file with streaming chunks, progress reporting, and retries."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and not force:
        local_size = dest_path.stat().st_size
        if expected_size is None or local_size == expected_size:
            print(f"[OK] File already exists: {dest_path} ({local_size:,} bytes). Skipping.")
            return True
        else:
            print(f"[!] File exists but size mismatch ({local_size} vs expected {expected_size}). Re-downloading.")

    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    headers = {"User-Agent": user_agent}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[*] Downloading {url} -> {dest_path.name} (attempt {attempt}/{max_retries})...")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                total_size = resp.headers.get("Content-Length")
                total_bytes = int(total_size) if total_size and total_size.isdigit() else None

                downloaded = 0
                start_time = time.time()
                last_report = start_time

                with open(temp_path, "wb") as f_out:
                    while True:
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_report >= 1.0 or (total_bytes and downloaded == total_bytes):
                            elapsed = max(0.001, now - start_time)
                            rate = (downloaded / (1024 * 1024)) / elapsed
                            if total_bytes:
                                pct = (downloaded / total_bytes) * 100
                                print(
                                    f"\r    {downloaded / (1024 * 1024):.1f} / {total_bytes / (1024 * 1024):.1f} MB "
                                    f"({pct:.1f}%) at {rate:.2f} MB/s",
                                    end="",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"\r    {downloaded / (1024 * 1024):.1f} MB downloaded at {rate:.2f} MB/s",
                                    end="",
                                    flush=True,
                                )
                            last_report = now

                print()

            # Atomic rename upon successful download
            if temp_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                temp_path.rename(dest_path)
            print(f"[SUCCESS] Download completed: {dest_path} ({dest_path.stat().st_size:,} bytes)")
            return True

        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            print(f"\n[ERROR] Download failed: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            if attempt < max_retries:
                sleep_sec = 2 * attempt
                print(f"Retrying in {sleep_sec} seconds...")
                time.sleep(sleep_sec)
            else:
                print(f"[FAILED] Could not download {url} after {max_retries} attempts.")
                return False

    return False


def download_lotus(dest_dir: Path, force: bool = False) -> bool:
    """Downloads LOTUS Zenodo frozen dump (expected ~90.3 MB)."""
    dest = Path(dest_dir) / LOTUS_FILENAME
    return download_file(LOTUS_URL, dest, expected_size=90298678, force=force)


def download_coconut(dest_dir: Path, force: bool = False) -> bool:
    """Downloads COCONUT archive (expected ~247.9 MB)."""
    dest = Path(dest_dir) / COCONUT_FILENAME
    return download_file(COCONUT_URL, dest, expected_size=247959854, force=force)


def main():
    parser = argparse.ArgumentParser(description="Download raw dumps for LOTUS and COCONUT")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "raw",
        help="Directory where raw dump files are stored (default: data/raw)",
    )
    parser.add_argument("--lotus-only", action="store_true", help="Download only LOTUS dump")
    parser.add_argument("--coconut-only", action="store_true", help="Download only COCONUT dump")
    parser.add_argument("--force", "-f", action="store_true", help="Force redownload even if file exists")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {args.output_dir.resolve()}")

    lotus_ok = True
    coconut_ok = True

    if not args.coconut_only:
        lotus_ok = download_lotus(args.output_dir, force=args.force)

    if not args.lotus_only:
        coconut_ok = download_coconut(args.output_dir, force=args.force)

    if lotus_ok and coconut_ok:
        print("\nAll requested dumps successfully downloaded.")
        sys.exit(0)
    else:
        print("\nWarning: Some downloads failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
