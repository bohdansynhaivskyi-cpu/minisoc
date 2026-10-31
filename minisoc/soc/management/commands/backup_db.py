import hashlib
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Erstellt ein Backup (JSON) mit SHA-256-Prüfsumme und löscht alte Backups (Rotation)."

    def handle(self, *args, **options):
        folder = settings.BACKUP_DIR
        folder.mkdir(mode=0o700, exist_ok=True)
        target = folder / f"backup-{datetime.now():%Y%m%d-%H%M%S}.json"
        call_command("dumpdata", exclude=["contenttypes", "auth.permission", "sessions"],
                     indent=2, output=str(target))
        target.chmod(0o600)  # Backup enthält Passwort-Hashes und MFA-Secrets -> nur Eigentümer
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        target.with_suffix(".json.sha256").write_text(f"{digest}  {target.name}\n")

        for old in sorted(folder.glob("backup-*.json"))[:-settings.BACKUP_KEEP]:  # Rotation
            old.unlink()
            old.with_suffix(".json.sha256").unlink(missing_ok=True)
        self.stdout.write(self.style.SUCCESS(f"Backup erstellt: {target}"))
