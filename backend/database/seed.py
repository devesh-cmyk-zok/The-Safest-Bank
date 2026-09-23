"""
FILE: database/seed.py
PURPOSE:
    Populates initial test fixtures into the PostgreSQL ledger.
    Creates a pre-funded demo customer account ('usr_1001') with ₹1,00,000 balance
    so we can simulate incoming transfers, keystroke telemetry, and escrow quarantine.
"""

from database.connection import SessionLocal
import database.models as models

def seed_demo_user():
    db = SessionLocal()
    try:
        existing_user = db.query(models.User).filter(models.User.id == "usr_1001").first()
        if not existing_user:
            demo_user = models.User(
                id="usr_1001",
                full_name="Demo Customer",
                account_balance=100000.0  # ₹1,00,000 initial balance
            )
            db.add(demo_user)
            db.commit()
            print("Successfully created demo user 'usr_1001' with balance ₹1,00,000!")
        else:
            print("Demo user 'usr_1001' already exists.")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_user()