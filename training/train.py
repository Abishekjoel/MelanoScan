"""Train MelanoHybridLite on ISIC 2020 / HAM10000-style data.

Data layout (either works):
  A) --csv labels.csv --images DIR
       CSV needs columns: image_name (no extension) and target (0/1).
       ISIC 2020 train.csv works as-is (optional patient_id enables patient-wise split).
       For HAM10000 build a CSV with target = (dx == 'mel').
  B) --images DIR containing two subfolders: melanoma/ and benign/

Phases (paper IV-D, scaled down): 1) frozen backbones, train fusion+head;
2) unfreeze everything, low LR, cosine schedule, early stopping.

  python training/train.py --csv train.csv --images jpeg/train --out backend/ml/weights/melano_lite.pt
"""
import argparse
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms as T

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ml.model import MelanoHybridLite  # noqa: E402

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
SIZE = 224


class Lesions(Dataset):
    def __init__(self, items, train):
        self.items = items
        aug = [
            T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(30),
            T.RandomResizedCrop(SIZE, scale=(0.75, 1.0)), T.ColorJitter(0.2, 0.2),
        ] if train else [T.Resize((SIZE, SIZE))]
        self.tf = T.Compose(aug + [T.ToTensor(), T.Normalize(MEAN, STD)])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, y = self.items[i]
        return self.tf(Image.open(path).convert("RGB")), torch.tensor(float(y))


def load_items(args):
    root = Path(args.images)
    if args.csv:
        df = pd.read_csv(args.csv)
        if "path" not in df:
            df["path"] = df["image_name"].map(lambda n: next(root.glob(f"{n}.*"), None))
        df = df.dropna(subset=["path"])
        if "patient_id" not in df:
            df["patient_id"] = df["image_name"]
        return df[["path", "target", "patient_id"]].rename(columns={"target": "y"})
    rows = [(p, y, p.stem) for y, d in enumerate(["benign", "melanoma"])
            for p in (root / d).glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    return pd.DataFrame(rows, columns=["path", "y", "patient_id"])


def patient_split(df, val_frac, seed):
    pats = df["patient_id"].unique()
    random.Random(seed).shuffle(pats)
    val_p = set(pats[: int(len(pats) * val_frac)])
    is_val = df["patient_id"].isin(val_p)
    return df[~is_val], df[is_val]


def focal_bce(logits, y, gamma=2.0, alpha=0.75):
    bce = F.binary_cross_entropy_with_logits(logits, y, reduction="none")
    p = torch.sigmoid(logits)
    pt = p * y + (1 - p) * (1 - y)
    at = alpha * y + (1 - alpha) * (1 - y)
    return (at * (1 - pt) ** gamma * bce).mean()


@torch.no_grad()
def evaluate(model, loader, dev):
    model.eval()
    ys, ps = [], []
    for x, y in loader:
        with torch.autocast("cuda", enabled=dev.type == "cuda"):
            ps.append(torch.sigmoid(model(x.to(dev))).float().cpu())
        ys.append(y)
    y, p = torch.cat(ys).numpy(), torch.cat(ps).numpy()
    pred = p >= 0.5
    sens = (pred & (y == 1)).sum() / max((y == 1).sum(), 1)
    spec = (~pred & (y == 0)).sum() / max((y == 0).sum(), 1)
    return {"auc": roc_auc_score(y, p) if len(set(y)) > 1 else float("nan"), "sens": sens, "spec": spec}


def run_phase(model, tr, va, dev, epochs, lr, accum, patience, name):
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=5e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")
    best, best_state, bad = -1, None, 0
    for ep in range(epochs):
        model.train()
        for i, (x, y) in enumerate(tr):
            with torch.autocast("cuda", enabled=dev.type == "cuda"):
                loss = focal_bce(model(x.to(dev)).float(), y.to(dev)) / accum
            scaler.scale(loss).backward()
            if (i + 1) % accum == 0:
                scaler.step(opt); scaler.update(); opt.zero_grad()
        sched.step()
        m = evaluate(model, va, dev)
        print(f"[{name}] epoch {ep+1}/{epochs} val AUC {m['auc']:.4f} sens {m['sens']:.3f} spec {m['spec']:.3f}", flush=True)
        if m["auc"] > best:
            best, bad = m["auc"], 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=".")
    ap.add_argument("--csv")
    ap.add_argument("--out", default="backend/ml/weights/melano_lite.pt")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--accum", type=int, default=2)
    ap.add_argument("--fusion-epochs", type=int, default=5)
    ap.add_argument("--finetune-epochs", type=int, default=15)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    df = load_items(args)
    train_df, val_df = patient_split(df, 0.15, args.seed)
    print(f"train {len(train_df)} (mel {int(train_df.y.sum())}) | val {len(val_df)} (mel {int(val_df.y.sum())})")

    # oversample melanoma so each batch sees the rare class
    w = np.where(train_df.y.values == 1, (train_df.y == 0).sum() / max(train_df.y.sum(), 1), 1.0)
    w = np.minimum(w, 10.0)
    sampler = WeightedRandomSampler(w, num_samples=len(train_df), replacement=True)
    mk = lambda d, t: list(zip(d.path, d.y))
    tr = DataLoader(Lesions(mk(train_df, 1), True), args.batch, sampler=sampler, num_workers=args.workers, pin_memory=True)
    va = DataLoader(Lesions(mk(val_df, 0), False), args.batch * 2, num_workers=args.workers)

    model = MelanoHybridLite(pretrained=True).to(dev)
    model.freeze_backbones(True)
    run_phase(model, tr, va, dev, args.fusion_epochs, 5e-4, args.accum, 99, "fusion")
    model.freeze_backbones(False)
    best = run_phase(model, tr, va, dev, args.finetune_epochs, 1e-5, args.accum, 5, "finetune")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "val_auc": best}, out)
    print(f"saved {out} (val AUC {best:.4f})")


if __name__ == "__main__":
    main()
