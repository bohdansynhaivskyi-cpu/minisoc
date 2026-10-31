from django.shortcuts import redirect
from django.urls import reverse

from .models import MFADevice


class MFARequiredMiddleware:
    """Deny-by-default (A01 Broken Access Control): Wer eingeloggt ist, aber MFA
    noch nicht bestanden hat, kommt nur an Login/Logout/MFA-Seiten – auch nicht ins Admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.session.get("mfa_verified"):
            exempt = {reverse(n) for n in ("login", "logout", "mfa_setup", "mfa_verify")}
            if request.path not in exempt and not request.path.startswith("/static/"):
                has_mfa = MFADevice.objects.filter(user=request.user, confirmed=True).exists()
                return redirect("mfa_verify" if has_mfa else "mfa_setup")
        return self.get_response(request)
