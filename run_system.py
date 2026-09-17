"""
LANDSAFE-NER — Unified System Launcher
Starts FastAPI Backend (Port 8000) and Vite React Frontend (Port 5173).
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def run_backend():
    print("[1/2] Starting FastAPI Backend on http://localhost:8000 ...")
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    return subprocess.Popen(cmd, cwd=ROOT_DIR)

def run_frontend():
    print("[2/2] Starting Vite React Frontend on http://localhost:5173 ...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    cmd = [npm_cmd, "run", "dev"]
    return subprocess.Popen(cmd, cwd=ROOT_DIR / "frontend")

def main():
    print("=" * 70)
    print("   LANDSAFE-NER: Landslide & Multi-Hazard Risk Monitoring System")
    print("   Northeast India — Academic Prototype (B.Tech AI & Data Science)")
    print("=" * 70)
    print("DISCLAIMER: LANDSAFE-NER is an academic prototype for demonstration")
    print("purposes only. Not an official government disaster warning system.\n")

    backend_proc = run_backend()
    time.sleep(2)
    frontend_proc = run_frontend()

    print("\n[OK] System running!")
    print("   * Frontend Dashboard: http://localhost:5173")
    print("   * Backend API Docs:   http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both servers...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Done. All services stopped.")

if __name__ == "__main__":
    main()
