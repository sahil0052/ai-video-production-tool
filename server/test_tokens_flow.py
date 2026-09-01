import requests, json, time, uuid

token1 = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
with open(r"c:\websites\google flow mcp\current_token.txt", "r") as f:
    token2 = f.read().strip()

tokens = [("Token from User Prompt", token1), ("Token from current_token.txt", token2)]

for label, tok in tokens:
    print(f"\n================== TESTING {label} ==================")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tok}",
        "Origin": "https://labs.google",
        "Referer": "https://labs.google/fx/tools/flow",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    # 1. Test user info / token validity endpoint
    try:
        r_user = requests.get(
            f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={tok}",
            timeout=10
        )
        print(f"Tokeninfo status: {r_user.status_code}")
        print(f"Tokeninfo response: {r_user.text[:300]}")
    except Exception as e:
        print(f"Tokeninfo error: {e}")

    # 2. Test aisandbox-pa direct generation
    project_id = "327b335c-f127-41dd-9907-63fb1ebbb421"
    body = {
        "clientContext": {
            "projectId": project_id,
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
                "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
                "textInput": {
                    "structuredPrompt": {
                        "parts": [
                            {
                                "text": "Cinematic aerial view of modern city highway at sunset, 4k 60fps"
                            }
                        ]
                    }
                },
                "videoModelKey": "abra_t2v_5s",
                "seed": 42,
                "metadata": {}
            }
        ],
        "useV2ModelConfig": True
    }

    try:
        r_gen = requests.post(
            "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText",
            json=body,
            headers=headers,
            timeout=15
        )
        print(f"Video Gen status: {r_gen.status_code}")
        print(f"Video Gen response: {r_gen.text[:500]}")
    except Exception as e:
        print(f"Video Gen error: {e}")
