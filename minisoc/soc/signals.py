from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .models import SecurityEvent
from .services import get_ip, record_event


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    record_event(SecurityEvent.Type.LOGIN_OK, user.get_username(), get_ip(request))


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    record_event(SecurityEvent.Type.LOGIN_FAIL, credentials.get("username", ""), get_ip(request))
