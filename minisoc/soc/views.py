import base64
import io
from datetime import timedelta

import pyotp
import qrcode
import qrcode.image.svg
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Alert, Endpoint, MFADevice, SecurityEvent
from .services import get_ip, record_event


def _qr_data_uri(uri):
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def _check_code(request, secret):
    """Prüft den 6-stelligen Code und schreibt das Ergebnis ins Event-Log."""
    ok = pyotp.TOTP(secret).verify(request.POST.get("code", "").strip(), valid_window=1)
    record_event(SecurityEvent.Type.MFA_OK if ok else SecurityEvent.Type.MFA_FAIL,
                 request.user.get_username(), get_ip(request))
    if ok:
        request.session["mfa_verified"] = True
    return ok


@login_required
def mfa_setup(request):
    device, _ = MFADevice.objects.get_or_create(user=request.user, defaults={"secret": pyotp.random_base32()})
    if device.confirmed:
        # Wichtig: kein erneutes Enrollment, sonst könnte man MFA mit einem neuen Secret umgehen.
        return redirect("dashboard")
    error = None
    if request.method == "POST":
        if _check_code(request, device.secret):
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            return redirect("dashboard")
        error = "Der Code ist ungültig. Prüfe die Uhrzeit deines Handys und versuche es erneut."
    uri = pyotp.TOTP(device.secret).provisioning_uri(name=request.user.get_username(), issuer_name="MiniSOC")
    return render(request, "soc/mfa.html", {"qr": _qr_data_uri(uri), "secret": device.secret, "error": error})


@login_required
def mfa_verify(request):
    device = MFADevice.objects.filter(user=request.user, confirmed=True).first()
    if not device:
        return redirect("mfa_setup")
    if request.session.get("mfa_verified"):
        return redirect("dashboard")
    error = None
    if request.method == "POST":
        if _check_code(request, device.secret):
            return redirect("dashboard")
        error = "Der Code ist ungültig."
    return render(request, "soc/mfa.html", {"error": error})


@login_required
@permission_required("soc.view_securityevent", raise_exception=True)  # RBAC über Django-Rechte
def dashboard(request):
    endpoints = list(Endpoint.objects.order_by("hostname"))
    return render(request, "soc/dashboard.html", {
        "alerts": Alert.objects.filter(acknowledged=False),
        "events": SecurityEvent.objects.all()[:15],
        "endpoints": endpoints,
        "events_24h": SecurityEvent.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24)).count(),
        "noncompliant": sum(not e.compliant for e in endpoints),
    })


@require_POST
@login_required
@permission_required("soc.change_alert", raise_exception=True)
def ack_alert(request, pk):
    alert = get_object_or_404(Alert, pk=pk)  # ORM = parametrisierte Queries -> kein SQL-Injection-Risiko (A03)
    alert.acknowledged = True
    alert.save(update_fields=["acknowledged"])
    return redirect("dashboard")
