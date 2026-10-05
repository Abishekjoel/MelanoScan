"""Train the lesion segmentation U-Net on HAM10000 + Tschandl lesion masks.

  python training/train_seg.py
Requires training/ham10000_labels.csv (run prepare_ham10000.py first) and the
HAM10000_segmentations_lesion_tschandl folder in the project root.
"""
import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from ml.seg_model import LesionUNet  # noqa: E402

SIZE = 256
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


class SegData(Dataset):
    def __init__(self, df, train):
        self.df, self.train = df.reset_index(drop=True), train

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        img = cv2.cvtColor(cv2.imread(r.path), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(r["mask_path"]), cv2.IMREAD_GRAYSCALE)
        img = cv2.resize(img, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (SIZE, SIZE), interpolation=cv2.INTER_NEAREST)
        if self.train:
            if random.random() < 0.5:
                img, mask = img[:, ::-1], mask[:, ::-1]
            if random.random() < 0.5:
                img, mask = img[::-1], mask[::-1]
            k = random.randint(0, 3)
            img, mask = np.rot90(img, k), np.rot90(mask, k)
            img = np.clip(img.astype(np.float32) * random.uniform(0.8, 1.2) + random.uniform(-15, 15), 0, 255)
        x = (np.ascontiguousarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
        return torch.from_numpy(x.transpose(2, 0, 1)), torch.from_numpy((np.ascontiguousarray(mask) > 127).astype(np.float32))


def dice_loss(logits, y):
    p = torch.sigmoid(logits)
    inter = (p * y).sum((1, 2))
    return 1 - ((2 * inter + 1) / (p.sum((1, 2)) + y.sum((1, 2)) + 1)).mean()


@torch.no_grad()
def evaluate(model, loader, dev):
    model.eval()
    ious = []
    for x, y in loader:
        pred = (torch.sigmoid(model(x.to(dev))) > 0.5).float().cpu()
        inter = (pred * y).sum((1, 2))
        union = pred.sum((1, 2)) + y.sum((1, 2)) - inter
        ious.append(((inter + 1) / (union + 1)))
    return torch.cat(ious).mean().item()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "backend/ml/weights/lesion_unet.pt"))
    args = ap.parse_args()

    df = pd.read_csv(ROOT / "training/ham10000_labels.csv")
    mask_dir = ROOT / "HAM10000_segmentations_lesion_tschandl"
    df["mask_path"] = df["image_name"].map(lambda n: mask_dir / f"{n}_segmentation.png")
    df = df[df["mask_path"].map(Path.exists)]

    # same lesion-wise split as the classifier (seed 42, 15% val)
    pats = df["patient_id"].unique()
    random.Random(42).shuffle(pats)
    val_p = set(pats[: int(len(pats) * 0.15)])
    is_val = df["patient_id"].isin(val_p)
    tr_df, va_df = df[~is_val], df[is_val]
    print(f"train {len(tr_df)} | val {len(va_df)}", flush=True)

    tr = DataLoader(SegData(tr_df, True), args.batch, shuffle=True, num_workers=args.workers, pin_memory=True, drop_last=True)
    va = DataLoader(SegData(va_df, False), args.batch * 2, num_workers=args.workers)

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LesionUNet().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")
    best = -1
    for ep in range(args.epochs):
        model.train()
        for x, y in tr:
            x, y = x.to(dev), y.to(dev)
            with torch.autocast("cuda", enabled=dev.type == "cuda"):
                logits = model(x).float()
            loss = F.binary_cross_entropy_with_logits(logits, y) + dice_loss(logits, y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        sched.step()
        iou = evaluate(model, va, dev)
        print(f"epoch {ep+1}/{args.epochs} val IoU {iou:.4f}", flush=True)
        if iou > best:
            best = iou
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            torch.save({"model": model.state_dict(), "val_iou": best}, args.out)
    print(f"saved {args.out} (val IoU {best:.4f})")


if __name__ == "__main__":
    main()
