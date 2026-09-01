---
name: davinci-resolve-production-editing
description: >-
  Expert guide, reference, and automation patterns for production-level video editing
  with DaVinci Resolve via Python, dvr CLI/MCP, pydavinci, auto-editor, and the native Resolve Scripting API.
  Use when generating timelines, jump cuts, kinetic captions, B-roll layers, audio ducking, color grading, and automated exports.
---

# DaVinci Resolve Production Video Automation Skill

This skill teaches the agent how to automate professional, broadcast-grade video editing inside **DaVinci Resolve** using Python scripts, the `dvr` library/MCP, `pydavinci`, `auto-editor`, and direct Resolve API calls.

---

## 1. Core Architecture & Tool Ecosystem

```
               ┌────────────────────────────────────────────────────────┐
               │              AI Agent / Python Pipeline                │
               └────────────┬─────────────────────────────┬─────────────┘
                            │                             │
            [High-Level CLI & Automation]         [Direct Python API]
                            │                             │
            ┌───────────────┴──────────────┐   ┌──────────┴───────────────┐
            │ 1. auto-editor (Silence Cut) │   │ 3. dvr (Declarative API) │
            │ 2. FCPXML / EDL Exporter     │   │ 4. pydavinci / Native API│
            └───────────────┬──────────────┘   └──────────┬───────────────┘
                            │                             │
                            ▼                             ▼
               ┌────────────────────────────────────────────────────────┐
               │          DaVinci Resolve Engine (GPU Accelerated)       │
               │  • Edit: Multi-track video, B-Roll, punch zooms        │
               │  • Fusion: 3D DVE, Text+ kinetic captions, animations  │
               │  • Fairlight: Sidechain audio ducking, -14 LUFS master  │
               │  • Deliver: NVENC / GPU render queue                   │
               └────────────────────────────────────────────────────────┘
```

### Key Libraries & Repositories

| Repository | Purpose | When to Use |
| :--- | :--- | :--- |
| **`mhadifilms/dvr`** | Declarative CLI, typed Python library, MCP server | High-level project/timeline inspection, batch queries, render tracking |
| **`pedrolabonia/pydavinci`** | Typed Python wrapper for Resolve API | Detailed object-oriented timeline manipulation, clip properties, markers |
| **`WyattBlue/auto-editor`** | Audio loudness & motion silence removal | First-pass jump-cutting, automated breath/pause reduction with XML export |
| **`deric/DaVinciResolve-API-Docs`** | Full API reference & dictionary keys | Exact parameter names, method signatures, and format codes |

---

## 2. Environment Setup & Connection

### Windows Environment Variables
Ensure these paths are set in Windows before launching Python:
```powershell
$env:RESOLVE_SCRIPT_API = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
$env:RESOLVE_SCRIPT_LIB = "C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
$env:PYTHONPATH = "$env:PYTHONPATH;$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
```

### Standard Connection Boilerplate
```python
import os
import sys

def get_resolve_instance():
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if resolve is None:
            raise ConnectionError("DaVinci Resolve is not running. Please launch the application.")
        return resolve
    except ImportError:
        # Fallback manual import
        api_path = os.getenv("RESOLVE_SCRIPT_API")
        if api_path:
            sys.path.append(os.path.join(api_path, "Modules"))
            import DaVinciResolveScript as dvr_script
            return dvr_script.scriptapp("Resolve")
        raise
```

---

## 3. First-Pass Silence Removal with `auto-editor`

To remove filler pauses and silence while preserving natural speech margins:

```bash
# Analyze audio volume and export directly to DaVinci Resolve XML format
auto-editor "input_raw.mp4" \
  --edit "audio:threshold=0.04" \
  --margin 0.18s,0.18s \
  --export resolve \
  --output "storage/timeline_cuts.xml"
```

Importing the XML into DaVinci Resolve via Python:
```python
project_manager = resolve.GetProjectManager()
project = project_manager.GetCurrentProject()
media_pool = project.GetMediaPool()

# Import the cut timeline XML
imported_timeline = media_pool.ImportTimelineFromFile(
    "storage/timeline_cuts.xml",
    {"timelineName": "Automated_Speech_Cut"}
)
```

---

## 4. Multi-Track Timeline Construction & B-Roll

### Timeline Setup for Vertical Shorts (1080×1920)
```python
def create_portrait_timeline(project, name="TechStory_Vertical"):
    media_pool = project.GetMediaPool()
    
    # Project settings for portrait video
    project.SetSetting("timelineFrameRate", "30")
    project.SetSetting("timelineResolutionWidth", "1080")
    project.SetSetting("timelineResolutionHeight", "1920")
    
    timeline = media_pool.CreateEmptyTimeline(name)
    return timeline
```

### Track Layout Standard
* **Video Track 1 (V1)**: Presenter A-Roll (talking head with punch zooms)
* **Video Track 2 (V2)**: B-Roll Footage / Product Demonstrations / Split Screen
* **Video Track 3 (V3)**: Graphics / Evidence Overlays / Document Macros
* **Video Track 4 (V4)**: Kinetic Captions (`Text+` / Fusion Templates)
* **Audio Track 1 (A1)**: Voice / Dialogue (Normalized & Cleaned)
* **Audio Track 2 (A2)**: Background Music Bed (Sidechained / Ducked)
* **Audio Track 3 (A3)**: Semantic Sound Effects (Whooshes, Clicks, Risers)

