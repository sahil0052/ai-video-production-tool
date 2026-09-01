from __future__ import annotations

import os
import sys
import time
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

RESOLVE_EXE = Path(r"D:\Resolve.exe")
FUSIONSCRIPT_DLL = Path(r"D:\fusionscript.dll")
SCRIPTING_API_DIR = Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
DEFAULT_EXPORTS_DIR = Path(r"D:\DaVinciResolve\Exports")


def configure_resolve_environment() -> None:
    """Configures environment variables and DLL search paths for Resolve."""
    if hasattr(os, "add_dll_directory") and RESOLVE_EXE.parent.is_dir():
        try:
            os.add_dll_directory(str(RESOLVE_EXE.parent))
        except Exception:
            pass

    os.environ["RESOLVE_SCRIPT_LIB"] = str(FUSIONSCRIPT_DLL)
    os.environ["RESOLVE_SCRIPT_API"] = str(SCRIPTING_API_DIR)
    
    modules_path = SCRIPTING_API_DIR / "Modules"
    if str(modules_path) not in sys.path:
        sys.path.append(str(modules_path))


def is_resolve_running() -> bool:
    """Checks if DaVinci Resolve process is currently active."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Resolve.exe"],
            text=True,
            errors="replace",
        )
        return "Resolve.exe" in output
    except Exception:
        return False


def launch_resolve(timeout_seconds: int = 40) -> Any:
    """
    Launches DaVinci Resolve if not running and connects to the Scripting API.
    """
    configure_resolve_environment()
    
    if not is_resolve_running():
        if not RESOLVE_EXE.is_file():
            raise FileNotFoundError(f"DaVinci Resolve not found at {RESOLVE_EXE}")
        
        print(f"[DaVinci] Launching Resolve on-demand from {RESOLVE_EXE}...")
        # Launch minimized/background
        subprocess.Popen([str(RESOLVE_EXE)], shell=False)
        time.sleep(3)

    import DaVinciResolveScript as dvr_script
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            resolve = dvr_script.scriptapp("Resolve")
            if resolve is not None:
                # Ensure ProjectManager is ready
                pm = resolve.GetProjectManager()
                if pm is not None:
                    print(f"[DaVinci] Successfully connected to Resolve {resolve.GetVersionString()}!")
                    return resolve
        except Exception:
            pass
        time.sleep(1.0)

    raise TimeoutError(f"Failed to connect to DaVinci Resolve within {timeout_seconds} seconds.")


def quit_resolve(resolve: Any | None = None) -> None:
    """Gracefully terminates DaVinci Resolve to reclaim 100% RAM."""
    print("[DaVinci] Reclaiming memory: Closing DaVinci Resolve...")
    if resolve:
        try:
            resolve.Quit()
            time.sleep(1.5)
        except Exception:
            pass
            
    # Terminate process if still lingering
    if is_resolve_running():
        subprocess.run(["taskkill", "/F", "/IM", "Resolve.exe"], capture_output=True)
    print("[DaVinci] Memory reclaimed. Resolve closed.")


@contextmanager
def on_demand_resolve(auto_close: bool = True) -> Generator[Any, None, None]:
    """
    Context manager that launches DaVinci Resolve on demand, yields the API handle,
    and cleanly terminates Resolve upon exit to maintain a 0 MB idle RAM footprint.
    """
    resolve = launch_resolve()
    try:
        yield resolve
    finally:
        if auto_close:
            quit_resolve(resolve)


def render_project_to_file(
    project: Any,
    output_path: Path,
    preset_name: str = "H.264 Master 1080x1920",
) -> None:
    """Configures render settings and renders timeline to the target output path."""
    output_dir = output_path.parent.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    custom_name = output_path.stem

    project.SetRenderSettings({
        "TargetDir": str(output_dir),
        "CustomName": custom_name,
        "ExportVideo": True,
        "ExportAudio": True,
        "FormatWidth": 1080,
        "FormatHeight": 1920,
        "FrameRate": 30,
        "VideoQuality": 0,
        "AudioCodec": "aac",
        "AudioBitDepth": 16,
        "AudioSampleRate": 48000,
    })

    project.DeleteAllRenderJobs()
    job_id = project.AddRenderJob()
    if not job_id:
        raise RuntimeError("Failed to add render job in DaVinci Resolve.")

    print(f"[DaVinci] Starting render job {job_id} -> {output_path}...")
    project.StartRendering(job_id)

    while project.IsRenderingInProgress():
        status = project.GetRenderJobStatus(job_id)
        pct = status.get("JobStatus", 0)
        print(f"[DaVinci] Rendering progress: {pct}%")
        time.sleep(1.0)

    print(f"[DaVinci] Render completed successfully: {output_path}")
