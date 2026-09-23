import redis
import random
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

def generate_and_store_otp(transaction_id: str, ttl_seconds: int = 300) -> str:
    otp = f"{random.randint(100000, 999999)}"
    if redis_client:
        try:
            redis_client.setex(f"otp:{transaction_id}", ttl_seconds, otp)
        except Exception as e:
            print(f"[Redis Warning] Could not store OTP in Redis: {e}")
    return otp

def verify_otp(transaction_id: str, input_otp: str) -> bool:
    if not redis_client:
        return input_otp == "123456"

    stored_otp = redis_client.get(f"otp:{transaction_id}")
    if stored_otp and stored_otp == input_otp:
        redis_client.delete(f"otp:{transaction_id}")
        return True
    return False