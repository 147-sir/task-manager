import redis
from functools import lru_cache

@lru_cache
def get_redis():
    # 获取 Redis 连接
    return redis.Redis(
        host = "localhost",
        port = 6379,
        decode_responses = True
    )

def test_redis():
    # 测试 Redis
    try:
        r = get_redis()
        r.ping()
        print("Redis 连接成功")
        return True
    except Exception as e:
        print(f"Redis 测试失败: {e}")
        return False