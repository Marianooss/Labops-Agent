"""start_local.py — One-script local startup for LabOps Agent demo.

Starts the FastAPI backend and the Slack Bolt client in parallel,
then seeds the database. Cross-platform (Windows / macOS / Linux).

Usage:
    python scripts/start_local.py

Requires:
    - PostgreSQL running locally (or set DATABASE_URL)
    - Python dependencies installed (pip install -r requirements.txt)
    - .env configured (copy from .env.example)
"""
import os
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")


def run_in_background(cmd, cwd):
    """Launch a process in the background."""
    if sys.platform == "win32":
        # Windows: use creationflags to detach
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        # Unix: nohup + redirect output
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def main():
    print("=" * 60)
    print(" LabOps Agent — Local Demo Startup")
    print("=" * 60)

    # 1. Seed database
    print("\n[1/3] Seeding database...")
    init_db = subprocess.run(
        [sys.executable, "scripts/init_db.py"],
        cwd=PROJECT_ROOT,
    )
    if init_db.returncode != 0:
        print("WARNING: Database init failed. Continuing anyway...")

    # 2. Start FastAPI backend
    print("\n[2/3] Starting FastAPI backend on http://localhost:8000 ...")
    backend_proc = run_in_background(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR,
    )
    time.sleep(3)

    # 3. Start Slack client
    print("\n[3/3] Starting Slack Bolt client...")
    slack_proc = run_in_background(
        [sys.executable, "slack_client.py"],
        cwd=BACKEND_DIR,
    )

    print("\n" + "=" * 60)
    print(" All services started!")
    print(" - API docs: http://localhost:8000/docs")
    print(" - Test alert: curl \"http://localhost:8000/alert/trigger?reagent_name=TSH\"")
    print("=" * 60)
    print(" Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        slack_proc.terminate()
        backend_proc.wait(timeout=5)
        slack_proc.wait(timeout=5)
        print("Done.")


if __name__ == "__main__":
    main()
