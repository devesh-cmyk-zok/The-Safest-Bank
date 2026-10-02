from functools import wraps

from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods


DEMO_PORTAL_USERS = {
    "aarav": {
        "password": "demo123",
        "user_id": "usr_1001",
        "full_name": "Aarav Sharma",
    },
    "priya": {
        "password": "demo123",
        "user_id": "usr_1002",
        "full_name": "Priya Patel",
    },
}


def portal_login_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.session.get("portal_authenticated"):
            return redirect("portal_login")
        return view_func(request, *args, **kwargs)

    return wrapped


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("portal_authenticated"):
        return redirect("dashboard")

    error = ""
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip().lower()
        password = request.POST.get("password") or ""
        profile = DEMO_PORTAL_USERS.get(username)
        if profile and profile["password"] == password:
            request.session["portal_authenticated"] = True
            request.session["portal_user_id"] = profile["user_id"]
            request.session["portal_user_name"] = profile["full_name"]
            return redirect("dashboard")
        error = "Invalid demo credentials. Use aarav / demo123."

    return render(request, "portal/login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("portal_login")


@portal_login_required
def dashboard_view(request):
    return render(request, "portal/transfer.html")


@portal_login_required
def transactions_view(request):
    return render(request, "portal/transactions.html")


@portal_login_required
def transfer_view(request):
    return render(request, "portal/send_money.html")


@portal_login_required
def fraud_shield_view(request):
    return render(request, "portal/fraud_shield.html")


@portal_login_required
def accounts_view(request):
    return render(request, "portal/accounts.html")
