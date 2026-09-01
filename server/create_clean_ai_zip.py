import zipfile
import os
from pathlib import Path

root_dir = Path(r"c:\websites\ai video production tool")
zip_output_path = Path(r"c:\websites\ai video production tool\ai_video_production_tool_clean_for_ai.zip")

IGNORE_DIRS = {
    "node_modules", ".remotion", ".pytest_cache", ".pytest-tmp-v8", ".pytest-tmp-v9-green-1",
    ".pytest-tmp-v9-green-2", ".pytest-tmp-v9-green-composite", ".pytest-tmp-v9-red",
    ".pytest-tmp-v9-red-composite", ".git", ".venv", "__pycache__", ".playwright-mcp",
    "storage", "training videos data" # skip giant video binary storage folders for the AI upload zip
}

ALLOWED_EXTENSIONS = {
    ".py", ".mjs", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".yaml", ".yml",
    ".css", ".html", ".sh", ".env", ".gitignore", ".config"
}

print("Creating clean lightweight ZIP for LLM analysis...")
file_count = 0
total_uncompressed_bytes = 0

with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp.name in ["ai_video_production_system.zip", "ai_video_production_tool_clean_for_ai.zip"]:
                continue
            # Include text/code files and key reference templates
            if fp.suffix.lower() in ALLOWED_EXTENSIONS or fp.name in ["Dockerfile", "package.json", "requirements.txt"]:
                rel_path = fp.relative_to(root_dir)
                zf.write(fp, arcname=str(rel_path))
                file_count += 1
                total_uncompressed_bytes += fp.stat().st_size

zip_size_mb = zip_output_path.stat().st_size / (1024 * 1024)
print(f"Successfully created {zip_output_path.name}!")
print(f"Total files included: {file_count}")
print(f"Uncompressed size: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
print(f"Compressed Zip size: {zip_size_mb:.2f} MB")
