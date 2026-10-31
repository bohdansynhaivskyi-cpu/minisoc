from django.apps import AppConfig


class SocConfig(AppConfig):
    name = "soc"

    def ready(self):
        from . import signals  # noqa: F401  (registriert die Login-Signale)
