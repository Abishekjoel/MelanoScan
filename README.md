# MelanoScan

React + Django REST Framework app for melanoma screening, based on the idea of
*"A Hybrid Model for Early Melanoma Detection: Integrating YOLOv9 and Faster R-CNN"* (IEEE Access 2025).

> Research prototype. Not a medical device, not a diagnosis.

## What's here
- `backend/` — Django + DRF API (`/api/predict/`, `/api/scans/`, `/api/health/`) and the PyTorch model in `backend/ml/`
- `frontend/` — React (Vite) UI: upload, probability, Grad-CAM heatmap, scan history
- `training/train.py` — training script (phased: fusion warm-up, then end-to-end fine-tune)

## Model (MelanoHybridLite)
The paper's full model (YOLOv9 + Faster R-CNN + fusion) needs A100-class GPUs. This is a scaled-down
version of the same idea that trains on a 6 GB GPU: **ResNet-50 + EfficientNet-B0 backbones joined by
adaptive channel-attention fusion + multi-head self-attention**, with a focal loss, CLAHE preprocessing,
and Grad-CAM explanations. It does **not** reproduce the paper's reported numbers.

## App pages
Landing (`/`), dashboard, new scan (optionally attached to a patient), patients (search, add/edit),
patient detail (details + scans + risk trend), history (filter), scan report (notes, print).
There is no login: anyone who can reach the server can see all data. Add authentication before any shared or real use.

## Not in this repository
Datasets and trained weights are excluded (size and licensing). To use the app you need to:
1. Download HAM10000 (images + `HAM10000_metadata.csv`) and the Tschandl lesion segmentations into the project root.
2. `python training/prepare_ham10000.py`, then `python training/train.py --csv training/ham10000_labels.csv` and
   `python training/train_seg.py` to produce `backend/ml/weights/melano_lite.pt` and `lesion_unet.pt`.
3. Backend deps: `pip install -r backend/requirements.txt`; frontend: copy `frontend/.env.example` to `frontend/.env`.

## Run
```powershell
# backend
cd backend
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver        # http://127.0.0.1:8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                                     # http://localhost:5173
```

## Train (needed for meaningful predictions)
Until weights exist at `backend/ml/weights/melano_lite.pt`, the UI shows an "untrained model" warning.

1. Download ISIC 2020 (or HAM10000) from https://challenge.isic-archive.com / Kaggle.
2. Train:
   ```powershell
   backend\.venv\Scripts\python training\train.py --csv train.csv --images jpeg\train
   ```
   (or `--images DIR` with `benign/` and `melanoma/` subfolders). Split is patient-wise when `patient_id` exists.
3. Restart the backend; the health endpoint reports `model_trained: true`.

## Not yet done / caveats
- No authentication; the API is open (throttled to 60 req/min). Add auth before any real use.
- Dev settings (`DEBUG=True`, SQLite, local media). Harden for deployment.
- Paper-reported skin-type bias (lower sensitivity on Fitzpatrick V–VI) applies to these public datasets too.
