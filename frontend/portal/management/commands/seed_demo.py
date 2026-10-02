"""Create demo logins: one per seeded customer (see backend/seed.py) plus a SOC analyst."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from portal.models import PortalProfile

DEMO_PASSWORD = "demo123"  # demo only; printed in the README
CUSTOMERS = [  # username, bank account id, first, last (matches backend/seed.py CUSTOMERS)
    ("aarav", "usr_1001", "Aarav", "Sharma"),
    ("priya", "usr_1002", "Priya", "Patel"),
    ("rohan", "usr_1003", "Rohan", "Mehta"),
    ("ananya", "usr_1004", "Ananya", "Iyer"),
    ("vikram", "usr_1005", "Vikram", "Singh"),
]


class Command(BaseCommand):
    help = "Create demo customer and analyst logins (idempotent)."

    def handle(self, *args, **options):
        for username, bank_id, first, last in CUSTOMERS:
            user = self._user(username, first_name=first, last_name=last)
            PortalProfile.objects.update_or_create(user=user, defaults={"bank_user_id": bank_id})
        self._user("analyst", first_name="Meera", last_name="Kapoor", is_staff=True)
        names = ", ".join(c[0] for c in CUSTOMERS)
        self.stdout.write(f"Customers: {names} | SOC analyst: analyst | password: {DEMO_PASSWORD}")

    @staticmethod
    def _user(username, **fields):
        user, _ = User.objects.update_or_create(username=username, defaults=fields)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user
