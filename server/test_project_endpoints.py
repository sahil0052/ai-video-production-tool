import requests

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

endpoints = [
    ("GET", f"https://aisandbox-pa.googleapis.com/v1/projects?key={API_KEY}"),
    ("GET", f"https://aisandbox-pa.googleapis.com/v1/users/me/projects?key={API_KEY}"),
    ("GET", f"https://aisandbox-pa.googleapis.com/v1/flow/projects?key={API_KEY}"),
    ("POST", f"https://aisandbox-pa.googleapis.com/v1/projects?key={API_KEY}", {"name": "Nisha Homes Project"}),
]

for method, url, *body in endpoints:
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=5)
        else:
            r = requests.post(url, headers=headers, json=body[0] if body else {}, timeout=5)
        print(f"[{method}] {url.split('?')[0]} -> {r.status_code}")
        print(f"   {r.text[:200]}")
    except Exception as e:
        print(f"[{method}] {url} -> {e}")
