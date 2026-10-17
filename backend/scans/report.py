"""PDF scan report: patient/verdict summary plus the photo, segmented lesion and Grad-CAM++ heatmap."""
import io

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

from ml import inference

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#e2e8f0")
BRAND = colors.HexColor("#0f766e")
PANEL = colors.HexColor("#f8fafc")
RISK = {
    "high": ("Suspicious", "Recommend dermatologist review.", colors.HexColor("#dc2626"), colors.HexColor("#fef2f2")),
    "medium": ("Borderline", "Monitor and consider a follow-up.", colors.HexColor("#d97706"), colors.HexColor("#fffbeb")),
    "low": ("Low risk", "No immediate concern flagged by the model.", colors.HexColor("#16a34a"), colors.HexColor("#f0fdf4")),
}
PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

_ss = getSampleStyleSheet()
H = ParagraphStyle("h", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=INK, spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("b", parent=_ss["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=INK)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7.5, leading=10.5, textColor=MUTED)
CAP = ParagraphStyle("c", parent=SMALL, alignment=TA_CENTER)
CAP_T = ParagraphStyle("ct", parent=CAP, fontName="Helvetica-Bold", fontSize=9, textColor=INK)


def risk_key(p):
    return "high" if p >= 0.5 else "medium" if p >= 0.3 else "low"


def _png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


class FittedImage(Flowable):
    """Image scaled to fit a w*h box (aspect preserved, centred) on a light panel with a thin border."""

    def __init__(self, reader, size, w, h, placeholder=None):
        super().__init__()
        self.reader, self.size, self.w, self.h, self.placeholder = reader, size, w, h, placeholder

    def wrap(self, *_):
        return self.w, self.h

    def draw(self):
        c = self.canv
        c.setFillColor(PANEL)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.w, self.h, 4, fill=1, stroke=1)
        if self.reader is None:
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            for i, line in enumerate((self.placeholder or "Not available").split("\n")):
                c.drawCentredString(self.w / 2, self.h / 2 + 4 - i * 11, line)
            return
        iw, ih = self.size
        pad = 3
        s = min((self.w - 2 * pad) / iw, (self.h - 2 * pad) / ih)
        dw, dh = iw * s, ih * s
        c.drawImage(self.reader, (self.w - dw) / 2, (self.h - dh) / 2, dw, dh)


class Bar(Flowable):
    def __init__(self, p, color, w):
        super().__init__()
        self.p, self.color, self.w = p, color, w

    def wrap(self, *_):
        return self.w, 7

    def draw(self):
        c = self.canv
        c.setFillColor(LINE)
        c.roundRect(0, 0, self.w, 6, 3, fill=1, stroke=0)
        c.setFillColor(self.color)
        c.roundRect(0, 0, max(6, self.w * self.p), 6, 3, fill=1, stroke=0)
        c.setStrokeColor(INK)  # 50% decision threshold
        c.setLineWidth(0.8)
        c.line(self.w * 0.5, -2, self.w * 0.5, 8)


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, PAGE_H - 30 * mm, PAGE_W, 30 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(MARGIN, PAGE_H - 15 * mm, "MelanoScan")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(MARGIN, PAGE_H - 21.5 * mm, "Skin lesion screening report")
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 15 * mm, f"Scan #{doc.scan.pk}")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 21.5 * mm, doc.scan.created_at.strftime("%d %b %Y, %H:%M"))
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN, 9.5 * mm, "Research prototype - screening aid only, not a medical device or a diagnosis.")
    canvas.drawRightString(PAGE_W - MARGIN, 9.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _kv(rows):
    t = Table([[Paragraph(k, SMALL), Paragraph(v or "-", BODY)] for k, v in rows], colWidths=[28 * mm, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def build_pdf(scan):
    """Render the report for a saved Scan and return the PDF bytes."""
    with Image.open(scan.image.path) as im:
        a = inference.analyze(im)
    key = risk_key(scan.probability)
    title, advice, color, tint = RISK[key]
    pat = scan.patient

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=36 * mm, bottomMargin=20 * mm,
                          title=f"MelanoScan report #{scan.pk}", author="MelanoScan")
    doc.scan = scan
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(MARGIN, 20 * mm, CONTENT_W, PAGE_H - 56 * mm, id="f",
                                                              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=_on_page)])
    story = []

    # Patient + scan details
    left = _kv([
        ("Patient", f"{pat.full_name} ({pat.code})" if pat else "Quick scan (no patient)"),
        ("Age / sex", f"{pat.age if pat and pat.age is not None else '-'} / {pat.get_sex_display() if pat and pat.sex else '-'}"),
        ("Skin type", f"Fitzpatrick {pat.get_skin_type_display()}" if pat and pat.skin_type else "-"),
    ])
    right = _kv([
        ("Body site", scan.body_site or "Not specified"),
        ("Scan date", scan.created_at.strftime("%d %b %Y, %H:%M")),
        ("Model", "MelanoHybridLite" + ("" if scan.model_trained else " (untrained)")),
    ])
    info = Table([[left, right]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [info, Spacer(1, 4 * mm)]

    # Verdict card
    pct = f"{scan.probability * 100:.1f}%"
    verdict = Table([[Paragraph(f'<font size="17" color="{color.hexval()}"><b>{title}</b></font>', BODY),
                      Paragraph(f'<font size="17" color="{color.hexval()}"><b>{pct}</b></font><br/>'
                                f'<font size="8" color="#64748b">melanoma probability</font>', ParagraphStyle("r", parent=BODY, alignment=2, leading=19))],
                     [Paragraph(advice, BODY), ""],
                     [Bar(scan.probability, color, CONTENT_W - 12 * mm), ""],
                     [Paragraph("0%  -  decision threshold at 50% (tick)  -  100%", SMALL), ""]],
                    colWidths=[CONTENT_W * 0.6, CONTENT_W * 0.4])
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), tint), ("BOX", (0, 0), (-1, -1), 0.8, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 4 * mm), ("BOTTOMPADDING", (0, -1), (-1, -1), 3 * mm),
        ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)), ("SPAN", (0, 3), (1, 3)),
        ("TOPPADDING", (0, 2), (-1, 2), 4), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [verdict]
    if not scan.model_trained:
        story += [Spacer(1, 2 * mm), Paragraph("<b>Note:</b> recorded with an untrained model - placeholder result.", SMALL)]

    # Images
    story += [Paragraph("Visual analysis", H)]
    gap = 4 * mm
    cw = (CONTENT_W - 2 * gap) / 3
    ih = cw * 1.0
    h, w = a["image"].shape[:2]
    lesion = a["lesion"]
    panels = [
        (FittedImage(_png(a["image"]), (w, h), cw, ih), "Original photo", "As uploaded"),
        (FittedImage(_png(lesion) if lesion is not None else None, lesion.shape[1::-1] if lesion is not None else (1, 1), cw, ih,
                     "Lesion not reliably\nsegmented"),
         "Segmented lesion", "Outline from U-Net; surrounding skin dimmed"),
        (FittedImage(_png(a["cam_overlay"]), (w, h), cw, ih), "Grad-CAM++ heatmap", "Red = regions driving the prediction"),
    ]
    grid = Table([[p[0] for p in panels], [Paragraph(p[1], CAP_T) for p in panels], [Paragraph(p[2], CAP) for p in panels]],
                 colWidths=[cw] * 3, hAlign="LEFT")
    grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), gap), ("RIGHTPADDING", (2, 0), (2, -1), 0),
                              ("TOPPADDING", (0, 1), (-1, 1), 4), ("TOPPADDING", (0, 2), (-1, 2), 0)]))
    story += [grid]

    # Notes
    story += [Paragraph("Clinical notes", H), Paragraph((scan.notes or "No notes recorded.").replace("\n", "<br/>"), BODY)]
    if pat and pat.medical_history:
        story += [Paragraph("Medical history", H), Paragraph(pat.medical_history.replace("\n", "<br/>"), BODY)]

    # Method + disclaimer
    story += [Paragraph("About this result", H), KeepTogether([
        Paragraph("The probability comes from MelanoHybridLite, a ResNet-50 + EfficientNet-B0 dual-backbone classifier with adaptive "
                  "feature fusion, trained on HAM10000. Grad-CAM++ highlights the image regions that most influenced the score; "
                  "the lesion outline comes from a separate ResNet-34 U-Net. On the held-out validation split the classifier reached "
                  "an AUC of about 0.90 (sensitivity 0.86, specificity 0.79), so false positives and missed lesions both occur.", SMALL),
        Spacer(1, 2 * mm),
        Paragraph("<b>Disclaimer:</b> this report is a screening aid generated by a research prototype. It is not a diagnosis and must "
                  "not replace examination by a qualified clinician. Any lesion that is changing, bleeding or concerning should be "
                  "reviewed by a dermatologist regardless of this result.", SMALL)])]
    doc.build(story)
    return buf.getvalue()
