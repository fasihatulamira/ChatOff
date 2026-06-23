"""Resolve application directory and load .env from a stable location."""
import os
import sys


def get_app_dir() -> str:
    """Project root when running from source; exe folder when frozen (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_env() -> None:
    """Load .env from the application directory (not the process working directory)."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(get_app_dir(), ".env"))
