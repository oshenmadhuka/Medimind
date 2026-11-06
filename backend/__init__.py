"""
MediMind Backend Package
Initializes UTF-8 encoding support for Windows console and worker threads.
"""
import sys

# Ensure UTF-8 output encoding across Windows consoles and worker threads
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
