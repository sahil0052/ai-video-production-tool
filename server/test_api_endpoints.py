import requests

TOKEN = "ya29.a0AdMD6EgaL9K3bkV8nyQx9KSlzgF0HQibTWenwuma_cXsb61TygC9pN9YZzPSbSan-18NFFMFdvYB9hyKsyFz0fTrn-xGoShconsDys5z2f3v-SdY7UbyTGjfe0BGLxdcCY_cxbcH_i1U_y8oVgESnrszlUE44U2xNgwwkfmQbZu7CoQaWMow97x-SP-RD3zMdkoYrlvbpjMFmFg-8IVqhQE9aekX0s_XlQjvlowhVlTdXSFMf6WNBG7Yc8fj_FvZWukaFdg7-b-EVFEbnXv9ticzdGCvtLdk8TvAevdkdBP_OxyPNU0u_Sw9SaUbpthDTCMe8DysPHs3Fb9hK8YsZkFR2dJS4hanfiJsWZlPbvDwE5DzZ1kkhbgaCgYKAcQSARISFQHGX2Mi7GgpcE8urm-j2TVnVeXD5Q0382"
API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
    "Content-Type": "application/json"
}

endpoints = [
    ("GET", f"https://aisandbox-pa.googleapis.com/v1/credits?key={API_KEY}", None),
    ("POST", f"https://aisandbox-pa.googleapis.com/v1/flow:batchLogFrontendEvents?key={API_KEY}", {}),
    ("POST", f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect", {"media_id": "test"}),
]

for method, url, body in endpoints:
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=5)
        else:
            r = requests.post(url, headers=headers, json=body, timeout=5)
        print(f"[{method}] {url.split('?')[0]} -> {r.status_code}")
        print(f"   Response: {r.text[:300]}")
    except Exception as e:
        print(f"[{method}] {url} -> Exception: {e}")
