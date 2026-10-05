"""Small U-Net with a ResNet-34 encoder for lesion segmentation."""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


def _block(cin, cout):
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
    )


class LesionUNet(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        r = models.resnet34(weights=models.ResNet34_Weights.DEFAULT if pretrained else None)
        self.stem = nn.Sequential(r.conv1, r.bn1, r.relu)      # /2, 64
        self.pool = r.maxpool
        self.l1, self.l2, self.l3, self.l4 = r.layer1, r.layer2, r.layer3, r.layer4  # /4 64, /8 128, /16 256, /32 512
        self.d4 = _block(512 + 256, 256)
        self.d3 = _block(256 + 128, 128)
        self.d2 = _block(128 + 64, 64)
        self.d1 = _block(64 + 64, 32)
        self.out = nn.Conv2d(32, 1, 1)

    def forward(self, x):
        size = x.shape[-2:]
        s = self.stem(x)
        e1 = self.l1(self.pool(s))
        e2 = self.l2(e1)
        e3 = self.l3(e2)
        e4 = self.l4(e3)
        up = lambda a, b: torch.cat([F.interpolate(a, size=b.shape[-2:], mode="bilinear", align_corners=False), b], 1)
        d = self.d4(up(e4, e3))
        d = self.d3(up(d, e2))
        d = self.d2(up(d, e1))
        d = self.d1(up(d, s))
        return F.interpolate(self.out(d), size=size, mode="bilinear", align_corners=False).squeeze(1)
