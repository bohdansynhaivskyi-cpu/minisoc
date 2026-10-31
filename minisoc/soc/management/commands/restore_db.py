import hashlib
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Stellt ein Backup wieder her. Prüft vorher die SHA-256-Prüfsumme (Integrität)."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Pfad zur backup-*.json")

    def handle(self, *args, file, **options):
        path = Path(file)
        checksum_file = path.with_suffix(".json.sha256")
        if not path.exists() or not checksum_file.exists():
            raise CommandError("Backup oder Prüfsummen-Datei fehlt.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum_file.read_text().split()[0]:
            raise CommandError("Prüfsumme stimmt nicht – Backup defekt oder manipuliert. Abbruch.")
        call_command("loaddata", str(path))
        self.stdout.write(self.style.SUCCESS("Wiederherstellung abgeschlossen."))
