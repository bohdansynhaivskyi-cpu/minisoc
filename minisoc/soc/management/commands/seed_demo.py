import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.utils import timezone

from soc.models import Endpoint, SecurityEvent
from soc.services import record_event


class Command(BaseCommand):
    help = "Legt Demo-Daten an: Analyst-Rolle, Benutzer, Endpoints und Events (löst einen Brute-Force-Alert aus)."

    def handle(self, *args, **options):
        # Rolle (RBAC): Analysten dürfen ansehen und Alerts bearbeiten, mehr nicht.
        group, _ = Group.objects.get_or_create(name="SOC Analyst")
        group.permissions.set(Permission.objects.filter(
            codename__in=["view_securityevent", "view_alert", "change_alert", "view_endpoint"]))

        user, created = get_user_model().objects.get_or_create(username="analyst")
        user.groups.add(group)
        if created:
            password = secrets.token_urlsafe(12)  # zufällig statt hartkodiert
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(f"Benutzer 'analyst' angelegt, Passwort: {password}"))

        today = timezone.localdate()
        for host, os_name, edr, enc, days in [
            ("WS-001", "Windows 11", True, True, 3),
            ("WS-014", "Windows 11", True, False, 12),
            ("LT-203", "macOS 15", False, True, 45),
            ("SRV-DB01", "Ubuntu 24.04", True, True, 5),
        ]:
            Endpoint.objects.update_or_create(hostname=host, defaults={
                "os": os_name, "edr_running": edr, "disk_encrypted": enc,
                "last_patch": today - timedelta(days=days)})

        if not SecurityEvent.objects.exists():
            for _ in range(6):  # simulierter Angriff -> Korrelationsregel schlägt an
                record_event(SecurityEvent.Type.LOGIN_FAIL, "admin", "203.0.113.7")
            # XSS-Demo: bösartiger Benutzername wird im Dashboard nur als Text angezeigt (Auto-Escaping)
            record_event(SecurityEvent.Type.LOGIN_FAIL, "<script>alert(1)</script>", "198.51.100.23")
        self.stdout.write(self.style.SUCCESS("Demo-Daten angelegt."))
