from datetime import date

from django.db import models


class Patient(models.Model):
    SEX_CHOICES = [("female", "Female"), ("male", "Male"), ("other", "Other")]
    SKIN_TYPES = [(str(i), t) for i, t in enumerate(["I", "II", "III", "IV", "V", "VI"], start=1)]

    full_name = models.CharField(max_length=120)
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    skin_type = models.CharField(max_length=1, choices=SKIN_TYPES, blank=True, help_text="Fitzpatrick type")
    medical_history = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def code(self):
        return f"P-{self.pk:05d}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        t = date.today()
        d = self.date_of_birth
        return t.year - d.year - ((t.month, t.day) < (d.month, d.day))

    def __str__(self):
        return f"{self.code} {self.full_name}"


class Scan(models.Model):
    patient = models.ForeignKey(Patient, null=True, blank=True, on_delete=models.CASCADE, related_name="scans")
    body_site = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to="scans/")
    heatmap = models.ImageField(upload_to="heatmaps/", blank=True)
    probability = models.FloatField()
    label = models.CharField(max_length=20)
    box = models.JSONField(null=True, blank=True)
    outline = models.JSONField(null=True, blank=True)
    model_trained = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
