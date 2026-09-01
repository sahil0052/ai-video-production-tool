import requests, json, time, uuid

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

# Test 1: Flow Media Batch Generate Images
img_payload = {
    "requests": [
        {
            "imageAspectRatio": "IMAGE_ASPECT_RATIO_PORTRAIT",
            "imageModelName": "GEM_PIX_2",
            "prompt": "Luxury modern villa in Gurgaon with swimming pool, 8k",
            "seed": 123456
        }
    ],
    "clientContext": {
        "projectId": "0143adf4-5864-4cb4-abb5-fe4254ad0dc7",
        "tool": "PINHOLE",
        "sessionId": f";{int(time.time()*1000)}",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "recaptchaContext": {
            "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
            "token": ""
        }
    }
}

url1 = "https://aisandbox-pa.googleapis.com/v1/projects/0143adf4-5864-4cb4-abb5-fe4254ad0dc7/flowMedia:batchGenerateImages"
print("--- TEST 1: Direct Image Gen ---")
try:
    r1 = requests.post(url1, headers=headers, json=img_payload, timeout=10)
    print(f"Status: {r1.status_code}")
    print(f"Response: {r1.text[:400]}")
except Exception as e:
    print(f"Exception: {e}")

# Test 2: Direct Text to Video
vid_payload = {
    "clientContext": {
        "projectId": "0143adf4-5864-4cb4-abb5-fe4254ad0dc7",
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
                    "parts": [{"text": "Cinematic aerial drone shot of luxury villas in Gurgaon at golden hour, 4k"}]
                }
            },
            "videoModelKey": "abra_t2v_5s",
            "seed": 123456,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

url2 = "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText"
print("\n--- TEST 2: Direct Text-to-Video ---")
try:
    r2 = requests.post(url2, headers=headers, json=vid_payload, timeout=10)
    print(f"Status: {r2.status_code}")
    print(f"Response: {r2.text[:400]}")
except Exception as e:
    print(f"Exception: {e}")
