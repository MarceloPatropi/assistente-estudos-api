import shelve
import hashlib
import json

CACHE_FILE = "openai_cache.db"

def make_cache_key(params: dict) -> str:
    """Gera uma chave única baseada nos parâmetros da requisição."""
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_str.encode()).hexdigest()

def get_cached_response(params: dict):
    key = make_cache_key(params)
    with shelve.open(CACHE_FILE) as cache:
        return cache.get(key)

def set_cached_response(params: dict, response):
    key = make_cache_key(params)
    with shelve.open(CACHE_FILE) as cache:
        cache[key] = response