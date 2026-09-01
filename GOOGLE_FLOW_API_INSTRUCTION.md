# 🚀 Google Flow (Veo / Labs FX) Direct API Generation Guide

This instruction manual provides the exact endpoints, authentication headers, JSON payloads, and automated execution scripts used to generate AI videos directly through Google Flow (`labs.google/fx/tools/flow`). Any AI agent or developer can use this specification to generate videos programmatically.

---

## 📌 1. System Architecture & Authentication

Google Flow uses Google's internal **AI Sandbox / Pinhole API (`aisandbox-pa.googleapis.com`)** powered by the **Abra (Veo 2)** video model.

### 🔑 Authentication Requirements
All requests require a Google Account Bearer Token:
- **Header**: `Authorization: Bearer <GOOGLE_OAUTH_TOKEN>`
- **Origin**: `https://labs.google`
- **Referer**: `https://labs.google/fx/tools/flow`

#### 🛠️ How to Extract Your Bearer Token:
1. Open Google Chrome and log in to [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow).
2. Press `F12` to open **Developer Tools** $\rightarrow$ go to the **Network** tab.
3. Type any prompt in Flow and click **Generate**.
4. Filter by `batchAsyncGenerateVideoText`.
5. Under **Request Headers**, copy the value of `Authorization` (starts with `Bearer ya29...`).

> [!NOTE]
> Google OAuth tokens typically refresh every 60 minutes. If running automated workflows, the local WebSocket Chrome extension bridge (`src/flow-agent-server.js`) captures and refreshes this token automatically.

---

## 📡 2. API Endpoints & Request Specifications

---

### 🎬 Step 1: Submit Video Generation
- **Endpoint**: `POST https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText`
- **Headers**:
  ```http
  Content-Type: application/json
  Authorization: Bearer ya29.a0AdMD6Ej7rACrL3nlyl-Cxq52qjJKX7Gs2xpCpktHpKypH9rMdxRRy3HjqrtBY1u3EHUoYtm8pJp1CqrtfP__TALG5JZ9zOHbvEisVCx9AkyW9T8VeTpegbMnBgCLzPpUoqQFDwFxxvn-HZwZ2kp9Aa9dHq9L_MYVgLK6gJ1BoehtvNDa_YEPrMf-iEVGbu4qnSQokIafCkqSmBp5-TrikceNCZdGfgf3--mGcWDrZFhkS32EMAEUXP8W48IvF6RZfoMmfK2D56Rl-_2kyCrxXydo1s3GqpC_wOEtzSFVhhs0aLUD-6vpzfV0A3VrJ9mtXY5nC1ANXl5z44Z6Rqmi4ltYWDsPPqLM9bDC5lhF--Fj-Ojhhh78XQaCgYKAe8SARISFQHGX2Miv7SyjEwhWGFsdgTFZaYNwA0381
  Origin: https://labs.google
  Referer: https://labs.google/fx/tools/flow
  ```

#### 📦 JSON Request Payload:
```json
{
  "clientContext": {
    "projectId": "0143adf4-5864-4cb4-abb5-fe4254ad0dc7",
    "tool": "PINHOLE",
    "userPaygateTier": "PAYGATE_TIER_ONE",
    "sessionId": ";1724500000000",
    "recaptchaContext": {
      "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
      "token": "<RECAPTCHA_ENTERPRISE_TOKEN>"
    }
  },
  "mediaGenerationContext": {
    "batchId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "requests": [
    {
      "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
      "textInput": {
        "structuredPrompt": {
          "parts": [
            {
              "text": "Cinematic 9:16 vertical shot, young Indian woman with round glasses presenting in a modern studio, high quality, 4k 60fps"
            }
          ]
        }
      },
      "videoModelKey": "abra_t2v_10s",
      "seed": 12345678,
      "metadata": {}
    }
  ],
  "useV2ModelConfig": true
}
```

#### ⚙️ Key Parameter Options:
| Parameter | Values | Description |
| :--- | :--- | :--- |
| `aspectRatio` | `VIDEO_ASPECT_RATIO_PORTRAIT`<br>`VIDEO_ASPECT_RATIO_LANDSCAPE` | `9:16` Vertical (Reels/TikTok/Shorts)<br>`16:9` Horizontal (YouTube) |
| `videoModelKey` | `abra_t2v_5s`<br>`abra_t2v_10s` | 5-second video duration<br>10-second video duration |
| `tool` | `PINHOLE` | Google Flow engine identifier |
| `seed` | Random Integer (`1` to `2147483647`) | Generation variation seed |

