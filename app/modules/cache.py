import os
from gptcache import Cache
from gptcache.manager import manager_factory
from gptcache.processor.pre import get_content_func
from gptcache.adapter.api import init_similar_cache

# Init Redis Cache
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}"

def get_rag_cache():
    # Setup data manager: Redis for Scalar, Redis for Vector (jika similarity search cache diinginkan)
    # Untuk simplifikasi, kita pakai map exact match dulu agar cepat
    data_manager = manager_factory("redis,string", data_dir=redis_url, scalar_dir=redis_url)
    
    cache = Cache()
    cache.init(
        pre_embedding_func=get_content_func, # Hash konten user
        data_manager=data_manager
    )
    return cache