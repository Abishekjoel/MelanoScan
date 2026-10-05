from rest_framework import serializers

from .models import Patient, Scan


class PatientSerializer(serializers.ModelSerializer):
    code = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    scan_count = serializers.SerializerMethodField()
    last_scan = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id", "code", "full_name", "date_of_birth", "age", "sex", "phone", "email", "skin_type",
            "medical_history", "notes", "created_at", "scan_count", "last_scan",
        ]

    def get_scan_count(self, obj):
        return obj.scans.count()

    def get_last_scan(self, obj):
        s = obj.scans.first()
        return {"label": s.label, "probability": s.probability, "created_at": s.created_at} if s else None


class ScanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    heatmap = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source="patient.full_name", read_only=True, default=None)
    patient_code = serializers.CharField(source="patient.code", read_only=True, default=None)

    class Meta:
        model = Scan
        fields = [
            "id", "patient", "patient_name", "patient_code", "body_site", "notes", "image", "heatmap",
            "probability", "label", "box", "outline", "model_trained", "created_at",
        ]
        read_only_fields = ["id", "image", "heatmap", "probability", "label", "box", "outline", "model_trained", "created_at"]

    def _url(self, f):
        request = self.context.get("request")
        return request.build_absolute_uri(f.url) if f and request else None

    def get_image(self, obj):
        return self._url(obj.image)

    def get_heatmap(self, obj):
        return self._url(obj.heatmap)
