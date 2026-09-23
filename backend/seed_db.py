import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect
from database.connection import SessionLocal, engine, Base
from database.models import User, Transaction

def seed_database():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("[Seed Engine] Initializing database schema...")

        # ----------------------------------------------------
        # 1. INSPECT MODEL FIELDS DYNAMICALLY
        # ----------------------------------------------------
        user_cols = {col.key for col in inspect(User).attrs}
        tx_cols = {col.key for col in inspect(Transaction).attrs}

        # ----------------------------------------------------
        # 2. SEED USERS
        # ----------------------------------------------------
        print("[Seed Engine] Seeding 10 diverse user profiles...")
        
        users_data = [
            {"id": "usr_1001", "name": "Aarav Sharma", "balance": 100000.0, "avg_daily_spend": 250.0},
            {"id": "usr_1002", "name": "Priya Patel", "balance": 100000.0, "avg_daily_spend": 180.0},
            {"id": "usr_1003", "name": "Rohan Mehta", "balance": 100000.0, "avg_daily_spend": 400.0},
            {"id": "usr_1004", "name": "Ananya Iyer", "balance": 100000.0, "avg_daily_spend": 150.0},
            {"id": "usr_1005", "name": "Vikram Singh", "balance": 100000.0, "avg_daily_spend": 600.0},
            {"id": "usr_1006", "name": "Sneha Gupta", "balance": 100000.0, "avg_daily_spend": 220.0},
            {"id": "usr_1007", "name": "Kabir Das", "balance": 100000.0, "avg_daily_spend": 310.0},
            {"id": "usr_1008", "name": "Neha Verma", "balance": 100000.0, "avg_daily_spend": 190.0},
            {"id": "usr_1009", "name": "Arjun Rao", "balance": 100000.0, "avg_daily_spend": 500.0},
            {"id": "usr_9999", "name": "Suspicious Mule Account", "balance": 100000.0, "avg_daily_spend": 50.0},
        ]

        for u in users_data:
            kwargs = {}
            if "id" in user_cols: kwargs["id"] = u["id"]
            if "full_name" in user_cols: kwargs["full_name"] = u["name"]
            elif "name" in user_cols: kwargs["name"] = u["name"]
            
            if "account_balance" in user_cols: kwargs["account_balance"] = u["balance"]
            elif "balance" in user_cols: kwargs["balance"] = u["balance"]

            # Merge any extra matching columns
            for k, v in u.items():
                if k in user_cols and k not in kwargs:
                    kwargs[k] = v

            db.merge(User(**kwargs))

        db.commit()

        # ----------------------------------------------------
        # 3. SEED HISTORICAL TRANSACTIONS
        # ----------------------------------------------------
        print("[Seed Engine] Generating 100+ historical transactions...")
        statuses = ["SETTLED", "SETTLED", "SETTLED", "SETTLED", "ESCROW_HELD", "AUTO_ABORTED"]
        now = datetime.now(timezone.utc)
        tx_count = 0

        for user in users_data:
            if user["id"] == "usr_9999":
                continue

            for i in range(12):
                tx_time = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59))
                status = random.choice(statuses)
                amount = round(random.uniform(100.0, user["avg_daily_spend"] * 1.5), 2)
                risk_score = round(random.uniform(0.05, 0.45), 3) if status == "SETTLED" else round(random.uniform(0.62, 0.94), 3)

                # Prepare payload map handling common attribute names
                raw_tx = {
                    "id": f"tx_{user['id']}_{i+1:03d}",
                    "sender_id": user["id"],
                    "user_id": user["id"],
                    "from_account_id": user["id"],
                    "receiver_id": "usr_1009" if user["id"] != "usr_1009" else "usr_1001",
                    "recipient_id": "usr_1009" if user["id"] != "usr_1009" else "usr_1001",
                    "to_account_id": "usr_1009" if user["id"] != "usr_1009" else "usr_1001",
                    "amount": amount,
                    "risk_score": risk_score,
                    "status": status,
                    "timestamp": tx_time,
                    "created_at": tx_time
                }

                # Only select parameters that exist in Transaction model
                tx_kwargs = {k: v for k, v in raw_tx.items() if k in tx_cols}
                db.merge(Transaction(**tx_kwargs))
                tx_count += 1

        db.commit()
        print(f"[Seed Engine] Successfully seeded {len(users_data)} users and {tx_count} historical transactions!")

    except Exception as e:
        db.rollback()
        print(f"[Seed Engine] Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()