#### 📥 Response Format:
```json
{
  "media": [
    {
      "name": "projects/0143adf4-5864-4cb4-abb5-fe4254ad0dc7/locations/us-central1/publishers/google/models/abra_t2v_10s/media/MEDIA_UUID_12345",
      "mediaMetadata": {
        "mediaStatus": {
          "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_IN_PROGRESS"
        }
      }
    }
  ]
}
```
> **Extract**: Store `media[0].name` as your `MEDIA_ID` for polling.

---

### ⏳ Step 2: Poll Generation Status
- **Endpoint**: `POST https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus`
- **Headers**:
  ```http
  Content-Type: application/json
  Authorization: Bearer <YOUR_BEARER_TOKEN>
  ```

#### 📦 JSON Request Payload:
```json
{
  "media": [
    {
      "name": "<MEDIA_ID_FROM_STEP_1>",
      "projectId": "0143adf4-5864-4cb4-abb5-fe4254ad0dc7"
    }
  ]
}
```

#### 📥 Status Lifecycle:
- `MEDIA_GENERATION_STATUS_IN_PROGRESS` $\rightarrow$ Wait 5–6 seconds and poll again.
- `MEDIA_GENERATION_STATUS_SUCCESSFUL` $\rightarrow$ Generation complete! Proceed to Step 3.
- `MEDIA_GENERATION_STATUS_FAILED` $\rightarrow$ Generation failed or blocked by safety filter.

---

### ⬇️ Step 3: Get Direct Download URL
- **Endpoint**: `POST https://labs.google/fx/api/trpc/media.getMediaUrlRedirect`
- **Headers**:
  ```http
  Content-Type: application/json
  Authorization: Bearer <YOUR_BEARER_TOKEN>
  ```

#### 📦 JSON Request Payload:
```json
{
  "media_id": "<MEDIA_ID_FROM_STEP_1>"
}
```

#### 📥 Response Format:
```json
{
  "result": {
    "url": "https://storage.googleapis.com/video-fx-public-storage/.../video.mp4?GoogleAccessId=...&Signature=..."
  }
}
```
> **Download**: Perform a standard `GET` request on `result.url` and save the binary `.mp4` file.

---

## 💻 3. Complete Standalone Node.js Automation Script

Save this script as `generate-flow-video.mjs` and execute directly with `node generate-flow-video.mjs`:

```javascript
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

// ─── CONFIGURATION ───
const BEARER_TOKEN = 'YOUR_GOOGLE_BEARER_TOKEN_HERE'; // Replace with your ya29... token
const PROJECT_ID = '0143adf4-5864-4cb4-abb5-fe4254ad0dc7';

const PROMPT = 'Cinematic 9:16 vertical shot, young Indian woman with round glasses presenting in a modern studio, 4k 60fps';
const DURATION_SECONDS = 10; // 5 or 10
const ASPECT_RATIO = 'VIDEO_ASPECT_RATIO_PORTRAIT'; // or 'VIDEO_ASPECT_RATIO_LANDSCAPE'
const OUTPUT_FILE = './output_video.mp4';

async function generateFlowVideo() {
  console.log('🎬 [1/3] Submitting prompt to Google Flow API...');

  const requestBody = {
    clientContext: {
      projectId: PROJECT_ID,
      tool: 'PINHOLE',
      userPaygateTier: 'PAYGATE_TIER_ONE',
      sessionId: `;${Date.now()}`,
      recaptchaContext: {
        applicationType: 'RECAPTCHA_APPLICATION_TYPE_WEB',
        token: ''
      }
    },
    mediaGenerationContext: {
      batchId: crypto.randomUUID()
    },
    requests: [
      {
        aspectRatio: ASPECT_RATIO,
        textInput: {
          structuredPrompt: {
            parts: [{ text: PROMPT }]
          }
        },
        videoModelKey: `abra_t2v_${DURATION_SECONDS}s`,
        seed: Math.floor(Math.random() * 2147483647),
        metadata: {}
      }
    ],
    useV2ModelConfig: true
  };

  const genRes = await fetch('https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${BEARER_TOKEN}`,
      'Origin': 'https://labs.google',
      'Referer': 'https://labs.google/fx/tools/flow'
    },
    body: JSON.stringify(requestBody)
  });

  if (!genRes.ok) {
    throw new Error(`Generation submission failed (${genRes.status}): ${await genRes.text()}`);
  }

  const genData = await genRes.json();
  const mediaId = genData.media?.[0]?.name;
  if (!mediaId) throw new Error(`No media ID returned: ${JSON.stringify(genData)}`);

  console.log(`✅ Submission successful! Media ID: ${mediaId}`);
  console.log('⏳ [2/3] Polling generation status...');

  // ─── POLLING LOOP ───
  let isComplete = false;
  const startTime = Date.now();

  while (!isComplete) {
    await new Promise(r => setTimeout(r, 6000));
    const elapsed = Math.round((Date.now() - startTime) / 1000);

    const pollRes = await fetch('https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${BEARER_TOKEN}`
      },
      body: JSON.stringify({
        media: [{ name: mediaId, projectId: PROJECT_ID }]
      })
    });

    const pollData = await pollRes.json();
    const status = pollData.media?.[0]?.mediaMetadata?.mediaStatus?.mediaGenerationStatus;
    console.log(`   [${elapsed}s] Status: ${status}`);

    if (status === 'MEDIA_GENERATION_STATUS_SUCCESSFUL') {
      isComplete = true;
    } else if (status && (status.includes('FAILED') || status.includes('BLOCKED'))) {
      throw new Error(`Video generation failed with status: ${status}`);
    }
  }

  console.log('📥 [3/3] Requesting signed download URL...');
  const urlRes = await fetch('https://labs.google/fx/api/trpc/media.getMediaUrlRedirect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${BEARER_TOKEN}`
    },
    body: JSON.stringify({ media_id: mediaId })
  });

  const urlData = await urlRes.json();
  const downloadUrl = urlData.result?.url;
  if (!downloadUrl) throw new Error(`Failed to obtain download URL: ${JSON.stringify(urlData)}`);

  console.log('⬇️ Downloading video file...');
  const dlResponse = await fetch(downloadUrl);
  const buffer = Buffer.from(await dlResponse.arrayBuffer());

  const outDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(OUTPUT_FILE, buffer);

  console.log(`🎉 Success! Video saved to ${OUTPUT_FILE} (${(buffer.length / (1024 * 1024)).toFixed(2)} MB)`);
}

