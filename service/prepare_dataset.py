"""Build a deduplicated image dataset linked to the Strapi catalog.

Example:
    python service/prepare_dataset.py ^
      --input-root D:\Датасет\Датасет ^
      --output-root D:\Датасет\prepared_dataset
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
from collections import defaultdict
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".jfif",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".heic",
}
VARIANT_PREFIXES = ("thumbnail_", "small_", "medium_")
EXCLUDED_PARTS = {"eval", "реальные фото", "__macosx"}


def normalize(value: str) -> str:
    value = value.lower().replace("ё", "е")
    return re.sub(r"[^a-z0-9]+", "", value)


def clean_csv_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def copy_or_link(source: Path, destination: Path, mode: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "hardlink":
        try:
            destination.hardlink_to(source)
            return
        except OSError:
            pass
    shutil.copy2(source, destination)


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def find_csv(root: Path) -> Path:
    candidates = list(root.glob("*.csv"))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one CSV in {root}, found {len(candidates)}")
    return candidates[0]


def load_catalog(csv_path: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    if not rows or "Slug" not in rows[0]:
        raise RuntimeError("CSV must contain a Slug column")

    by_slug: dict[str, dict[str, str]] = {}
    for row in rows:
        slug = clean_csv_value(row.get("Slug", ""))
        if slug:
            by_slug.setdefault(slug, row)
    return rows, by_slug


def source_images(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        relative_parts = {part.lower() for part in path.relative_to(root).parts}
        if relative_parts & EXCLUDED_PARTS:
            continue
        if "prod-svoe-vino-strapi2" in relative_parts:
            continue
        if is_image(path):
            stem = path.stem.lower()
            if stem.startswith(VARIANT_PREFIXES):
                continue
            result.append(path)
    return result


def match_images(
    slugs: list[str], images: list[Path]
) -> tuple[dict[str, list[Path]], list[dict[str, str]]]:
    normalized_slugs = {slug: normalize(slug) for slug in slugs}
    candidates: dict[Path, list[tuple[str, int]]] = defaultdict(list)

    for image in images:
        normalized_name = normalize(image.stem)
        for slug, normalized_slug in normalized_slugs.items():
            if normalized_slug and normalized_slug in normalized_name:
                candidates[image].append((slug, len(normalized_slug)))

    matched: dict[str, list[Path]] = defaultdict(list)
    ambiguous: list[dict[str, str]] = []
    for image, values in candidates.items():
        longest = max(length for _, length in values)
        owners = [slug for slug, length in values if length == longest]
        if len(owners) != 1:
            ambiguous.append({
                "image": str(image),
                "slugs": "|".join(sorted(owners)),
                "reason": "ambiguous_longest_match",
            })
            continue
        matched[owners[0]].append(image)

    return matched, ambiguous


def find_named_dir(root: Path, name: str) -> Path | None:
    for path in root.iterdir():
        if path.is_dir() and path.name.casefold() == name.casefold():
            return path
    return None


def copy_directory_images(source_dir: Path | None, destination: Path, mode: str) -> int:
    if source_dir is None:
        return 0
    count = 0
    for source in source_dir.rglob("*"):
        if not is_image(source) or "__MACOSX" in {part.upper() for part in source.parts}:
            continue
        destination_name = f"{count:05d}_{source.name}"
        copy_or_link(source, destination / destination_name, mode)
        count += 1
    return count


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_dataset(input_root: Path, output_root: Path, link_mode: str) -> None:
    catalog_path = find_csv(input_root)
    catalog_rows, catalog = load_catalog(catalog_path)
    images = source_images(input_root)
    matched, ambiguous = match_images(list(catalog), images)

    train_dir = output_root / "train" / "images"
    real_dir = output_root / "test_real"
    eval_dir = output_root / "eval"
    train_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str]] = []
    used_hashes: set[str] = set()
    skipped_duplicates = 0

    for slug, paths in sorted(matched.items()):
        row = catalog[slug]
        for source in sorted(paths):
            digest = file_sha256(source)
            if digest in used_hashes:
                skipped_duplicates += 1
                continue
            used_hashes.add(digest)
            destination_name = f"{slug}__{digest[:12]}{source.suffix.lower()}"
            destination = train_dir / destination_name
            copy_or_link(source, destination, link_mode)
            manifest.append({
                "image_path": destination.relative_to(output_root).as_posix(),
                "slug": slug,
                "name": clean_csv_value(row.get("Название вина", "")),
                "category": clean_csv_value(row.get("Категория", "")),
                "color": clean_csv_value(row.get("Цвет", "")),
                "region": clean_csv_value(row.get("Регион", "")),
                "grape_variety": clean_csv_value(row.get("Сорт винограда", "")),
                "winery": clean_csv_value(row.get("Винодельня", "")),
                "description": clean_csv_value(row.get("Описание", "")),
                "source_file": str(source),
                "sha256": digest,
            })

    real_count = copy_directory_images(
        find_named_dir(input_root, "Реальные фото"), real_dir, link_mode
    )
    eval_source = find_named_dir(input_root, "eval")
    eval_count = copy_directory_images(
        eval_source / "queries" if eval_source else None, eval_dir / "queries", link_mode
    )

    unmatched = [
        {"slug": slug, "name": clean_csv_value(row.get("Название вина", ""))}
        for slug, row in sorted(catalog.items())
        if slug not in matched
    ]
    write_csv(
        output_root / "manifest.csv",
        manifest,
        list(manifest[0]) if manifest else [
            "image_path", "slug", "name", "category", "color", "region",
            "grape_variety", "winery", "description", "source_file", "sha256",
        ],
    )
    write_csv(output_root / "unmatched_slugs.csv", unmatched, ["slug", "name"])
    write_csv(
        output_root / "ambiguous_images.csv",
        ambiguous,
        ["image", "slugs", "reason"],
    )
    (output_root / "summary.txt").write_text(
        "\n".join([
            f"catalog_rows={len(catalog_rows)}",
            f"unique_slugs={len(catalog)}",
            f"source_images_considered={len(images)}",
            f"matched_slugs={len(matched)}",
            f"unmatched_slugs={len(unmatched)}",
            f"training_images={len(manifest)}",
            f"duplicate_images_skipped={skipped_duplicates}",
            f"ambiguous_images={len(ambiguous)}",
            f"real_test_images={real_count}",
            f"eval_images={eval_count}",
            f"link_mode={link_mode}",
        ]) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--link-mode",
        choices=("hardlink", "copy"),
        default="hardlink",
        help="Hardlinks save disk space when source and output are on the same volume.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_dataset(args.input_root.resolve(), args.output_root.resolve(), args.link_mode)
