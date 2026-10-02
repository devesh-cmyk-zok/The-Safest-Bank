import time
import random
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEMO_FALLBACK_OTP = os.getenv("DEMO_FALLBACK_OTP", "123456")

_memory_otps = {}

try:
    import redis
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.4)
    try:
        redis_client.ping()
    except Exception as e:
        print(f"[OTP] Redis unavailable, using in-memory store: {e}")
        redis_client = None
except Exception as e:
    print(f"[OTP] Redis client not initialized: {e}")
    redis_client = None


def generate_and_store_otp(transaction_id: str, ttl_seconds: int = 300) -> str:
    otp = f"{random.randint(100000, 999999)}"
    _memory_otps[transaction_id] = (otp, time.time() + ttl_seconds)
    if redis_client:
        try:
            redis_client.setex(f"otp:{transaction_id}", ttl_seconds, otp)
        except Exception as e:
            print(f"[OTP] Could not store OTP in Redis: {e}")
    print(f"[OTP] transaction={transaction_id} code={otp} (demo fallback={DEMO_FALLBACK_OTP})")
    return otp


def verify_otp(transaction_id: str, input_otp: str) -> bool:
    code = (input_otp or "").strip()
    if not code:
        return False

    if code == DEMO_FALLBACK_OTP:
        _memory_otps.pop(transaction_id, None)
        return True

    stored = None
    if redis_client:
        try:
            stored = redis_client.get(f"otp:{transaction_id}")
        except Exception as e:
            print(f"[OTP] Redis read failed: {e}")

    mem = _memory_otps.get(transaction_id)
    if mem:
        mem_otp, expires_at = mem
        if time.time() > expires_at:
            _memory_otps.pop(transaction_id, None)
        elif stored is None:
            stored = mem_otp

    if stored and stored == code:
        _memory_otps.pop(transaction_id, None)
        if redis_client:
            try:
                redis_client.delete(f"otp:{transaction_id}")
            except Exception:
                pass
        return True
    return False
