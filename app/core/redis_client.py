import redis
from functools import lru_cache

@lru_cache
def get_redis():
    return redis.Redis(
        host = "localhost",
        port = 6379,
        decode_responses = True
    )

def test_redis():
    try:
        r = get_redis()
        r.ping()
        print("Redis 连接成功")
        return True
    except Exception as e:
        print(f"Redis连接失败: {e}")
        return False
