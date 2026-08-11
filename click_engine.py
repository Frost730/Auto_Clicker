"""
Click Engine Module
Handles mouse automation, position capturing, single/double click operations using pynput,
and high-precision performance worker execution with throttled UI CPS tracking.
"""

import ctypes
import ctypes.wintypes
import threading
import time
from typing import Callable, Optional, List, Tuple
from pynput.mouse import Button, Controller


class ClickEngine:
    def __init__(self):
        self.mouse = Controller()

        # Mapping string identifiers to pynput Button objects
        self.button_map = {
            "Left": Button.left,
            "Right": Button.right,
            "Middle": Button.middle
        }

    def get_current_position(self) -> tuple[int, int]:
        """
        Returns current cursor (x, y) coordinates with fallback support.
        """
        try:
            pos = self.mouse.position
            if pos is not None:
                return int(pos[0]), int(pos[1])
        except Exception:
            pass

        # Windows fallback via Win32 API
        try:
            pt = ctypes.wintypes.POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
        except Exception:
            pass

        return 0, 0

    def set_position(self, x: int, y: int):
        """
        Moves cursor to specified coordinates if not already there.
        """
        try:
            curr_x, curr_y = self.get_current_position()
            if curr_x != x or curr_y != y:
                self.mouse.position = (x, y)
        except Exception:
            try:
                ctypes.windll.user32.SetCursorPos(int(x), int(y))
            except Exception:
                pass

    def perform_click(
        self,
        button_name: str = "Left",
        click_type: str = "Single",
        position_mode: str = "Current Position",
        x: int = 0,
        y: int = 0
    ):
        """
        Executes mouse click(s) according to specified settings.
        """
        button = self.button_map.get(button_name, Button.left)
        clicks = 2 if click_type == "Double" else 1

        if position_mode == "Fixed Position":
            self.set_position(x, y)

        try:
            self.mouse.click(button, clicks)
        except Exception:
            self._win32_click_fallback(button_name, clicks)

    def _win32_click_fallback(self, button_name: str, clicks: int):
        try:
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            MOUSEEVENTF_RIGHTDOWN = 0x0008
            MOUSEEVENTF_RIGHTUP = 0x0010
            MOUSEEVENTF_MIDDLEDOWN = 0x0020
            MOUSEEVENTF_MIDDLEUP = 0x0040

            if button_name == "Right":
                down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
            elif button_name == "Middle":
                down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
            else:
                down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

            for _ in range(clicks):
                ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
        except Exception:
            pass


class ClickWorker(threading.Thread):
    """
    High-performance worker thread executing clicks asynchronously.
    Includes CPS (Clicks Per Second) performance monitoring and throttled UI updates.
    """
    def __init__(
        self,
        settings: dict,
        click_engine: ClickEngine,
        on_click_callback: Optional[Callable[[int, float], None]] = None,
        on_complete_callback: Optional[Callable[[], None]] = None,
        on_error_callback: Optional[Callable[[str], None]] = None
    ):
        super().__init__(daemon=True)
        self.settings = settings
        self.engine = click_engine
        self.on_click_callback = on_click_callback
        self.on_complete_callback = on_complete_callback
        self.on_error_callback = on_error_callback

        self.stop_event = threading.Event()
        self.clicks_performed = 0

    def stop(self):
        """
        Signals the worker thread to stop immediately.
        """
        self.stop_event.set()

    def run(self):
        interval = self.settings.get("total_seconds", 1.0)
        repeat_mode = self.settings.get("repeat_mode", "Infinite")
        repeat_count = self.settings.get("repeat_count", 0)
        mouse_button = self.settings.get("mouse_button", "Left")
        click_type = self.settings.get("click_type", "Single")
        position_mode = self.settings.get("position_mode", "Current Position")
        recorded_positions: List[Tuple[int, int]] = self.settings.get("recorded_positions", [])
        x = self.settings.get("x", 0)
        y = self.settings.get("y", 0)

        pos_index = 0
        start_time = time.perf_counter()
        last_ui_update = 0.0

        try:
            while not self.stop_event.is_set():
                # Check repeat count limit
                if repeat_mode == "Count" and self.clicks_performed >= repeat_count:
                    if self.on_complete_callback:
                        self.on_complete_callback()
                    break

                # Determine target position for sequence
                if position_mode == "Recorded Positions" and recorded_positions:
                    target_x, target_y = recorded_positions[pos_index]
                    pos_mode = "Fixed Position"
                    pos_index = (pos_index + 1) % len(recorded_positions)
                else:
                    target_x, target_y = x, y
                    pos_mode = position_mode

                # Execute click
                self.engine.perform_click(
                    button_name=mouse_button,
                    click_type=click_type,
                    position_mode=pos_mode,
                    x=target_x,
                    y=target_y
                )
                self.clicks_performed += 1

                # Calculate real-time CPS
                now = time.perf_counter()
                elapsed = now - start_time
                cps = self.clicks_performed / elapsed if elapsed > 0 else 0.0

                # Throttle UI callback to 20Hz (every 50ms) to ensure butter-smooth GUI execution
                if now - last_ui_update >= 0.05:
                    last_ui_update = now
                    if self.on_click_callback:
                        self.on_click_callback(self.clicks_performed, cps)

                # High-precision interruptible wait
                if self.stop_event.wait(interval):
                    break

            # Final update upon stopping
            if self.on_click_callback:
                final_elapsed = time.perf_counter() - start_time
                final_cps = self.clicks_performed / final_elapsed if final_elapsed > 0 else 0.0
                self.on_click_callback(self.clicks_performed, final_cps)

        except Exception as e:
            if self.on_error_callback:
                self.on_error_callback(str(e))
