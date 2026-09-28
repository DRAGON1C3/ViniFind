"""Import top-1 candidate matches into the prepared training dataset.

This is an intentionally permissive MVP importer. It accepts every decision
class, but imports only rank=1 for each slug to avoid adding the same image
five times or assigning top-2 alternatives as separate labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: str) -> str:
    return value.strip().strip('"').strip("'")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(input_root: Path, prepared_root: Path, copy_mode: str) -> None:
    candidates_path = prepared_root / "candidates.csv"
    manifest_path = prepared_root / "manifest.csv"
    candidates = read_rows(candidates_path)
    manifest = read_rows(manifest_path)

    top_by_slug: dict[str, dict[str, str]] = {}
    for row in candidates:
        slug = clean(row.get("slug", ""))
        if slug and row.get("rank") == "1":
            top_by_slug.setdefault(slug, row)

    known_slugs = {clean(row.get("slug", "")) for row in manifest}
    known_hashes = {clean(row.get("sha256", "")) for row in manifest}
    candidate_hashes: dict[str, str] = {}
    imported: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    image_dir = prepared_root / "train" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    for slug, row in sorted(top_by_slug.items()):
        source = input_root / Path(row["candidate_path"])
        reason = ""
        if not source.is_file():
            reason = "missing_source_file"
        elif slug in known_slugs:
            reason = "slug_already_in_manifest"
        else:
            digest = sha256(source)
            if digest in known_hashes:
                reason = "image_already_in_manifest"
            elif digest in candidate_hashes:
                reason = f"same_image_already_assigned_to:{candidate_hashes[digest]}"

        if reason:
            skipped.append({
                "slug": slug,
                "candidate_path": row.get("candidate_path", ""),
                "reason": reason,
            })
            continue

        destination_name = f"{slug}__{digest[:12]}{source.suffix.lower()}"
        destination = image_dir / destination_name
        if copy_mode == "hardlink":
            try:
                destination.hardlink_to(source)
            except OSError:
                shutil.copy2(source, destination)
        else:
            shutil.copy2(source, destination)

        candidate_hashes[digest] = slug
        known_hashes.add(digest)
        known_slugs.add(slug)
        imported.append({
            "image_path": destination.relative_to(prepared_root).as_posix(),
            "slug": slug,
            "name": clean(row.get("name", "")),
            "category": "",
            "color": "",
            "region": "",
            "grape_variety": "",
            "winery": clean(row.get("winery", "")),
            "description": "",
            "source_file": str(source),
            "sha256": digest,
            "match_method": "candidate_top1",
            "match_score": row.get("score", ""),
            "match_decision": row.get("decision", ""),
        })

    manifest_fields = list(manifest[0]) if manifest else [
        "image_path", "slug", "name", "category", "color", "region",
        "grape_variety", "winery", "description", "source_file", "sha256",
    ]
    for field in (
        "match_method",
        "match_score",
        "match_decision",
    ):
        if field not in manifest_fields:
            manifest_fields.append(field)
    for row in manifest:
        for field in manifest_fields:
            row.setdefault(field, "")

    write_rows(manifest_path, manifest + imported, manifest_fields)
    write_rows(
        prepared_root / "candidate_import_skipped.csv",
        skipped,
        ["slug", "candidate_path", "reason"],
    )
    print(f"Candidate slugs: {len(top_by_slug)}")
    print(f"Imported: {len(imported)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Manifest rows: {len(manifest) + len(imported)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--copy-mode", choices=("hardlink", "copy"), default="hardlink")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.input_root.resolve(), args.prepared_root.resolve(), args.copy_mode)
