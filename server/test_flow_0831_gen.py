import sys, os
from pathlib import Path
from google_flow_client import GoogleFlowClient

client = GoogleFlowClient()
print("Starting Google Flow Video Generation for Beat 1...")
prompt = "A 3D cinematic animated human brain glowing on a dark high-tech trading desk. One half is cool blue glowing circuitry and the other half is fiery red molten neural energy pulsating with green and red candlestick charts floating in 3D space, camera slowly zooming in, 4k hyperrealistic."

try:
    path = client.generate_and_download(
        prompt=prompt,
        duration=5,
        aspect_ratio="VIDEO_ASPECT_RATIO_PORTRAIT",
        output_filename="flow0831_01_brain_logic_vs_emotion.mp4"
    )
    print("SUCCESS! Generated Beat 1:", path)
except Exception as e:
    print("ERROR during Flow generation:", e)
