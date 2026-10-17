"""Preprocessing, prediction, lesion segmentation and Grad-CAM heatmap."""
import base64
import io
import threading

import cv2
import numpy as np
import torch
from django.conf import settings
from PIL import Image

from .model import MelanoHybridLite
from .seg_model import LesionUNet

IMG_SIZE = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
THRESHOLD = 0.5

_lock = threading.Lock()
_state = {"model": None, "loaded": False, "device": None, "seg": None, "seg_tried": False}
SEG_SIZE = 256


def get_model():
    """Lazily load the model once. Returns (model, has_trained_weights)."""
    with _lock:
        if _state["model"] is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = MelanoHybridLite(pretrained=False).to(device).eval()
            path = settings.MODEL_WEIGHTS_PATH
            if path.exists():
                ckpt = torch.load(path, map_location=device)
                model.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
                _state["loaded"] = True
            _state.update(model=model, device=device)
    return _state["model"], _state["loaded"]


def get_seg_model():
    """Lazily load the lesion U-Net; None if its weights haven't been trained yet."""
    with _lock:
        if not _state["seg_tried"]:
            _state["seg_tried"] = True
            path = settings.SEG_WEIGHTS_PATH
            if path.exists():
                device = _state["device"] or torch.device("cuda" if torch.cuda.is_available() else "cpu")
                net = LesionUNet(pretrained=False).to(device).eval()
                ckpt = torch.load(path, map_location=device)
                net.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
                _state["seg"] = net
    return _state["seg"]


def segment_lesion(img_rgb):
    """Predict the lesion mask and return {'box': {x,y,w,h}, 'outline': [[x,y],...]} (normalised
    0-1 coordinates), or None when there is no model or the result looks unreliable."""
    get_model()                                    # makes sure _state['device'] is set
    net = get_seg_model()
    if net is None:
        return None
    small = cv2.resize(img_rgb, (SEG_SIZE, SEG_SIZE), interpolation=cv2.INTER_AREA)
    x = torch.from_numpy(((small.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)).unsqueeze(0)
    with torch.no_grad():
        prob = torch.sigmoid(net(x.to(_state["device"]))).squeeze(0).cpu().numpy()
    mask = (prob > 0.5).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    comp = (labels == i).astype(np.uint8)
    area = comp.sum() / comp.size
    # Reject implausible results instead of showing a misleading box.
    if area < 0.005 or area > 0.85 or prob[comp > 0].mean() < 0.75:
        return None
    cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 0.004 * cv2.arcLength(c, True), True)[:, 0, :]
    bx, by, bw, bh = cv2.boundingRect(c)
    f = float(SEG_SIZE)
    return {
        "box": {"x": bx / f, "y": by / f, "w": bw / f, "h": bh / f},
        "outline": [[round(px / f, 4), round(py / f, 4)] for px, py in c],
    }


def preprocess(img_rgb):
    """CLAHE contrast enhancement (paper III-C) + resize + normalise."""
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    resized = cv2.resize(enhanced, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    arr = (resized.astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0)


def _gradcam(model, tensor, device):
    """Grad-CAM++ on the fused feature map (Chattopadhay et al., 2018)."""
    model.zero_grad()
    logit, fused, _ = model(tensor.to(device).requires_grad_(True), return_maps=True)
    fused.retain_grad()
    logit.sum().backward()
    g = fused.grad
    g2, g3 = g ** 2, g ** 3
    denom = 2 * g2 + fused.sum((2, 3), keepdim=True) * g3
    alpha = g2 / torch.where(denom != 0, denom, torch.ones_like(denom))
    weights = (alpha * torch.relu(g)).sum((2, 3), keepdim=True)
    cam = torch.relu((weights * fused).sum(1)).squeeze(0).detach().cpu().numpy()
    cam = cam - cam.min()
    return cam / cam.max() if cam.max() > 0 else cam


def overlay_array(img_rgb, cam):
    cam = cv2.resize(cam, (img_rgb.shape[1], img_rgb.shape[0]))
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    return (0.55 * img_rgb + 0.45 * heat).astype(np.uint8)


def _overlay_png(img_rgb, cam):
    buf = io.BytesIO()
    Image.fromarray(overlay_array(img_rgb, cam)).save(buf, format="PNG")
    return buf.getvalue()


def lesion_crop(img_rgb, outline, pad=0.12):
    """Lesion cut-out: background outside the segmented outline is dimmed, contour drawn, cropped to the box.
    Returns None when there is no outline."""
    if not outline:
        return None
    h, w = img_rgb.shape[:2]
    pts = np.array([[x * w, y * h] for x, y in outline], dtype=np.int32)
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [pts], 1)
    out = img_rgb.copy()
    out[mask == 0] = (out[mask == 0] * 0.18).astype(np.uint8)
    cv2.polylines(out, [pts], True, (0, 230, 160), max(2, round(min(h, w) / 220)), cv2.LINE_AA)
    x, y, bw, bh = cv2.boundingRect(pts)
    px, py = int(bw * pad), int(bh * pad)
    return out[max(0, y - py):min(h, y + bh + py), max(0, x - px):min(w, x + bw + px)]


def analyze(pil_image):
    """Everything the PDF report needs: probability, lesion outline, Grad-CAM++ overlay and lesion crop."""
    img_rgb = np.array(pil_image.convert("RGB"))
    model, trained = get_model()
    tensor = preprocess(img_rgb)
    cam = _gradcam(model, tensor, _state["device"])
    with torch.no_grad():
        prob = torch.sigmoid(model(tensor.to(_state["device"]))).item()
    lesion = segment_lesion(img_rgb)
    outline = lesion["outline"] if lesion else None
    return {
        "probability": prob, "model_trained": trained, "image": img_rgb,
        "cam_overlay": overlay_array(img_rgb, cam), "lesion": lesion_crop(img_rgb, outline),
    }


def predict(pil_image):
    """Returns dict with probability, label, lesion box/outline (or None), heatmap PNG bytes, model status."""
    img_rgb = np.array(pil_image.convert("RGB"))
    model, trained = get_model()
    device = _state["device"]
    tensor = preprocess(img_rgb)
    cam = _gradcam(model, tensor, device)
    with torch.no_grad():
        prob = torch.sigmoid(model(tensor.to(device))).item()
    lesion = segment_lesion(img_rgb)
    return {
        "probability": prob,
        "box": lesion["box"] if lesion else None,
        "outline": lesion["outline"] if lesion else None,
        "label": "melanoma" if prob >= THRESHOLD else "non-melanoma",
        "heatmap_png": _overlay_png(img_rgb, cam),
        "model_trained": trained,
    }


def png_to_data_url(png_bytes):
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()
