"""MelanoHybridLite: dual-backbone classifier with adaptive feature fusion.

A scaled-down take on the paper's Melano Hybrid Model. The YOLOv9 + Faster R-CNN
detectors are replaced by two lightweight classification backbones so the model
can be trained on a 6 GB GPU:
  * ResNet-50  -> fine-grained texture/boundary features (Faster R-CNN role)
  * EfficientNet-B0 -> fast global context features (YOLOv9 role)
Their feature maps are fused with channel-wise adaptive attention (paper eq. 1-2),
refined by multi-head self-attention (eq. 5) and fed to a single melanoma logit.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

FUSED_CH = 256


class AdaptiveFusion(nn.Module):
    def __init__(self, ch_a, ch_b, out_ch=FUSED_CH, heads=8):
        super().__init__()
        self.proj_a = nn.Conv2d(ch_a, out_ch, 1)
        self.proj_b = nn.Conv2d(ch_b, out_ch, 1)
        self.gate = nn.Sequential(nn.Linear(out_ch * 2, out_ch), nn.Sigmoid())
        self.msa = nn.MultiheadAttention(out_ch, heads, batch_first=True)
        self.norm = nn.LayerNorm(out_ch)

    def forward(self, fa, fb):
        fa = self.proj_a(fa)
        fb = self.proj_b(fb)
        if fb.shape[-2:] != fa.shape[-2:]:
            fb = F.interpolate(fb, size=fa.shape[-2:], mode="bilinear", align_corners=False)
        pooled = torch.cat([fa.mean((2, 3)), fb.mean((2, 3))], dim=1)
        s = self.gate(pooled)[:, :, None, None]           # S = sigmoid(FC(GAP(Fa ⊕ Fb)))
        fused = s * fa + (1 - s) * fb                      # S⊗Fa + (1-S)⊗Fb
        b, c, h, w = fused.shape
        seq = fused.flatten(2).transpose(1, 2)             # B, HW, C
        attn, _ = self.msa(seq, seq, seq)
        seq = self.norm(seq + attn)                        # MSA(F) + F
        return seq.transpose(1, 2).reshape(b, c, h, w), s.flatten(1).mean(1)


class MelanoHybridLite(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        rw = models.ResNet50_Weights.DEFAULT if pretrained else None
        ew = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        resnet = models.resnet50(weights=rw)
        self.res = nn.Sequential(*list(resnet.children())[:-2])      # -> 2048 ch
        self.eff = models.efficientnet_b0(weights=ew).features       # -> 1280 ch
        self.fusion = AdaptiveFusion(2048, 1280)
        self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(FUSED_CH, 1))

    def forward(self, x, return_maps=False):
        fused, gate = self.fusion(self.res(x), self.eff(x))
        logit = self.head(fused.mean((2, 3))).squeeze(1)
        return (logit, fused, gate) if return_maps else logit

    def freeze_backbones(self, frozen=True):
        for p in list(self.res.parameters()) + list(self.eff.parameters()):
            p.requires_grad = not frozen
