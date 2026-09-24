"""Find likely image candidates for catalog slugs without changing the dataset.

Example:
    python service/find_dataset_candidates.py ^
      --input-root D:\Датасет\Датасет ^
      --prepared-root D:\Датасет\prepared_dataset ^
      --output D:\Датасет\prepared_dataset\candidates.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jfif", ".png", ".webp", ".tif", ".tiff", ".heic"
}
VARIANT_PREFIXES = ("thumbnail_", "small_", "medium_")
EXCLUDED_PARTS = {"eval", "реальные фото", "__macosx"}
GENERIC_TOKENS = {
    "vino", "wine", "beloe", "belyy", "belaya", "krasnoe", "krasnyy",
    "rozovoe", "rozovyy", "roze", "suhoe", "suhoie", "polusuhoe",
    "polusladkoe", "bryut", "igristoe", "vinodelnya", "vinograd",
}


def clean(value: str) -> str:
    return value.strip().strip('"').strip("'")


def tokens(value: str) -> set[str]:
    value = value.lower().replace("ё", "е")
    return {
        token
        for token in re.findall(r"[a-z0-9а-я]{3,}", value)
        if token not in GENERIC_TOKENS
    }


def normalize(value: str) -> str:
    return "".join(sorted(tokens(value)))


def image_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob("*"):
        parts = {part.casefold() for part in path.relative_to(root).parts}
        if (
            path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
            and not parts & EXCLUDED_PARTS
            and "prod-svoe-vino-strapi2" not in parts
            and not path.stem.casefold().startswith(VARIANT_PREFIXES)
        ):
            result.append(path)
    return sorted(result)


def unique_images(images: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for image in images:
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest not in seen:
            seen.add(digest)
            result.append(image)
    return result


def load_catalog(root: Path) -> dict[str, dict[str, str]]:
    csv_files = list(root.glob("*.csv"))
    if len(csv_files) != 1:
        raise RuntimeError(f"Expected one catalog CSV, found {len(csv_files)}")
    with csv_files[0].open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {
        clean(row["Slug"]): row
        for row in rows
        if clean(row.get("Slug", ""))
    }


def load_unmatched(prepared_root: Path, catalog: dict[str, dict[str, str]]) -> list[str]:
    path = prepared_root / "unmatched_slugs.csv"
    if not path.exists():
        raise RuntimeError(f"Missing {path}; run prepare_dataset.py first")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        slugs = [clean(row["slug"]) for row in csv.DictReader(stream)]
    return [slug for slug in slugs if slug in catalog]


def profile(slug: str, row: dict[str, str]) -> tuple[set[str], set[str]]:
    metadata = " ".join(
        row.get(field, "")
        for field in (
            "Название вина",
            "Винодельня",
            "Сорт винограда",
            "Цвет",
            "Категория",
            "Регион",
        )
    )
    return tokens(slug), tokens(clean(metadata))


def score_candidate(
    slug_tokens: set[str],
    metadata_tokens: set[str],
    slug: str,
    image: Path,
) -> tuple[float, int, float, str]:
    image_tokens = tokens(image.stem)
    slug_overlap = slug_tokens & image_tokens
    metadata_overlap = metadata_tokens & image_tokens
    slug_score = len(slug_overlap) / max(len(slug_tokens), 1)
    metadata_score = len(metadata_overlap) / max(len(metadata_tokens), 1)
    sequence_score = SequenceMatcher(
        None, normalize(slug), normalize(image.stem)
    ).ratio()
    score = 0.75 * slug_score + 0.15 * metadata_score + 0.10 * sequence_score
    overlap = slug_overlap | metadata_overlap
    return score, len(overlap), sequence_score, "|".join(sorted(overlap))


def decision(score: float, margin: float) -> str:
    if score >= 0.92 and margin >= 0.08:
        return "auto_candidate"
    if score >= 0.75:
        return "manual_review"
    return "weak_candidate"


def write_candidates(
    output: Path,
    input_root: Path,
    catalog: dict[str, dict[str, str]],
    unmatched: list[str],
    images: list[Path],
    top_n: int,
) -> None:
    rows: list[dict[str, str]] = []
    for slug in unmatched:
        slug_tokens, metadata_tokens = profile(slug, catalog[slug])
        ranked = []
        for image in images:
            score, overlap_count, sequence, overlap = score_candidate(
                slug_tokens, metadata_tokens, slug, image
            )
            if overlap_count:
                ranked.append((score, overlap_count, sequence, overlap, image))
        ranked.sort(key=lambda item: item[:3], reverse=True)
        top = ranked[:top_n]
        top_score = top[0][0] if top else 0.0
        second_score = top[1][0] if len(top) > 1 else 0.0
        margin = top_score - second_score

        for rank, (score, overlap_count, sequence, overlap, image) in enumerate(
            top, start=1
        ):
            rows.append({
                "slug": slug,
                "name": clean(catalog[slug].get("Название вина", "")),
                "winery": clean(catalog[slug].get("Винодельня", "")),
                "rank": str(rank),
                "candidate_path": image.relative_to(input_root).as_posix(),
                "score": f"{score:.4f}",
                "top1_margin": f"{margin:.4f}",
                "overlap_count": str(overlap_count),
                "sequence_score": f"{sequence:.4f}",
                "matched_tokens": overlap,
                "decision": decision(score, margin),
            })

    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "slug", "name", "winery", "rank", "candidate_path", "score",
        "top1_margin", "overlap_count", "sequence_score", "matched_tokens",
        "decision",
    ]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = Counter(row["decision"] for row in rows if row["rank"] == "1")
    print(f"Unmatched slugs: {len(unmatched)}")
    print(f"Images searched: {len(images)}")
    print(f"Candidate rows: {len(rows)}")
    print(f"Top-1 decisions: {dict(summary)}")
    print(f"Output: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    catalog = load_catalog(args.input_root)
    unmatched = load_unmatched(args.prepared_root, catalog)
    images = unique_images(image_files(args.input_root))
    write_candidates(
        args.output,
        args.input_root,
        catalog,
        unmatched,
        images,
        max(1, args.top_n),
    )
