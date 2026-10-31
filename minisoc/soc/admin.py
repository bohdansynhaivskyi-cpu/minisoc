from django.contrib import admin

from .models import Alert, Endpoint, SecurityEvent

# MFADevice ist absichtlich NICHT im Admin registriert (enthält Secrets).


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Logs sind nur lesbar: A09 – Log-Integrität, niemand soll Spuren löschen können."""
    list_display = ("created_at", "event_type", "username", "ip")
    list_filter = ("event_type",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Alert)
admin.site.register(Endpoint)