generateFlowVideo().catch(console.error);
```

---

## 🐍 4. Standalone Python Automation Script

```python
import time
import uuid
import random
import requests

BEARER_TOKEN = "YOUR_GOOGLE_BEARER_TOKEN_HERE"
PROJECT_ID = "0143adf4-5864-4cb4-abb5-fe4254ad0dc7"
PROMPT = "Cinematic 9:16 vertical shot, young Indian woman with glasses presenting in modern studio, 4k 60fps"
OUTPUT_FILE = "flow_output.mp4"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Origin": "https://labs.google",
    "Referer": "https://labs.google/fx/tools/flow",
}

# 1. Submit Request
body = {
    "clientContext": {
        "projectId": PROJECT_ID,
        "tool": "PINHOLE",
        "userPaygateTier": "PAYGATE_TIER_ONE",
        "sessionId": f";{int(time.time() * 1000)}",
        "recaptchaContext": {"applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB", "token": ""},
    },
    "mediaGenerationContext": {"batchId": str(uuid.uuid4())},
    "requests": [{
        "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
        "textInput": {"structuredPrompt": {"parts": [{"text": PROMPT}]}},
        "videoModelKey": "abra_t2v_10s",
        "seed": random.randint(1, 2147483647),
        "metadata": {},
    }],
    "useV2ModelConfig": True,
}

res = requests.post("https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText", json=body, headers=headers)
res.raise_for_status()
media_id = res.json()["media"][0]["name"]
print(f"🎬 Submitted! Media ID: {media_id}")

# 2. Poll Status
while True:
    time.sleep(6)
    poll_res = requests.post(
        "https://aisandbox-pa.googleapis.com/v1/video:batchCheckAsyncVideoGenerationStatus",
        json={"media": [{"name": media_id, "projectId": PROJECT_ID}]},
        headers=headers,
    )
    status = poll_res.json()["media"][0]["mediaMetadata"]["mediaStatus"]["mediaGenerationStatus"]
    print(f"Status: {status}")
    if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
        break
    elif "FAILED" in status or "BLOCKED" in status:
        raise RuntimeError(f"Generation failed: {status}")

# 3. Download Video
url_res = requests.post("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect", json={"media_id": media_id}, headers=headers)
download_url = url_res.json()["result"]["url"]

vid_data = requests.get(download_url)
with open(OUTPUT_FILE, "wb") as f:
    f.write(vid_data.content)

print(f"🎉 Saved to {OUTPUT_FILE} ({len(vid_data.content) / (1024*1024):.2f} MB)")
```

---

## 🎯 5. Best-Practice Prompts for High Quality

1. **Camera Framing**: Start with `Cinematic 9:16 vertical shot` (or `Cinematic 16:9 widescreen shot`).
2. **Subject Consistency**: Specify character details explicitly (`young Indian woman with dark round glasses, wavy shoulder hair, minimal grey crewneck`).
3. **Lighting & Motion**: Include `soft studio lighting, 4k 60fps photorealistic, smooth camera dolly motion`.
4. **Avoid Prohibited Terms**: Avoid real living celebrity names if strict safety filter triggers (`MEDIA_GENERATION_STATUS_BLOCKED`). Use descriptive archetypes instead.
