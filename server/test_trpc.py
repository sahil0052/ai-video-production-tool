import requests

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

trpc_endpoints = [
    "project.list",
    "project.get",
    "project.create",
    "user.get",
    "user.session",
    "flow.list",
    "tools.list"
]

for ep in trpc_endpoints:
    url = f"https://labs.google/fx/api/trpc/{ep}"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"[GET] {ep} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"[GET] {ep} -> {e}")

    try:
        r = requests.post(url, headers=headers, json={}, timeout=5)
        print(f"[POST] {ep} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"[POST] {ep} -> {e}")
