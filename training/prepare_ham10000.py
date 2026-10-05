"""Build training/ham10000_labels.csv (melanoma vs rest) from HAM10000_metadata.csv.

lesion_id is used as patient_id so all photos of one lesion stay in the same split.
"""
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
meta = pd.read_csv(root / "HAM10000_metadata.csv")
files = {p.stem: p for d in ("HAM10000_images_part_1", "HAM10000_images_part_2") for p in (root / d).glob("*.jpg")}

meta["path"] = meta["image_id"].map(files)
missing = meta["path"].isna().sum()
meta = meta.dropna(subset=["path"])
out = pd.DataFrame({
    "image_name": meta["image_id"],
    "path": meta["path"].astype(str),
    "target": (meta["dx"] == "mel").astype(int),
    "patient_id": meta["lesion_id"],
})
out.to_csv(root / "training" / "ham10000_labels.csv", index=False)
print(f"{len(out)} images ({missing} missing), melanoma {out.target.sum()} ({out.target.mean():.1%}), lesions {out.patient_id.nunique()}")
