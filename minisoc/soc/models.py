from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class MFADevice(models.Model):
    """TOTP-Gerät (Authenticator-App) eines Benutzers. IAM/MFA."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Hinweis: In Produktion würde man das Secret verschlüsselt speichern.
    secret = models.CharField(max_length=32)
    confirmed = models.BooleanField(default=False)


class SecurityEvent(models.Model):
    """Ein Log-Eintrag – die 'Rohdaten' eines SIEM."""
    class Type(models.TextChoices):
        LOGIN_OK = "LOGIN_OK", "Login erfolgreich"
        LOGIN_FAIL = "LOGIN_FAIL", "Login fehlgeschlagen"
        MFA_OK = "MFA_OK", "MFA bestanden"
        MFA_FAIL = "MFA_FAIL", "MFA fehlgeschlagen"

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    event_type = models.CharField(max_length=20, choices=Type.choices)
    username = models.CharField(max_length=150, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Alert(models.Model):
    """Ergebnis einer Korrelationsregel (SIEM-Alert)."""
    class Severity(models.TextChoices):
        MEDIUM = "MEDIUM", "Mittel"
        HIGH = "HIGH", "Hoch"

    created_at = models.DateTimeField(default=timezone.now)
    rule = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    details = models.TextField()
    acknowledged = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class Endpoint(models.Model):
    """Ein Client/Server mit Compliance-Status (Intune/EDR-Gedanke)."""
    hostname = models.CharField(max_length=100, unique=True)
    os = models.CharField(max_length=50)
    edr_running = models.BooleanField(default=True)
    disk_encrypted = models.BooleanField(default=True)
    last_patch = models.DateField()

    MAX_PATCH_AGE_DAYS = 30

    @property
    def issues(self):
        problems = []
        if not self.edr_running:
            problems.append("EDR-Agent läuft nicht")
        if not self.disk_encrypted:
            problems.append("Festplatte nicht verschlüsselt")
        age = (timezone.localdate() - self.last_patch).days
        if age > self.MAX_PATCH_AGE_DAYS:
            problems.append(f"Letzter Patch vor {age} Tagen")
        return problems

    @property
    def compliant(self):
        return not self.issues

    def __str__(self):
        return self.hostname
