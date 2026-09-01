import subprocess
import os

token = "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"
username = "sahil0052"
repo_name = "ai-video-production-tool"

# 1. Create a clean orphan branch without the 340MB historical blob bloat
subprocess.run(["git", "checkout", "--orphan", "deploy_main"], check=True)

# 2. Reset index and stage only clean source code, skills, docs, server, renderer, web, configs
subprocess.run(["git", "reset"], check=True)
subprocess.run(["git", "add", ".agents/", "docs/", "renderer/", "scripts/", "server/", "web/", "*.md", "*.json", "*.py", ".gitignore"], check=True)

# Commit
subprocess.run(["git", "commit", "-m", "feat: AI Video Production Engine with Google Flow Veo 3.1 & Vox Motion Graphics"], check=True)

# Delete old main and rename deploy_main to main
subprocess.run(["git", "branch", "-D", "main"], capture_output=True)
subprocess.run(["git", "branch", "-M", "main"], check=True)

# Push to GitHub
remote_url = f"https://{token}@github.com/{username}/{repo_name}.git"
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)

print("Pushing clean production codebase to GitHub main branch...")
res = subprocess.run(["git", "push", "-u", "origin", "main", "--force"], capture_output=True, text=True)
print(f"Return Code: {res.returncode}")
print(f"Stdout:\n{res.stdout}")
print(f"Stderr:\n{res.stderr}")

# Sanitize origin URL
clean_remote = f"https://github.com/{username}/{repo_name}.git"
subprocess.run(["git", "remote", "set-url", "origin", clean_remote])
