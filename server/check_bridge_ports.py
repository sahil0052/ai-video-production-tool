import requests

for port in [9222, 9223, 9224]:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/status", timeout=2)
        print(f"Port {port} Status: {r.status_code} -> {r.text[:200]}")
    except Exception as e:
        print(f"Port {port}: Not listening ({e})")
