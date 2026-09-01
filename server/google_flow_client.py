"""
Google Flow Direct API Client for Autonomous Video Generation
Supports text-to-video, image-to-video, and multi-scene automation.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoogleFlowClient")

WORKSPACE = Path(__file__).resolve().parent.parent
FLOW_OUTPUT_DIR = WORKSPACE / "storage" / "assets" / "flow_videos"
REMOTION_FLOW_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"

FLOW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REMOTION_FLOW_DIR.mkdir(parents=True, exist_ok=True)

# Default Project Credentials
DEFAULT_PROJECT_ID = "0143adf4-5864-4cb4-abb5-fe4254ad0dc7"
DEFAULT_API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"

class GoogleFlowClient:
    def __init__(
        self,
        bearer_token: Optional[str] = None,
        project_id: str = DEFAULT_PROJECT_ID,
        api_key: str = DEFAULT_API_KEY
    ):
        self.project_id = project_id
        self.api_key = api_key
        self.bearer_token = bearer_token or os.environ.get(
            "GOOGLE_FLOW_BEARER_TOKEN",
            "ya29.a0AdMD6EgHSkMUUGCqUCB8_AnrKfiGvyIPQcpd17EWGUdmk1TZAknqXtNp9rs2lFUSKkMhZe02RT07GliOe1JA-fJ_dSHMR8ZLonWVSr8enKD6PXTRRHe0R_1vFn_QSWQ5R8yaDGzk9X0hmabEG1CPXppwl7burUeQwnJ2ocDVFML69dc9wgwb3zk-4cmNIfOppr94JDwXqCPTZ1EqAfFQNqUWxI3JmXIGbwZG6LX0UYGWaLDL59aSMhqOJh4gVvWZlFuuDM10XrcWG7wCWT00ePNEWEy7EnpXBt2_kGFTb3zpoo4M9gziYQEy0G0vFjJMuM03k_xZDMHv95OR1Cgyg0zV34td4xLkgK_5irYfBRIA2RzzuRUJLEYaCgYKAQkSARUSFQHGX2MiK2aBL8y4EXSCrBJKwdGKPQ0382"
        )
        self.base_url = "https://aisandbox-pa.googleapis.com"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "Origin": "https://labs.google",
            "Referer": "https://labs.google/fx/tools/flow",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }

    def set_bearer_token(self, token: str) -> None:
        """Update live bearer session token."""
        self.bearer_token = token.strip()
        logger.info(f"Updated Google Flow Bearer Token (Length: {len(self.bearer_token)})")

    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
        model_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a direct text-to-video generation request.
        duration: 5 or 10 seconds (default 5s for fast shorts pacing)
        aspect_ratio: VIDEO_ASPECT_RATIO_PORTRAIT (9:16) or VIDEO_ASPECT_RATIO_LANDSCAPE (16:9)
        """
        model = model_key or f"abra_t2v_{duration}s"
        logger.info(f"Submitting Video Generation Request: '{prompt[:60]}...' ({duration}s, {aspect_ratio})")

        payload = {
            "clientContext": {
                "projectId": self.project_id,
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
                    "aspectRatio": aspect_ratio,
                    "textInput": {
                        "structuredPrompt": {
                            "parts": [{"text": prompt}]
                        }
                    },
                    "videoModelKey": model,
                    "seed": int(time.time()) % 2147483647,
                    "metadata": {}
                }
            ],
            "useV2ModelConfig": True
        }

        url = f"{self.base_url}/v1/video:batchAsyncGenerateVideoText?key={self.api_key}"
        res = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
        
        if res.status_code != 200:
            logger.error(f"Generation request failed ({res.status_code}): {res.text}")
            raise RuntimeError(f"Google Flow Generation Failed ({res.status_code}): {res.text}")

        data = res.json()
        media_list = data.get("media", [])
        if not media_list:
            raise RuntimeError(f"No media items returned from Google Flow: {data}")

        media_id = media_list[0].get("name")
        logger.info(f"Video Generation Job Created! Media ID: {media_id}")
        return {
            "media_id": media_id,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "raw_response": data
        }

    def poll_video_status(self, media_id: str, max_wait_seconds: int = 360, poll_interval: int = 6) -> str:
        """
        Poll status until generation is SUCCESSFUL or fails.
        """
        logger.info(f"Polling Google Flow for Media ID: {media_id}...")
        url = f"{self.base_url}/v1/video:batchCheckAsyncVideoGenerationStatus?key={self.api_key}"
        start_time = time.time()

        payload = {
            "media": [
                {
                    "name": media_id,
                    "projectId": self.project_id
                }
            ]
        }

        while time.time() - start_time < max_wait_seconds:
            res = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                media = data.get("media", [])
                if media:
                    status_info = media[0].get("mediaMetadata", {}).get("mediaStatus", {})
                    status = status_info.get("mediaGenerationStatus", "")
                    elapsed = int(time.time() - start_time)
                    logger.info(f"[{elapsed}s] Render Status: {status}")

                    if status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                        logger.info(f"Video Render Complete in {elapsed} seconds!")
                        return "SUCCESSFUL"
                    elif "FAILED" in status or "BLOCKED" in status:
                        raise RuntimeError(f"Generation Failed: {status}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Polling timed out after {max_wait_seconds} seconds.")

    def download_video(self, media_id: str, output_filename: Optional[str] = None) -> Path:
        """
        Obtain signed download URL and save binary MP4.
        """
        filename = output_filename or f"flow_{media_id.replace('/', '_')}.mp4"
        out_path = FLOW_OUTPUT_DIR / filename
        remotion_copy = REMOTION_FLOW_DIR / filename

        logger.info(f"Requesting Signed Download URL for {media_id}...")
        url_endpoint = "https://labs.google/fx/api/trpc/media.getMediaUrlRedirect"
        res = requests.post(url_endpoint, headers=self._get_headers(), json={"media_id": media_id}, timeout=20)

        if res.status_code != 200:
            raise RuntimeError(f"Failed to get media download URL ({res.status_code}): {res.text}")

        res_data = res.json()
        download_url = res_data.get("result", {}).get("url") or res_data.get("url")
        if not download_url:
            raise RuntimeError(f"Could not extract signed URL from response: {res_data}")

        logger.info(f"Downloading video stream to {out_path}...")
        video_res = requests.get(download_url, stream=True, timeout=60)
        video_res.raise_for_status()

        with open(out_path, "wb") as f:
            for chunk in video_res.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # Mirror copy to Remotion public directory for instant composition preview
        import shutil
        shutil.copy2(out_path, remotion_copy)

        size_mb = out_path.stat().st_size / (1024 * 1024)
        logger.info(f"Video Downloaded Successfully! Size: {size_mb:.2f} MB")
        logger.info(f"Staged for Remotion: {remotion_copy}")
        return out_path

    def generate_and_download(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
        output_filename: Optional[str] = None
    ) -> Path:
        """Complete one-shot generation, polling, and download."""
        job = self.generate_video(prompt, duration=duration, aspect_ratio=aspect_ratio)
        self.poll_video_status(job["media_id"])
        return self.download_video(job["media_id"], output_filename=output_filename)

if __name__ == "__main__":
    client = GoogleFlowClient()
    print("Google Flow Client initialized with active credentials.")
