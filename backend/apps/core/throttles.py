import hashlib

from rest_framework.throttling import AnonRateThrottle as _AnonRateThrottle
from rest_framework.throttling import SimpleRateThrottle as _SimpleRateThrottle

from apps.core.net import proxied_client_ip


class _ProxyAwareIdent:
    """Behind the Cloudflare proxy every request comes from Cloudflare; use the visitor's IP it reports."""

    def get_ident(self, request):
        return proxied_client_ip(request) or super().get_ident(request)


class AnonRateThrottle(_ProxyAwareIdent, _AnonRateThrottle):
    pass


class SimpleRateThrottle(_ProxyAwareIdent, _SimpleRateThrottle):
    pass


class AttemptStartThrottle(AnonRateThrottle):
    scope = "attempt_start"


class PublicMetaThrottle(AnonRateThrottle):
    scope = "public_meta"


class AttemptTokenThrottle(SimpleRateThrottle):
    """Limits per exam attempt (token), not per IP: classrooms share one IP."""

    scope = "attempt_token"

    def get_cache_key(self, request, view):
        token = request.headers.get("X-Attempt-Token", "")
        if not token:
            return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
        ident = hashlib.sha256(token.encode()).hexdigest()[:32]
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AdminLoginThrottle(AnonRateThrottle):
    scope = "admin_login"


class AdminThrottle(SimpleRateThrottle):
    scope = "admin"

    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user and request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
