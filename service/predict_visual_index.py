"""Run visual retrieval against a previously built index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor


def main(
    dataset_root: Path,
    index_path: Path,
    images_root: Path,
    output: Path,
    model_id: str,
) -> None:
    index = torch.load(index_path, map_location="cpu", weights_only=False)
    vectors: torch.Tensor = index["vectors"]
    rows: list[dict[str, str]] = index["rows"]
    target = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).to(target)
    model.eval()

    predictions = []
    for image_path in sorted(images_root.rglob("*")):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        with Image.open(image_path) as image:
            inputs = processor(images=image.convert("RGB"), return_tensors="pt")
        inputs = {key: value.to(target) for key, value in inputs.items()}
        with torch.inference_mode():
            query = model.get_image_features(**inputs)
            query = torch.nn.functional.normalize(query, dim=-1).float().cpu()
        scores = query @ vectors.T
        top = torch.topk(scores[0], k=min(5, len(rows)))
        candidates = [
            {
                "slug": rows[item]["slug"],
                "score": round(float(score), 6),
                "image_path": rows[item]["image_path"],
            }
            for score, item in zip(top.values.tolist(), top.indices.tolist())
        ]
        predictions.append({
            "query_id": image_path.stem,
            "image_path": str(image_path.relative_to(dataset_root)).replace("\\", "/"),
            "predicted_slug": candidates[0]["slug"],
            "candidates": candidates,
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for prediction in predictions:
            stream.write(json.dumps(prediction, ensure_ascii=False) + "\n")
    print(f"Predictions: {len(predictions)}")
    print(f"Output: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="google/siglip-base-patch16-224")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(
        args.dataset_root.resolve(),
        args.index.resolve(),
        args.images_root.resolve(),
        args.output.resolve(),
        args.model,
    )
