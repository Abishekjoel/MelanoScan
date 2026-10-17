from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import HttpResponse
from django.db.models.functions import TruncDate
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ml import inference

from .models import Patient, Scan
from .report import build_pdf
from .serializers import PatientSerializer, ScanSerializer

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}


class PredictView(APIView):
    """POST an image (+ optional patient, body_site, notes) -> saved scan with prediction."""

    def post(self, request):
        upload = request.FILES.get("image")
        if upload is None:
            return Response({"error": "No 'image' file provided."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > settings.MAX_UPLOAD_BYTES:
            return Response({"error": "Image too large (max 10 MB)."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        patient = None
        if request.data.get("patient"):
            patient = Patient.objects.filter(pk=request.data["patient"]).first()
            if patient is None:
                return Response({"error": "Patient not found."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            img = Image.open(upload)
            if img.format not in ALLOWED_FORMATS:
                raise UnidentifiedImageError
            img.load()
        except (UnidentifiedImageError, OSError):
            return Response({"error": "Unsupported or corrupt image."}, status=status.HTTP_400_BAD_REQUEST)

        result = inference.predict(img)
        scan = Scan(
            patient=patient,
            body_site=request.data.get("body_site", "")[:60],
            notes=request.data.get("notes", ""),
            probability=result["probability"],
            label=result["label"],
            box=result["box"],
            outline=result["outline"],
            model_trained=result["model_trained"],
        )
        upload.seek(0)
        scan.image.save(upload.name, upload, save=False)
        scan.heatmap.save("heatmap.png", ContentFile(result["heatmap_png"]), save=False)
        scan.save()
        return Response(ScanSerializer(scan, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PatientListCreate(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        qs = Patient.objects.all()
        q = self.request.query_params.get("q")
        if q:
            cond = Q(full_name__icontains=q) | Q(phone__icontains=q)
            if q.upper().startswith("P-") and q[2:].isdigit():
                cond |= Q(pk=int(q[2:]))
            qs = qs.filter(cond)
        return qs


class PatientDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        return Patient.objects.all()


class ScanList(generics.ListAPIView):
    serializer_class = ScanSerializer

    def get_queryset(self):
        qs = Scan.objects.select_related("patient")
        p = self.request.query_params
        if p.get("patient"):
            qs = qs.filter(patient_id=p["patient"])
        if p.get("label") in ("melanoma", "non-melanoma"):
            qs = qs.filter(label=p["label"])
        return qs


class ScanDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScanSerializer

    def get_queryset(self):
        return Scan.objects.select_related("patient")

    def perform_destroy(self, instance):
        instance.image.delete(save=False)
        instance.heatmap.delete(save=False)
        instance.delete()


class ScanReportPDF(APIView):
    def get(self, request, pk):
        scan = get_object_or_404(Scan.objects.select_related("patient"), pk=pk)
        resp = HttpResponse(build_pdf(scan), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="melanoscan-report-{scan.pk}.pdf"'
        return resp


class StatsView(APIView):
    def get(self, request):
        now = timezone.now()
        scans = Scan.objects.all()
        days = 14
        start = (now - timedelta(days=days - 1)).date()
        per_day = {
            r["d"]: r["n"]
            for r in scans.filter(created_at__date__gte=start)
            .annotate(d=TruncDate("created_at")).values("d").annotate(n=Count("id"))
        }
        series = [
            {"date": (start + timedelta(days=i)).isoformat(), "count": per_day.get(start + timedelta(days=i), 0)}
            for i in range(days)
        ]
        total = scans.count()
        flagged = scans.filter(label="melanoma").count()
        return Response({
            "patients": Patient.objects.count(),
            "scans": total,
            "flagged": flagged,
            "flagged_rate": flagged / total if total else 0,
            "scans_7d": scans.filter(created_at__gte=now - timedelta(days=7)).count(),
            "per_day": series,
            "risk": {
                "low": scans.filter(probability__lt=0.3).count(),
                "medium": scans.filter(probability__gte=0.3, probability__lt=0.5).count(),
                "high": scans.filter(probability__gte=0.5).count(),
            },
            "recent": ScanSerializer(scans.select_related("patient")[:6], many=True, context={"request": request}).data,
        })


class HealthView(APIView):
    def get(self, request):
        _, trained = inference.get_model()
        return Response({"status": "ok", "model_trained": trained, "segmentation": inference.get_seg_model() is not None})
