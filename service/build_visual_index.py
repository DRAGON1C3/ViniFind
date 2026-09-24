"""Generate SigLIP embeddings and evaluate visual retrieval.

The script uses the prepared dataset manifest and keeps one vector per
training image. It does not modify the source dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def embed_images(
    model: AutoModel,
    processor: AutoProcessor,
    rows: list[dict[str, str]],
    root: Path,
    target: torch.device,
) -> tuple[torch.Tensor, list[dict[str, str]]]:
    vectors: list[torch.Tensor] = []
    kept: list[dict[str, str]] = []
    model.eval()

    for index, row in enumerate(rows, start=1):
        path = root / row["image_path"]
        try:
            with Image.open(path) as image:
                inputs = processor(
                    images=image.convert("RGB"),
                    return_tensors="pt",
                )
            inputs = {key: value.to(target) for key, value in inputs.items()}
            with torch.inference_mode():
                vector = model.get_image_features(**inputs)
                vector = torch.nn.functional.normalize(vector, dim=-1)
            vectors.append(vector[0].float().cpu())
            kept.append(row)
        except Exception as error:
            print(f"Skipping {path}: {error}")

        if index % 50 == 0 or index == len(rows):
            print(f"Embedded {index}/{len(rows)}")

    if not vectors:
        raise RuntimeError("No images were embedded")
    return torch.stack(vectors), kept


def evaluate(
    model: AutoModel,
    processor: AutoProcessor,
    rows: list[dict[str, str]],
    root: Path,
    index_vectors: torch.Tensor,
    index_rows: list[dict[str, str]],
    target: torch.device,
) -> dict[str, float]:
    top1 = 0
    top5 = 0
    evaluated = 0
    for row in rows:
        path = root / row["image_path"]
        try:
            with Image.open(path) as image:
                inputs = processor(images=image.convert("RGB"), return_tensors="pt")
            inputs = {key: value.to(target) for key, value in inputs.items()}
            with torch.inference_mode():
                vector = model.get_image_features(**inputs)
                vector = torch.nn.functional.normalize(vector, dim=-1).float().cpu()
            scores = vector @ index_vectors.T
            indices = torch.topk(scores[0], k=min(5, len(index_rows))).indices
            slugs = [index_rows[item]["slug"] for item in indices.tolist()]
            expected = row["slug"]
            top1 += int(slugs[0] == expected)
            top5 += int(expected in slugs)
            evaluated += 1
        except Exception as error:
            print(f"Skipping evaluation image {path}: {error}")

    return {
        "evaluated": evaluated,
        "top1": top1 / evaluated if evaluated else 0.0,
        "top5": top5 / evaluated if evaluated else 0.0,
    }


def main(
    dataset_root: Path,
    output: Path,
    model_id: str,
    eval_root: Path | None,
) -> None:
    manifest_rows = load_manifest(dataset_root / "manifest.csv")
    target = device()
    print(f"Device: {target}")
    print(f"Model: {model_id}")

    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).to(target)
    vectors, kept_rows = embed_images(
        model, processor, manifest_rows, dataset_root, target
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"vectors": vectors, "rows": kept_rows}, output)
    print(f"Saved {len(kept_rows)} vectors to {output}")

    if eval_root is not None:
        eval_images = sorted(
            path for path in (eval_root / "queries").glob("*")
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        eval_rows = [
            {"image_path": str(path.relative_to(dataset_root)), "slug": ""}
            for path in eval_images
        ]
        print(json.dumps(
            evaluate(
                model,
                processor,
                eval_rows,
                dataset_root,
                vectors,
                kept_rows,
                target,
            ),
            indent=2,
        ))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--model",
        default="google/siglip-base-patch16-224",
    )
    parser.add_argument("--eval-root", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(
        args.dataset_root.resolve(),
        args.output.resolve(),
        args.model,
        args.eval_root.resolve() if args.eval_root else None,
    )