### Inserting Clips on Specific Tracks
```python
def insert_clip_to_track(media_pool, timeline, media_item, track_type="video", track_index=1, start_frame=0, duration_frames=90):
    clip_info = {
        "mediaPoolItem": media_item,
        "startFrame": 0,
        "endFrame": duration_frames,
        "recordFrame": start_frame,
        "trackIndex": track_index,
        "mediaType": 1 if track_type == "video" else 2
    }
    media_pool.AppendToTimeline([clip_info])
```

---

## 5. Punch Zooms & Dynamic Camera Motion

### Smooth Bezier Punch Zoom on Presenter
To reset viewer attention every 2–4 seconds without robotic CSS transitions:

```python
def apply_punch_zoom(timeline_item, scale=1.22, x_offset=0.0, y_offset=0.05):
    """
    Applies a smooth punch zoom with GPU sub-pixel filtering and reframing.
    """
    # Set Pan / Tilt / Zoom properties
    timeline_item.SetProperty("ZoomX", scale)
    timeline_item.SetProperty("ZoomY", scale)
    timeline_item.SetProperty("Pan", x_offset * 1080)
    timeline_item.SetProperty("Tilt", y_offset * 1920)
    
    # Enable Dynamic Zoom for continuous subtle push
    timeline_item.SetDynamicZoom(True)
    # EaseInOut creates natural cinematic acceleration
    timeline_item.SetDynamicZoomEase(3) # 0: Linear, 1: EaseIn, 2: EaseOut, 3: EaseInOut
```

---

## 6. Kinetic Typography with Fusion Text+

### Creating Monospace Boxed Word Highlights
```python
def create_text_plus_title(timeline, text, start_frame, end_frame, font="Share Tech Mono", size=0.045):
    # Insert standard Fusion Text+ template
    media_pool = project.GetMediaPool()
    
    # Add Text+ title to Track 4
    title_item = timeline.InsertFusionTitleIntoTimeline("Text+", trackIndex=4, startFrame=start_frame, endFrame=end_frame)
    
    # Access the underlying Fusion Composition
    fusion_comp = title_item.GetFusionCompByIndex(1)
    if fusion_comp:
        template_node = fusion_comp.FindToolByID("Template")
        if template_node:
            template_node.SetInput("StyledText", text)
            template_node.SetInput("Font", font)
            template_node.SetInput("Size", size)
            
            # Box Pill Styling
            template_node.SetInput("BackgroundEnable", 1)
            template_node.SetInput("BackgroundColor", [0.05, 0.07, 0.08, 0.95]) # Near-black pill
            template_node.SetInput("BackgroundRound", 0.08)
            template_node.SetInput("BackgroundPadding", [0.03, 0.02])
```

---

## 7. Fairlight Audio Mixing & Auto-Ducking

### Sidechain Voice-Activated Music Ducking
1. **Dialogue Track (A1)**: Send sidechain trigger to compressor bus.
2. **Music Track (A2)**: Compressor listens to A1 sidechain input.
   - **Threshold**: `-24 dB`
   - **Ratio**: `4:1`
   - **Attack**: `15 ms` (smooth, non-clicking fade)
   - **Release**: `350 ms` (natural swell during pauses)
3. **Master Output (Bus 1)**: Integrated Loudness normalization targeting `-14.0 LUFS` with `-1.0 dBTP` True Peak.

---

## 8. Automated Render & Export Pipeline

```python
def export_production_master(project, output_path, preset_name="H.264 Master 1080x1920"):
    output_dir = os.path.dirname(output_path)
    output_file = os.path.basename(output_path)
    file_name_no_ext, ext = os.path.splitext(output_file)
    
    project.SetRenderSettings({
        "TargetDir": output_dir,
        "CustomName": file_name_no_ext,
        "ExportVideo": True,
        "ExportAudio": True,
        "FormatWidth": 1080,
        "FormatHeight": 1920,
        "FrameRate": 30,
        "VideoQuality": 0, # Auto/High
        "AudioCodec": "aac",
        "AudioBitDepth": 16,
        "AudioSampleRate": 48000
    })
    
    # Clear existing queue and add new render job
    project.DeleteAllRenderJobs()
    job_id = project.AddRenderJob()
    
    # Start rendering and monitor progress
    project.StartRendering(job_id)
    
    while project.IsRenderingInProgress():
        status = project.GetRenderJobStatus(job_id)
        pct = status.get("JobStatus", 0)
        time.sleep(0.5)
        
    print(f"Export completed successfully: {output_path}")
```

---

## 9. Common Error Handling & Workarounds

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `scriptapp("Resolve")` returns `None` | Resolve is not running or external scripting is disabled | Go to **Preferences > System > General > External scripting** and select **Local**. Ensure DaVinci Resolve is open. |
| Clips not appearing on timeline | Frame rate mismatch | Set project timeline framerate to match media before creating the timeline. |
| Text+ styling fails to apply | Fusion graph unready | Call `fusion_comp.GetToolList()` or add a 50ms sleep to allow the node graph to initialize. |
| Silent render failure | Invalid output directory path | Use `os.path.abspath()` and verify write permissions. |
