"""Launch the AI Hedge Fund web app. Run: poetry run python run_webapp.py"""
import subprocess
import sys
import os
import webbrowser
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "webapp", "frontend", "dist")

# Build frontend if not already built
if not os.path.isdir(DIST):
    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=os.path.join(ROOT, "webapp", "frontend"), check=True)

print("\n  AI Hedge Fund is running at: http://localhost:8000\n")

# Open browser after a short delay
def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

import threading
threading.Thread(target=open_browser, daemon=True).start()

# Start the server
os.environ["PYTHONIOENCODING"] = "utf-8"
import uvicorn
uvicorn.run("webapp.backend.main:app", host="127.0.0.1", port=8000, timeout_keep_alive=300)
