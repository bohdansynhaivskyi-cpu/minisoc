import tempfile
from pathlib import Path

import pyotp
from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import Alert, MFADevice, SecurityEvent
from .services import record_event

FAIL = SecurityEvent.Type.LOGIN_FAIL


class SiemTests(TestCase):
    def test_bruteforce_creates_exactly_one_alert(self):
        for _ in range(7):
            record_event(FAIL, "admin", "203.0.113.7")
        self.assertEqual(Alert.objects.filter(rule="BRUTE_FORCE").count(), 1)

    def test_few_failures_create_no_alert(self):
        for _ in range(4):
            record_event(FAIL, "admin", "203.0.113.7")
        self.assertFalse(Alert.objects.exists())


class MfaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("anna", password="correct-horse-battery")
        self.user.user_permissions.add(Permission.objects.get(codename="view_securityevent"))
        self.secret = pyotp.random_base32()
        MFADevice.objects.create(user=self.user, secret=self.secret, confirmed=True)
        self.client.force_login(self.user)

    def test_dashboard_blocked_without_mfa(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/mfa/verify/", fetch_redirect_response=False)

    def test_wrong_code_is_logged_and_denied(self):
        self.client.post("/mfa/verify/", {"code": "000000"})
        self.assertTrue(SecurityEvent.objects.filter(event_type="MFA_FAIL").exists())
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_valid_code_grants_access(self):
        self.client.post("/mfa/verify/", {"code": pyotp.TOTP(self.secret).now()})
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_no_reenrollment_when_mfa_exists(self):
        self.client.get("/mfa/setup/")
        self.assertEqual(MFADevice.objects.get(user=self.user).secret, self.secret)


class BackupTests(TestCase):
    def test_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(BACKUP_DIR=Path(tmp)):
            record_event(FAIL, "x", "203.0.113.7")
            call_command("backup_db")
            backup = next(Path(tmp).glob("backup-*.json"))
            call_command("restore_db", str(backup))  # intakte Datei -> ok
            backup.write_text(backup.read_text() + " ")  # Manipulation
            with self.assertRaises(CommandError):
                call_command("restore_db", str(backup))
