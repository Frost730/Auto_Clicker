"""
Global Hotkeys Module
Implements global keyboard listener using pynput for F6 (Start/Stop) and F7 (Emergency Stop).
"""

from typing import Callable, Optional
from pynput import keyboard


class HotkeyManager:
    def __init__(
        self,
        on_toggle_start_stop: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None
    ):
        """
        :param on_toggle_start_stop: Callback executed when F6 is pressed.
        :param on_emergency_stop: Callback executed when F7 is pressed.
        """
        self.on_toggle_start_stop = on_toggle_start_stop
        self.on_emergency_stop = on_emergency_stop
        self.listener = None

    def _on_press(self, key):
        try:
            key_name = getattr(key, 'name', None)
            if key == keyboard.Key.f6 or key_name == "f6":
                if self.on_toggle_start_stop:
                    self.on_toggle_start_stop()
            elif key == keyboard.Key.f7 or key_name == "f7":
                if self.on_emergency_stop:
                    self.on_emergency_stop()
        except Exception:
            pass

    def start(self):
        """
        Starts the background global keyboard listener.
        """
        if self.listener is None or not self.listener.running:
            self.listener = keyboard.Listener(on_press=self._on_press)
            self.listener.daemon = True
            self.listener.start()

    def stop(self):
        """
        Stops the global keyboard listener.
        """
        if self.listener and self.listener.running:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
