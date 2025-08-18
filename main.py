#!/usr/bin/env python3
import requests
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add as many URLs as you want here
URLS = [
    "https://rag-api-807h.onrender.com/file_summary",
    "https://eu-trade-scraper-api.onrender.com/docs",
    # "https://another-api.example.com/ping",
]

def ping_backend(url: str):
    try:
        print(f"{datetime.datetime.now()}: Pinging {url}")
        response = requests.get(url, timeout=30)
        print(f"{url} → Response: {response.status_code}")
        if response.status_code == 200:
            print(f"{url} → Backend is alive")
        else:
            print(f"{url} → ⚠️ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"{url} → Error: {e}")

def ping_all(urls):
    # run them "at once" with a small thread pool
    max_workers = min(len(urls), 10) or 1
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(ping_backend, url): url for url in urls}
        for _ in as_completed(futures):
            pass  # output is printed inside ping_backend

if __name__ == "__main__":
    ping_all(URLS)  # ping all once, then exit
