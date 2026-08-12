"""
Centralized Application Paths Module
Ensures all user-writable data (logs, profiles, settings) is safely stored under %LOCALAPPDATA%\\AutoClicker\\
both when running python scripts and inside packaged PyInstaller executables.
"""

import os
import sys
from pathlib import Path

APP_NAME = "AutoClicker"

# Resolve base user data directory under LOCALAPPDATA
local_appdata = os.environ.get("LOCALAPPDATA")
if local_appdata:
    APP_DIR = Path(local_appdata) / APP_NAME
else:
    APP_DIR = Path.home() / "AppData" / "Local" / APP_NAME

LOG_DIR = APP_DIR / "logs"
PROFILE_DIR = APP_DIR / "profiles"
SETTINGS_FILE = APP_DIR / "settings.json"
PROFILES_FILE = APP_DIR / "profiles.json"
LOG_FILE = LOG_DIR / "app.log"


def ensure_app_directories():
    """
    Creates all required application directories under %LOCALAPPDATA%\\AutoClicker\\
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def get_asset_path(relative_path: str) -> Path:
    """
    Resolves read-only bundled assets (e.g. assets/icon.ico) safely both in source execution
    and inside PyInstaller's _MEIPASS extraction directory.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path
