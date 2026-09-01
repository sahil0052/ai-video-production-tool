import requests, json, time, uuid

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
PROJECT_ID = "327b335c-f127-41dd-9907-63fb1ebbb421"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": f"https://labs.google/fx/tools/flow/project/{PROJECT_ID}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

payload = {
    "clientContext": {
        "projectId": PROJECT_ID,
        "tool": "PINHOLE",
        "sessionId": f";{int(time.time()*1000)}",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "recaptchaContext": {
            "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
            "token": ""
        }
    },
    "mediaGenerationContext": {
        "batchId": str(uuid.uuid4())
    },
    "requests": [
        {
            "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "textInput": {
                "structuredPrompt": {
                    "parts": [{"text": "Cinematic 4K aerial drone shot flying over a modern expressway in Gurgaon NCR at sunset with luxury high-rise towers, golden hour light reflections, smooth camera motion, 60fps"}]
                }
            },
            "videoModelKey": "abra_t2v_5s",
            "seed": 123456,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

url = "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText"
print(f"Submitting Video Generation with Project ID: {PROJECT_ID}...")
res = requests.post(url, headers=headers, json=payload, timeout=20)
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")
