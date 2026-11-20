"""The visitor's IP address, also when the site runs behind the Cloudflare Pages proxy."""
import hmac

from django.conf import settings


def proxied_client_ip(request) -> str | None:
    """IP sent by our own proxy (functions/api in the frontend), trusted only with the shared secret."""
    secret = getattr(settings, "PROXY_SECRET", "")
    if not secret:
        return None
    sent = request.META.get("HTTP_X_PROXY_SECRET", "")
    if sent and hmac.compare_digest(sent, secret):
        ip = request.META.get("HTTP_X_CLIENT_IP", "").strip()
        return ip[:45] or None
    return None


def client_ip(request) -> str | None:
    return proxied_client_ip(request) or request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
