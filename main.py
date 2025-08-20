#!/usr/bin/env python3
import datetime as dt
import time
import random
import logging
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

import requests

# -------------------- Configuration --------------------
URLS: List[str] = [
    "https://rag-api-807h.onrender.com/file_summary",
    "https://eu-trade-scraper-api.onrender.com/",
    "https://watcher-fn3v.onrender.com/",
]

TIMEOUT_SECONDS = 8
RETRIES = 3
BACKOFF_BASE = 0.6
ACCEPTABLE_CODES = {200, 204}
ACCEPTABLE_REDIRECTS = {301, 302, 307, 308}
MAX_WORKERS = 8
USER_AGENT = "KeepAliveBot/1.3 (+https://github.com/you/keep-backend-alive)"

# -------------------- Logging setup --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("keepalive")

# -------------------- HTTP Session --------------------
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=32)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})


def _with_cache_bust(url: str) -> str:
    """Append a tiny cache-busting query param so CDNs/proxies don't 304 us to sleep."""
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query))
    q["_kick"] = str(int(time.time()))
    new_query = urlencode(q)
    return urlunparse(parsed._replace(query=new_query))


def _attempt(url: str) -> Tuple[bool, int, float, str]:
    """One attempt with HEAD → fallback GET. Returns (ok, status, latency, error)."""
    start = time.perf_counter()
    try:
        head = session.head(_with_cache_bust(url), allow_redirects=True, timeout=TIMEOUT_SECONDS)
        latency = time.perf_counter() - start
        sc = head.status_code

        if sc in ACCEPTABLE_CODES or sc in ACCEPTABLE_REDIRECTS:
            return True, sc, latency, ""

        # fallback GET
        start_get = time.perf_counter()
        get = session.get(_with_cache_bust(url), allow_redirects=True, timeout=TIMEOUT_SECONDS)
        sc = get.status_code
        latency = time.perf_counter() - start

        if sc in ACCEPTABLE_CODES or sc in ACCEPTABLE_REDIRECTS:
            return True, sc, latency, ""
        return False, sc, latency, f"Unexpected status {sc}"

    except requests.RequestException as e:
        latency = time.perf_counter() - start
        return False, -1, latency, str(e)


def ping_backend(url: str) -> dict:
    """Ping one backend with retries + logging."""
    log.info(f"Starting ping for {url}")
    for attempt in range(1, RETRIES + 1):
        ok, status, latency, err = _attempt(url)
        if ok:
            log.info(f"SUCCESS {url} → {status} in {latency*1000:.0f} ms (attempt {attempt})")
            return {"url": url, "ok": True, "status": status, "latency": latency, "attempts": attempt, "error": ""}

        log.warning(f"FAIL {url} attempt {attempt}/{RETRIES} → {status if status!=-1 else 'ERR'} ({err})")
        if attempt < RETRIES:
            sleep_s = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            log.debug(f"Retrying {url} after {sleep_s:.2f}s")
            time.sleep(sleep_s)

    log.error(f"FINAL FAIL {url} after {RETRIES} attempts")
    return {"url": url, "ok": False, "status": status, "latency": latency, "attempts": RETRIES, "error": err}


def ping_all(urls: List[str]):
    if not urls:
        log.error("No URLs configured.")
        return

    time.sleep(random.uniform(0, 0.6))  # jitter
    workers = max(1, min(len(urls), MAX_WORKERS))
    log.info(f"Launching ping for {len(urls)} URLs with {workers} workers")

    results = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(ping_backend, u): u for u in urls}
        for fut in as_completed(futures):
            results.append(fut.result())
    elapsed = time.perf_counter() - t0

    ok_n = sum(1 for r in results if r["ok"])
    fail_n = len(results) - ok_n
    slowest = max(results, key=lambda r: r["latency"]) if results else None
    fastest = min(results, key=lambda r: r["latency"]) if results else None

    log.info("— Summary —")
    log.info(f"Total: {len(results)} | OK: {ok_n} | Fail: {fail_n} | Wall time: {elapsed:.2f}s")
    if results:
        log.info(f"Fastest: {fastest['url']} → {fastest['status']} in {fastest['latency']*1000:.0f} ms")
        log.info(f"Slowest: {slowest['url']} → {slowest['status']} in {slowest['latency']*1000:.0f} ms")
        if fail_n:
            log.error("Failures:")
            for r in results:
                if not r["ok"]:
                    log.error(f"  - {r['url']} → {r['status'] if r['status']!=-1 else 'ERR'} "
                              f"after {r['attempts']} attempts ({r['error']})")


if __name__ == "__main__":
    ping_all(URLS)
