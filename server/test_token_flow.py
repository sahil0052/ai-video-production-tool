import requests, json, uuid, time

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json"
}

project_id = str(uuid.uuid4())
batch_id = str(uuid.uuid4())
session_id = f";{int(time.time() * 1000)}"

payload = {
    "clientContext": {
        "projectId": project_id,
        "tool": "PINHOLE",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "sessionId": session_id
    },
    "mediaGenerationContext": {
        "batchId": batch_id
    },
    "requests": [
        {
            "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "textInput": {
                "structuredPrompt": {
                    "parts": [
                        {
                            "text": "Cinematic aerial drone shot of modern luxury villas in Gurgaon NCR at golden hour"
                        }
                    ]
                }
            },
            "videoModelKey": "abra_t2v_5s",
            "seed": 424242,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

url = f"https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText?key={API_KEY}"
print("Testing Flow generation endpoint...")
try:
    res = requests.post(url, headers=headers, json=payload, timeout=20)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Exception: {e}")
