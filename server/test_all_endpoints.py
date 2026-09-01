import requests, json, time, uuid

token = "ya29.a0AdMD6Eh9dutqtLWM7bq5IPLAsY8rDZEJ19_e4J_ptdtNrfiKTks_yNBP9dGGVqfyLPr1y99pzJ21s9mYLlRN0GxoT7KygXUNBFpvo31Mql2doQs-tqvPo9xslbBx9dDCpijXUzt0j17Q3UfxSVHUIN46_7eC_03Le4jgfEV3V07l_rVxQBrXUif6r7PhtifhjbUPxUJEoigId6vNUtPLRRgjkQpoJOUBjIi-35LxdLs7rYuir02mVn8kpxXnIDuvivvZDHu3l7sD4BsHgmG7q0aBoMyotMa6xth9aOn3vYWEg7wfn904VvseTl0xwbQruZ1QNPmICH8Hah7ViwVV-rmRzniUcZUD3yb_0PpsFhQjli3Gk3redqMaCgYKAQkSARUSFQHGX2MivMcaFqkWvMPM_QAXJNkhzQ0382"
project_id = "327b335c-f127-41dd-9907-63fb1ebbb421"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
    "Origin": "https://labs.google",
    "Referer": f"https://labs.google/fx/tools/flow/project/{project_id}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

endpoints_to_test = [
    # 1. Project-scoped image generation (GEM_PIX_2 / Nano Banana)
    f"https://aisandbox-pa.googleapis.com/v1/projects/{project_id}/flowMedia:batchGenerateImages",
    # 2. Project-scoped video generation
    f"https://aisandbox-pa.googleapis.com/v1/projects/{project_id}/video:batchAsyncGenerateVideoText",
    # 3. Global flowMedia image generation
    "https://aisandbox-pa.googleapis.com/v1/flowMedia:batchGenerateImages",
    # 4. Global video generation
    "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText"
]

print("=== TESTING IMAGE GENERATION ENDPOINT ===")
img_body = {
    "requests": [
        {
            "imageAspectRatio": "IMAGE_ASPECT_RATIO_PORTRAIT",
            "imageModelName": "GEM_PIX_2",
            "prompt": "Cinematic aerial view of modern Delhi NCR residential towers, sunset golden hour, 4k",
            "seed": 12345
        }
    ],
    "clientContext": {
        "projectId": project_id,
        "tool": "PINHOLE",
        "sessionId": f";{int(time.time() * 1000)}",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "recaptchaContext": {"applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB", "token": ""}
    }
}

for ep in endpoints_to_test[:3]:
    print(f"\nTesting: {ep}")
    try:
        r = requests.post(ep, json=img_body, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")

print("\n=== TESTING VIDEO GENERATION ENDPOINT ===")
vid_body = {
    "clientContext": {
        "projectId": project_id,
        "tool": "PINHOLE",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "sessionId": f";{int(time.time() * 1000)}",
        "recaptchaContext": {"applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB", "token": ""}
    },
    "mediaGenerationContext": {"batchId": str(uuid.uuid4())},
    "requests": [
        {
            "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "textInput": {"structuredPrompt": {"parts": [{"text": "Aerial view of city, 4k"}]}},
            "videoModelKey": "abra_t2v_5s",
            "seed": 12345,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

for ep in [endpoints_to_test[1], endpoints_to_test[3]]:
    print(f"\nTesting: {ep}")
    try:
        r = requests.post(ep, json=vid_body, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")
