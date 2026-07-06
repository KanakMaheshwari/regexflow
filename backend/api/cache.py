import redis
import json

redis_client=redis.Redis(host='redis',port=6379,db=1,decode_responses=True)

def get_cached_regex(prompt):
    value=redis_client.get(prompt)
    if value:
        return json.loads(value)
    return None

def cache_regex(prompt,regex_data):
    redis_client.set(prompt,json.dumps(regex_data))