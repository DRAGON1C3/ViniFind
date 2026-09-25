"""Build an ML manifest from the wine_team_handoff photo links.

This script copies only the original image files referenced by photo_links.csv.
It does not modify the handoff files or the source uploads directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--handoff",
        type=Path,
        default=Path(r"D:\Датасет\wine_team_handoff"),
    )
    parser.add_argument(
        "--uploads",
        type=Path,
        default=Path(
            r"D:\Датасет\Датасет\prod-svoe-vino-strapi1"
            r"\prod-svoe-vino\strapi\uploads"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"D:\Датасет\ml_handoff"),
    )
    return parser.parse_args()


def read_catalog(path: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc
            slug = str(item.get("slug", "")).strip()
            if slug:
                catalog[slug] = item
    return catalog


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_uploads(uploads: Path) -> dict[str, Path]:
    if not uploads.is_dir():
        raise FileNotFoundError(f"Uploads directory does not exist: {uploads}")

    index: dict[str, Path] = {}
    for path in uploads.rglob("*"):
        if not path.is_file():
            continue
        if path.name.lower().startswith(("thumbnail_", "small_", "medium_")):
            continue
        index.setdefault(path.name, path)
    return index


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    links_path = args.handoff / "output" / "photo_links.csv"
    catalog_path = args.handoff / "output" / "catalog.jsonl"
    if not links_path.is_file():
        raise FileNotFoundError(f"Missing photo links file: {links_path}")
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Missing catalog file: {catalog_path}")

    catalog = read_catalog(catalog_path)
    upload_index = index_uploads(args.uploads)
    image_dir = args.output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    copied_by_hash: dict[str, str] = {}
    copied_files: set[str] = set()

    with links_path.open("r", encoding="utf-8-sig", newline="") as handle:
        links = csv.DictReader(handle)
        for link in links:
            slug = (link.get("slug") or "").strip()
            filename = (link.get("asset_filename") or "").strip()
            source = upload_index.get(filename)
            if source is None:
                missing_rows.append(
                    {
                        "slug": slug,
                        "asset_filename": filename,
                        "review_status": link.get("review_status", ""),
                        "reason": "asset_filename_not_found",
                    }
                )
                continue

            digest = sha256(source)
            destination_name = source.name
            existing_name = copied_by_hash.get(digest)
            if existing_name is not None:
                destination_name = existing_name
            else:
                destination = image_dir / destination_name
                if destination_name not in copied_files:
                    shutil.copy2(source, destination)
                    copied_files.add(destination_name)
                copied_by_hash[digest] = destination_name

            item = catalog.get(slug, {})
            manifest_rows.append(
                {
                    "slug": slug,
                    "image_path": str(image_dir / destination_name),
                    "asset_filename": filename,
                    "sha256": digest,
                    "review_status": link.get("review_status", ""),
                    "match_method": link.get("match_method", ""),
                    "name": item.get("name", ""),
                    "producer": item.get("producer", ""),
                    "color_category": item.get("color_category", ""),
                    "region": item.get("region", ""),
                    "grapes": item.get("grapes", ""),
                    "vintage_candidate": item.get("vintage_candidate", ""),
                    "vintage_status": item.get("vintage_status", ""),
                }
            )

    manifest_fields = [
        "slug",
        "image_path",
        "asset_filename",
        "sha256",
        "review_status",
        "match_method",
        "name",
        "producer",
        "color_category",
        "region",
        "grapes",
        "vintage_candidate",
        "vintage_status",
    ]
    missing_fields = ["slug", "asset_filename", "review_status", "reason"]
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "manifest.csv", manifest_rows, manifest_fields)
    write_csv(args.output / "missing.csv", missing_rows, missing_fields)

    summary = {
        "catalog_rows": len(catalog),
        "photo_link_rows": len(manifest_rows) + len(missing_rows),
        "manifest_rows": len(manifest_rows),
        "unique_copied_files": len(copied_files),
        "missing_rows": len(missing_rows),
        "review_status_counts": {},
    }
    for row in manifest_rows:
        status = row["review_status"] or "empty"
        summary["review_status_counts"][status] = (
            summary["review_status_counts"].get(status, 0) + 1
        )
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
