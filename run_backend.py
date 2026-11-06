#!/usr/bin/env python3
"""
MediMind — Backend Startup Script
Run: python run_backend.py
"""
import subprocess
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    print("[*] Starting MediMind Backend...")
    print("=" * 50)

    # Check .env
    if not os.path.exists(".env"):
        print("[!] No .env file found. Copying from .env.example...")
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print("[OK] Created .env — please add your GROQ_API_KEY before continuing!")
            print("\nEdit .env and add your API key:")
            print("  GROQ_API_KEY=gsk_your_key_here")
            print("\nGet your free key at: https://console.groq.com")
            sys.exit(1)
        else:
            print("[X] No .env.example found")
            sys.exit(1)

    # Check for API key
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key_here":
        print("[X] GROQ_API_KEY not set in .env")
        print("   Get your free key at: https://console.groq.com")
        sys.exit(1)

    # Prefer .venv python if available
    venv_py = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
    python_exec = venv_py if os.path.exists(venv_py) else sys.executable

    print("[OK] Environment configured")
    print("[*] Starting server at http://localhost:8000")
    print("[*] API Docs at http://localhost:8000/docs")
    print("=" * 50)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    subprocess.run([
        python_exec, "-m", "uvicorn",
        "backend.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "info",
    ], env=env)

if __name__ == "__main__":
    main()
