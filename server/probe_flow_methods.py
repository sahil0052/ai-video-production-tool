import requests

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
PROJECT_ID = "327b335c-f127-41dd-9907-63fb1ebbb421"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": f"https://labs.google/fx/tools/flow/project/{PROJECT_ID}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

methods = [
    "flowMedia:batchGenerateImages",
    "flowMedia:batchGenerateVideos",
    "flowMedia:batchAsyncGenerateVideos",
    "flowMedia:batchAsyncGenerateVideoText",
    "flowMedia:batchGenerateVideoText",
    "flowMedia:batchAsyncGenerateVideoStartImage",
    "flowMedia:batchGenerateVideo",
    "flowMedia:batchCreateVideos",
    "flowMedia:generateVideo",
    "flowMedia:batchCheckAsyncVideoGenerationStatus",
    "flowMedia:batchCheckStatus",
]

for m in methods:
    url = f"https://aisandbox-pa.googleapis.com/v1/projects/{PROJECT_ID}/{m}"
    try:
        r = requests.post(url, headers=headers, json={}, timeout=5)
        print(f"{m} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"{m} -> {e}")
