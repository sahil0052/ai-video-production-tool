import zipfile
import os
from pathlib import Path

root_dir = Path(r"c:\websites\ai video production tool")
zip_output_path = Path(r"c:\websites\ai video production tool\ai_video_production_system.zip")

# Directories and patterns to ignore to keep the zip fast, clean, and compatible with web LLMs
IGNORE_DIRS = {
    "node_modules", ".remotion", ".pytest_cache", ".pytest-tmp-v8", ".pytest-tmp-v9-green-1",
    ".pytest-tmp-v9-green-2", ".pytest-tmp-v9-green-composite", ".pytest-tmp-v9-red",
    ".pytest-tmp-v9-red-composite", ".git", ".venv", "__pycache__", ".playwright-mcp"
}

# Exclude giant multi-gigabyte video caches inside storage, but include deliverables scripts, transcripts, schemas, configs, and assets
def should_include(file_path: Path) -> bool:
    parts = file_path.parts
    for ignored in IGNORE_DIRS:
        if ignored in parts:
            return False
            
    # If in storage, only include non-huge files (transcripts, jsons, txts, schemas, py, md, png logos)
    if "storage" in parts:
        if file_path.suffix.lower() in [".mp4", ".wav", ".avi", ".mov"] and file_path.stat().st_size > 10 * 1024 * 1024:
            return False # skip huge >10MB binary video files in storage to stay within upload limits
            
    # Skip huge training video binaries in the main zip if > 25MB, or keep essential code & patterns
    if file_path.suffix.lower() in [".zip", ".tar", ".gz"] and file_path.name != zip_output_path.name:
        return False
        
    return True

print("Creating optimized zip package for LLM analysis...")
file_count = 0
total_uncompressed_bytes = 0

with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(root_dir):
        # prune ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp == zip_output_path:
                continue
            if should_include(fp):
                rel_path = fp.relative_to(root_dir)
                zf.write(fp, arcname=str(rel_path))
                file_count += 1
                total_uncompressed_bytes += fp.stat().st_size

zip_size_mb = zip_output_path.stat().st_size / (1024 * 1024)
print(f"Successfully created {zip_output_path.name}!")
print(f"Total files included: {file_count}")
print(f"Uncompressed size: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
print(f"Compressed Zip size: {zip_size_mb:.2f} MB")
