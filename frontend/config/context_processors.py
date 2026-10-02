from django.conf import settings


def integration(request):
    user_id = request.session.get("portal_user_id") or getattr(settings, "PORTAL_USER_ID", "usr_1001")
    user_name = request.session.get("portal_user_name") or "Aarav Sharma"
    return {
        "FASTAPI_BASE_URL": getattr(settings, "FASTAPI_BASE_URL", "http://127.0.0.1:8001"),
        "PORTAL_USER_ID": user_id,
        "PORTAL_USER_NAME": user_name,
        "PORTAL_AUTHENTICATED": bool(request.session.get("portal_authenticated")),
    }
