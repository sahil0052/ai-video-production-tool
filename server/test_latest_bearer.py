import requests, json, time, uuid

token = "ya29.a0AdMD6Eh9dutqtLWM7bq5IPLAsY8rDZEJ19_e4J_ptdtNrfiKTks_yNBP9dGGVqfyLPr1y99pzJ21s9mYLlRN0GxoT7KygXUNBFpvo31Mql2doQs-tqvPo9xslbBx9dDCpijXUzt0j17Q3UfxSVHUIN46_7eC_03Le4jgfEV3V07l_rVxQBrXUif6r7PhtifhjbUPxUJEoigId6vNUtPLRRgjkQpoJOUBjIi-35LxdLs7rYuir02mVn8kpxXnIDuvivvZDHu3l7sD4BsHgmG7q0aBoMyotMa6xth9aOn3vYWEg7wfn904VvseTl0xwbQruZ1QNPmICH8Hah7ViwVV-rmRzniUcZUD3yb_0PpsFhQjli3Gk3redqMaCgYKAQkSARUSFQHGX2MivMcaFqkWvMPM_QAXJNkhzQ0382"
project_id = "327b335c-f127-41dd-9907-63fb1ebbb421"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

# 1. Token info check
print("1. Checking Token Validity...")
r_user = requests.get(f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}")
print(f"Token status: {r_user.status_code}")
print(f"Token response: {r_user.text}")

# 2. Test Video Gen API call
print("\n2. Testing Video Generation Request...")
payload = {
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
                            "text": "Cinematic aerial view of modern Delhi NCR residential towers, sunset golden hour, 4k 60fps"
                        }
                    ]
                }
            },
            "videoModelKey": "abra_t2v_5s",
            "seed": 1001,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

r_gen = requests.post("https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText", json=payload, headers=headers)
print(f"Video Gen HTTP Status: {r_gen.status_code}")
print(f"Video Gen Full Response:\n{r_gen.text}")

# Save token in current_token.txt
with open(r"c:\websites\google flow mcp\current_token.txt", "w") as f:
    f.write(token + "\n")
print("\nSaved token to c:\\websites\\google flow mcp\\current_token.txt")
