"""SIEM-Grundprinzip: Events sammeln -> normalisieren -> korrelieren -> alarmieren."""
from datetime import timedelta

from django.utils import timezone

from .models import Alert, SecurityEvent

FAIL_TYPES = [SecurityEvent.Type.LOGIN_FAIL, SecurityEvent.Type.MFA_FAIL]
THRESHOLD = 5                      # ab so vielen Fehlversuchen ...
WINDOW = timedelta(minutes=10)     # ... innerhalb dieses Zeitfensters gibt es einen Alert


def get_ip(request):
    # Bewusst nur REMOTE_ADDR: X-Forwarded-For kann ein Angreifer selbst setzen.
    return request.META.get("REMOTE_ADDR") if request else None


def record_event(event_type, username="", ip=None):
    # A09 Logging: wir loggen Benutzername + IP, aber niemals Passwörter oder Codes.
    event = SecurityEvent.objects.create(event_type=event_type, username=str(username)[:150], ip=ip)
    if event_type in FAIL_TYPES and ip:
        correlate_bruteforce(ip)
    return event


def correlate_bruteforce(ip):
    """Korrelationsregel: viele Fehlversuche von einer IP in kurzer Zeit = Brute-Force-Verdacht."""
    since = timezone.now() - WINDOW
    failures = SecurityEvent.objects.filter(event_type__in=FAIL_TYPES, ip=ip, created_at__gte=since).count()
    already_alerted = Alert.objects.filter(rule="BRUTE_FORCE", details__contains=ip, created_at__gte=since).exists()
    if failures >= THRESHOLD and not already_alerted:
        Alert.objects.create(
            rule="BRUTE_FORCE",
            severity=Alert.Severity.HIGH,
            details=f"{failures} fehlgeschlagene Anmeldungen von {ip} in 10 Minuten",
        )
