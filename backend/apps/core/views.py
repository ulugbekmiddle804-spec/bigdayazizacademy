from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    status = {"db": False, "cache": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["db"] = True
    except Exception:  # pragma: no cover
        pass
    try:
        cache.set("health-check", "ok", 5)
        status["cache"] = cache.get("health-check") == "ok"
    except Exception:  # pragma: no cover
        pass
    ok = status["db"]
    return JsonResponse({"ok": ok, **status}, status=200 if ok else 503)
