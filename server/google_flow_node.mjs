import fs from "fs";
import path from "path";
import crypto from "crypto";

const DEFAULT_PROJECT_ID = "0143adf4-5864-4cb4-abb5-fe4254ad0dc7";
const DEFAULT_API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY";
const DEFAULT_TOKEN = "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382";

export class GoogleFlowNodeClient {
  constructor(token = DEFAULT_TOKEN, projectId = DEFAULT_PROJECT_ID, apiKey = DEFAULT_API_KEY) {
    this.token = token;
    this.projectId = projectId;
    this.apiKey = apiKey;
    this.baseUrl = "https://aisandbox-pa.googleapis.com";
  }

  getHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${this.token}`,
      "Origin": "https://labs.google",
      "Referer": "https://labs.google/fx/tools/flow",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    };
  }

  async generateVideo(prompt, duration = 5, aspect = "VIDEO_ASPECT_RATIO_PORTRAIT") {
    console.log(`[GoogleFlow] Submitting Video Generation: "${prompt}" (${duration}s, ${aspect})...`);
    const payload = {
      clientContext: {
        projectId: this.projectId,
        tool: "PINHOLE",
        userPaygateTier: "PAYGATE_TIER_ONE",
        sessionId: `;${Date.now()}`,
        recaptchaContext: {
          applicationType: "RECAPTCHA_APPLICATION_TYPE_WEB",
          token: "",
        },
      },
      mediaGenerationContext: {
        batchId: crypto.randomUUID(),
      },
      requests: [
        {
          aspectRatio: aspect,
          textInput: {
            structuredPrompt: {
              parts: [{ text: prompt }],
            },
          },
          videoModelKey: `abra_t2v_${duration}s`,
          seed: Math.floor(Math.random() * 2147483647),
          metadata: {},
        },
      ],
      useV2ModelConfig: true,
    };

    const url = `${this.baseUrl}/v1/video:batchAsyncGenerateVideoText?key=${this.apiKey}`;
    const res = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Google Flow Submission Failed (${res.status}): ${errText}`);
    }

    const data = await res.json();
    const media = data.media || [];
    if (!media.length) throw new Error(`No media returned: ${JSON.stringify(data)}`);

    const mediaId = media[0].name;
    console.log(`[GoogleFlow] Job Created! Media ID: ${mediaId}`);
    return { mediaId, prompt, duration, aspect };
  }

  async pollStatus(mediaId, maxWaitSec = 360) {
    const start = Date.now();
    const url = `${this.baseUrl}/v1/video:batchCheckAsyncVideoGenerationStatus?key=${this.apiKey}`;

    while ((Date.now() - start) < maxWaitSec * 1000) {
      const res = await fetch(url, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({ media: [{ name: mediaId, projectId: this.projectId }] }),
      });

      if (res.ok) {
        const data = await res.json();
        const media = data.media || [];
        if (media.length > 0) {
          const status = media[0]?.mediaMetadata?.mediaStatus?.mediaGenerationStatus || "";
          const elapsed = Math.round((Date.now() - start) / 1000);
          console.log(`[GoogleFlow] [${elapsed}s] Status: ${status}`);

          if (status === "MEDIA_GENERATION_STATUS_SUCCESSFUL") {
            return true;
          } else if (status.includes("FAILED") || status.includes("BLOCKED")) {
            throw new Error(`Render Failed: ${status}`);
          }
        }
      }
      await new Promise((r) => setTimeout(r, 6000));
    }
    throw new Error(`Polling timed out after ${maxWaitSec}s`);
  }

  async download(mediaId, outPath) {
    console.log(`[GoogleFlow] Requesting signed URL for ${mediaId}...`);
    const res = await fetch("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect", {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ media_id: mediaId }),
    });

    if (!res.ok) throw new Error(`Failed to get URL: ${res.status}`);
    const data = await res.json();
    const url = data.result?.url || data.url;

    if (!url) throw new Error(`No download URL: ${JSON.stringify(data)}`);
    console.log(`[GoogleFlow] Downloading binary stream...`);

    const videoRes = await fetch(url);
    if (!videoRes.ok) throw new Error(`Download failed: ${videoRes.status}`);

    const buffer = Buffer.from(await videoRes.arrayBuffer());
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, buffer);
    console.log(`[GoogleFlow] Saved ${outPath} (${(buffer.length / 1024 / 1024).toFixed(2)} MB)`);
    return outPath;
  }
}
