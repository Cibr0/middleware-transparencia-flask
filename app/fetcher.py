import requests
import time
from datetime import datetime
from cache import cache


DEFAULT_TTL = 120
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5
TIMEOUT = 5

# Circuit breaker #
failure_count = 0
CIRCUIT_OPEN = False
FAILURE_THRESHOLD = 5
CIRCUIT_RESET_TIMEOUT = 30
last_failure_time = 0

# LAST FETCH INFO
LAST_FETCH_TIMESTAMP = None
LAST_FETCH_STATUS = None
LAST_FETCH_FALLBACK = False


def fetch_produtos(simular_erro=False):
    global failure_count, CIRCUIT_OPEN, last_failure_time
    global LAST_FETCH_TIMESTAMP, LAST_FETCH_STATUS, LAST_FETCH_FALLBACK

    cache_key = "produtos_all"

    cached = cache.get(cache_key)
    if cached and not simular_erro:
        LAST_FETCH_TIMESTAMP = datetime.utcnow().isoformat()
        LAST_FETCH_STATUS = 200
        LAST_FETCH_FALLBACK = False
        return cached, 200, False

    if CIRCUIT_OPEN:
        if time.time() - last_failure_time < CIRCUIT_RESET_TIMEOUT:
            fallback = cache.get_last_valid(cache_key)
            LAST_FETCH_TIMESTAMP = datetime.utcnow().isoformat()
            LAST_FETCH_STATUS = 503
            LAST_FETCH_FALLBACK = True

            if fallback:
                return fallback, 200, True
            return None, 503, True
        else:
            CIRCUIT_OPEN = False
            failure_count = 0

    for attempt in range(MAX_RETRIES):
        try:
            start = time.time()

            response = requests.get(
                "https://dummyjson.com/products",
                timeout=TIMEOUT
            )
            response.raise_for_status()

            latency = time.time() - start

            data = response.json()
            produtos = data["products"]

            if not simular_erro:
                cache.set(cache_key, produtos, ttl=DEFAULT_TTL)

            failure_count = 0

            #Atualiza last fetch 
            LAST_FETCH_TIMESTAMP = datetime.utcnow().isoformat()
            LAST_FETCH_STATUS = response.status_code
            LAST_FETCH_FALLBACK = False

            return produtos, 200, False

        except Exception as e:
            failure_count += 1
            last_failure_time = time.time()

            sleep_time = BACKOFF_FACTOR ** attempt
            time.sleep(sleep_time)

    if failure_count >= FAILURE_THRESHOLD:
        CIRCUIT_OPEN = True

    fallback = cache.get_last_valid(cache_key)

    #Atualiza last fetch 
    LAST_FETCH_TIMESTAMP = datetime.utcnow().isoformat()
    LAST_FETCH_STATUS = 503
    LAST_FETCH_FALLBACK = True

    if fallback:
        return fallback, 200, True

    return None, 503, True