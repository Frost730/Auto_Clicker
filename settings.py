"""
Settings & Profiles Management Module
Handles JSON configuration persistence and multiple profile management safely under %LOCALAPPDATA%\\AutoClicker\\
"""

import json
import os
import shutil
import logging
from pathlib import Path
from paths import SETTINGS_FILE, PROFILES_FILE, ensure_app_directories

DEFAULT_SETTINGS = {
    "hours": 0,
    "minutes": 0,
    "seconds": 1,
    "milliseconds": 500,
    "mouse_button": "Left",
    "click_type": "Single",
    "repeat_mode": "Infinite",
    "click_count": 1000,
    "position_mode": "Current Position",
    "x": 0,
    "y": 0,
    "appearance_mode": "Dark"
}


class SettingsManager:
    def __init__(self, filepath: str | Path = SETTINGS_FILE):
        self.filepath = Path(filepath)
        ensure_app_directories()

    def load_settings(self) -> dict:
        if not self.filepath.exists():
            self.save_settings(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Settings root must be a JSON object")

            validated = dict(DEFAULT_SETTINGS)
            for key, default_val in DEFAULT_SETTINGS.items():
                if key in data:
                    val = data[key]
                    if isinstance(default_val, int) and isinstance(val, (int, float)):
                        validated[key] = int(val)
                    elif isinstance(default_val, str) and isinstance(val, str):
                        validated[key] = val

            return validated

        except Exception:
            corrupted_backup = self.filepath.with_suffix(".corrupted")
            try:
                shutil.copyfile(self.filepath, corrupted_backup)
            except Exception:
                pass
            
            self.save_settings(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)

    def save_settings(self, settings: dict) -> bool:
        try:
            ensure_app_directories()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception:
            return False

    def reset_defaults(self) -> dict:
        self.save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)


class ProfileManager:
    """
    Manages named profiles (Default, Fast Clicking, Slow Clicking, Game Profile, Custom, etc.)
    stored safely under %LOCALAPPDATA%\\AutoClicker\\
    """
    def __init__(self, filepath: str | Path = PROFILES_FILE):
        self.filepath = Path(filepath)
        ensure_app_directories()
        self.default_profiles = {
            "Default": dict(DEFAULT_SETTINGS),
            "Fast Clicking": {**DEFAULT_SETTINGS, "seconds": 0, "milliseconds": 100},
            "Slow Clicking": {**DEFAULT_SETTINGS, "seconds": 5, "milliseconds": 0},
            "Game Profile": {**DEFAULT_SETTINGS, "seconds": 0, "milliseconds": 50, "click_type": "Double"},
            "Custom": dict(DEFAULT_SETTINGS)
        }

    def load_profiles(self) -> tuple[dict, str]:
        """
        Loads profiles catalog and current active profile name.
        """
        if not self.filepath.exists():
            data = {
                "active_profile": "Default",
                "profiles": dict(self.default_profiles)
            }
            self.save_profiles_data(data)
            return data["profiles"], data["active_profile"]

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            profiles = data.get("profiles", {})
            active = data.get("active_profile", "Default")

            if not isinstance(profiles, dict) or not profiles:
                profiles = dict(self.default_profiles)

            if active not in profiles:
                active = "Default" if "Default" in profiles else list(profiles.keys())[0]

            return profiles, active
        except Exception:
            data = {
                "active_profile": "Default",
                "profiles": dict(self.default_profiles)
            }
            self.save_profiles_data(data)
            return data["profiles"], data["active_profile"]

    def save_profiles_data(self, data: dict) -> bool:
        try:
            ensure_app_directories()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception:
            return False

    def save_profile(self, name: str, settings: dict) -> tuple[dict, str]:
        profiles, active = self.load_profiles()
        profiles[name] = settings
        active = name
        self.save_profiles_data({"active_profile": active, "profiles": profiles})
        return profiles, active

    def set_active_profile(self, name: str) -> tuple[dict, str]:
        profiles, active = self.load_profiles()
        if name in profiles:
            active = name
            self.save_profiles_data({"active_profile": active, "profiles": profiles})
        return profiles, active

    def delete_profile(self, name: str) -> tuple[dict, str, bool]:
        """
        Deletes specified profile. Safely prevents deleting "Default" if it's the last profile
        and handles switching active profile if deleting the current active profile.
        """
        profiles, active = self.load_profiles()

        if name not in profiles:
            return profiles, active, False

        if len(profiles) <= 1 or name == "Default":
            return profiles, active, False

        del profiles[name]

        if active == name:
            active = "Default" if "Default" in profiles else list(profiles.keys())[0]

        self.save_profiles_data({"active_profile": active, "profiles": profiles})
        return profiles, active, True
