import redis

class RedisConnector:
    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db)

    def set_key(self, key, value):
        return self.client.set(key, value)

    def get_key(self, key):
        value = self.client.get(key)
        return value.decode() if value else None

    def delete_key(self, key):
        return self.client.delete(key)

    def flush_db(self):
        return self.client.flushdb()

# Usage example
if __name__ == "__main__":
    redis_conn = RedisConnector()
    redis_conn.set_key("sample_key", "hello redis")
    value = redis_conn.get_key("sample_key")
    print(f"The value of 'sample_key' is: {value}")
    redis_conn.delete_key("sample_key")
