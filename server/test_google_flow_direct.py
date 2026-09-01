import json
import uuid
import time
import requests

TOKEN = "ya29.a0AdMD6EgaL9K3bkV8nyQx9KSlzgF0HQibTWenwuma_cXsb61TygC9pN9YZzPSbSan-18NFFMFdvYB9hyKsyFz0fTrn-xGoShconsDys5z2f3v-SdY7UbyTGjfe0BGLxdcCY_cxbcH_i1U_y8oVgESnrszlUE44U2xNgwwkfmQbZu7CoQaWMow97x-SP-RD3zMdkoYrlvbpjMFmFg-8IVqhQE9aekX0s_XlQjvlowhVlTdXSFMf6WNBG7Yc8fj_FvZWukaFdg7-b-EVFEbnXv9ticzdGCvtLdk8TvAevdkdBP_OxyPNU0u_Sw9SaUbpthDTCMe8DysPHs3Fb9hK8YsZkFR2dJS4hanfiJsWZlPbvDwE5DzZ1kkhbgaCgYKAcQSARISFQHGX2Mi7GgpcE8urm-j2TVnVeXD5Q0382"
PROJECT_ID = "0143adf4-5864-4cb4-abb5-fe4254ad0dc7"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
}

body = {
    "clientContext": {
        "projectId": PROJECT_ID,
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
            "aspectRatio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "textInput": {
                "structuredPrompt": {
                    "parts": [
                        {
                            "text": "3D animated stock trading market candlestick chart plunging violently downward into deep red abyss, glowing neon line graph, dramatic camera zoom in, 4k 60fps"
                        }
                    ]
                }
            },
            "videoModelKey": "abra_t2v_5s",
            "seed": 961705173,
            "metadata": {}
        }
    ],
    "useV2ModelConfig": True
}

url = "https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText"
print("Submitting Direct Request to Google Flow API...")
res = requests.post(url, headers=headers, json=body)
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text[:1000]}")
