"""
System Tray Module
Handles system tray icon creation, context menu, and window minimization/restoration using pystray.
Ensures tray icon matches application icon perfectly.
"""

import os
import threading
from pathlib import Path
from typing import Callable, Optional
from PIL import Image
import pystray
from pystray import MenuItem as item
from paths import get_asset_path


class SystemTrayManager:
    def __init__(
        self,
        icon_path: str | Path = "assets/icon.ico",
        on_show: Optional[Callable[[], None]] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None
    ):
        self.icon_path = str(icon_path)
        self.on_show_cb = on_show
        self.on_start_cb = on_start
        self.on_stop_cb = on_stop
        self.on_emergency_stop_cb = on_emergency_stop
        self.on_exit_cb = on_exit

        self.tray_icon = None
        self.tray_thread = None

    def _load_image(self) -> Image.Image:
        # Resolve icon path using centralized asset path
        target_path = Path(self.icon_path)
        if not target_path.exists():
            target_path = get_asset_path("assets/icon.ico")

        if target_path.exists():
            try:
                img = Image.open(target_path)
                # Convert and scale smoothly to 64x64 RGBA matching window icon
                img_rgba = img.convert("RGBA")
                return img_rgba.resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

        # Fallback 64x64 colored square if asset missing
        return Image.new("RGBA", (64, 64), (59, 130, 246, 255))

    def create_tray(self):
        menu = pystray.Menu(
            item("Show Auto Clicker", lambda icon, item: self._call_cb(self.on_show_cb), default=True),
            pystray.Menu.SEPARATOR,
            item("Start", lambda icon, item: self._call_cb(self.on_start_cb)),
            item("Stop", lambda icon, item: self._call_cb(self.on_stop_cb)),
            item("Emergency Stop", lambda icon, item: self._call_cb(self.on_emergency_stop_cb)),
            pystray.Menu.SEPARATOR,
            item("Exit", lambda icon, item: self._call_cb(self.on_exit_cb))
        )

        image = self._load_image()
        self.tray_icon = pystray.Icon("AutoClicker", image, "AUTO CLICKER", menu)

    def _call_cb(self, cb):
        if cb:
            cb()

    def start(self):
        """
        Starts system tray icon in a dedicated daemon thread.
        """
        if self.tray_icon is None:
            self.create_tray()

        if self.tray_thread is None or not self.tray_thread.is_alive():
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

    def stop(self):
        """
        Stops the system tray icon cleanly.
        """
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
