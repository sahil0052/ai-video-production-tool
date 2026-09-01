import requests, json, time, uuid

TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}

models_to_test = [
    ("abra_t2v_5s", "VIDEO_ASPECT_RATIO_PORTRAIT"),
    ("abra_t2v_5s", "VIDEO_ASPECT_RATIO_LANDSCAPE"),
    ("veo_2_t2v_5s", "VIDEO_ASPECT_RATIO_PORTRAIT"),
    ("veo_3_1_t2v_s_fast_portrait", "VIDEO_ASPECT_RATIO_PORTRAIT"),
]

for model, aspect in models_to_test:
    payload = {
        "clientContext": {
            "projectId": "0143adf4-5864-4cb4-abb5-fe4254ad0dc7",
            "tool": "PINHOLE",
            "userPaygateTier": "PAYGATE_TIER_ONE",
            "sessionId": f";{int(time.time() * 1000)}",
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
                "aspectRatio": aspect,
                "textInput": {
                    "structuredPrompt": {
                        "parts": [
                            {
                                "text": "Cinematic aerial drone shot of modern luxury real estate villas in Gurgaon with swimming pool"
                            }
                        ]
                    }
                },
                "videoModelKey": model,
                "seed": 123456,
                "metadata": {}
            }
        ],
        "useV2ModelConfig": True
    }

    url = "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText"
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[{model} / {aspect}] Status: {res.status_code}")
        print(f"Response: {res.text[:300]}\n")
    except Exception as e:
        print(f"[{model}] Exception: {e}\n")
