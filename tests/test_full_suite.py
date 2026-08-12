import os
import sys
import time
from pathlib import Path

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import AutoClickerGUI
from click_engine import ClickEngine, ClickWorker
from hotkeys import HotkeyManager
from settings import SettingsManager, DEFAULT_SETTINGS
from recorder import PositionRecorder
from tray import SystemTrayManager
from paths import APP_DIR, LOG_DIR, PROFILE_DIR, SETTINGS_FILE, PROFILES_FILE, LOG_FILE, ensure_app_directories

print("==================================================")
print("   AUTO CLICKER COMPREHENSIVE 25-TEST SUITE       ")
print("==================================================")

passed_tests = []

def run_test(test_num, title, func):
    try:
        func()
        print(f"Test {test_num:02d}: {title:45s} [ PASSED ]")
        passed_tests.append(test_num)
    except Exception as e:
        print(f"Test {test_num:02d}: {title:45s} [ FAILED ] -> {e}")

app = AutoClickerGUI()
app.withdraw()

# 1. GUI startup
def test_1():
    assert app.title() == "AUTO CLICKER"
    assert app.status == "STOPPED"
run_test(1, "GUI startup", test_1)

# 2. GUI responsiveness
def test_2():
    app.update_click_counter(42, 10.5)
    assert app.click_count == 42
run_test(2, "GUI responsiveness", test_2)

# 3. Interval validation
def test_3():
    app.hours_var.set("0")
    app.minutes_var.set("0")
    app.seconds_var.set("0")
    app.milliseconds_var.set("0")
    assert app.validate_inputs() is None
    assert app.error_banner.cget("text") == "Click interval must be greater than 0."
run_test(3, "Interval validation (Zero Check)", test_3)

# 4. 100 ms interval
def test_4():
    app.hours_var.set("0"); app.minutes_var.set("0"); app.seconds_var.set("0"); app.milliseconds_var.set("100")
    res = app.validate_inputs()
    assert res["total_seconds"] == 0.1
run_test(4, "100 ms interval", test_4)

# 5. 500 ms interval
def test_5():
    app.hours_var.set("0"); app.minutes_var.set("0"); app.seconds_var.set("0"); app.milliseconds_var.set("500")
    res = app.validate_inputs()
    assert res["total_seconds"] == 0.5
run_test(5, "500 ms interval", test_5)

# 6. 1 second interval
def test_6():
    app.hours_var.set("0"); app.minutes_var.set("0"); app.seconds_var.set("1"); app.milliseconds_var.set("0")
    res = app.validate_inputs()
    assert res["total_seconds"] == 1.0
run_test(6, "1 second interval", test_6)

# 7. 1.5 second interval
def test_7():
    app.hours_var.set("0"); app.minutes_var.set("0"); app.seconds_var.set("1"); app.milliseconds_var.set("500")
    res = app.validate_inputs()
    assert res["total_seconds"] == 1.5
run_test(7, "1.5 second interval", test_7)

# 8. 1 minute interval
def test_8():
    app.hours_var.set("0"); app.minutes_var.set("1"); app.seconds_var.set("0"); app.milliseconds_var.set("0")
    res = app.validate_inputs()
    assert res["total_seconds"] == 60.0
run_test(8, "1 minute interval", test_8)

# 9. Combined hour/minute/second/millisecond interval
def test_9():
    app.hours_var.set("1"); app.minutes_var.set("30"); app.seconds_var.set("15"); app.milliseconds_var.set("250")
    res = app.validate_inputs()
    assert res["total_seconds"] == 5415.25
run_test(9, "Combined h/m/s/ms interval", test_9)

# 10. Left click
def test_10():
    engine = ClickEngine()
    engine.perform_click("Left", "Single", "Current Position")
run_test(10, "Left click execution", test_10)

# 11. Right click
def test_11():
    engine = ClickEngine()
    engine.perform_click("Right", "Single", "Current Position")
run_test(11, "Right click execution", test_11)

# 12. Middle click
def test_12():
    engine = ClickEngine()
    engine.perform_click("Middle", "Single", "Current Position")
run_test(12, "Middle click execution", test_12)

# 13. Single click
def test_13():
    engine = ClickEngine()
    engine.perform_click("Left", "Single", "Current Position")
run_test(13, "Single click mode", test_13)

# 14. Double click
def test_14():
    engine = ClickEngine()
    engine.perform_click("Left", "Double", "Current Position")
run_test(14, "Double click mode", test_14)

# 15. Fixed position
def test_15():
    engine = ClickEngine()
    engine.perform_click("Left", "Single", "Fixed Position", x=100, y=200)
run_test(15, "Fixed position mode", test_15)

# 16. Current cursor position
def test_16():
    pos = app.click_engine.get_current_position()
    assert isinstance(pos, tuple) and len(pos) == 2
run_test(16, "Current cursor position query", test_16)

# 17. Finite click count
def test_17():
    clicks = []
    done = [False]
    settings = {"total_seconds": 0.01, "repeat_mode": "Count", "repeat_count": 3, "mouse_button": "Left", "click_type": "Single", "position_mode": "Current Position"}
    w = ClickWorker(settings, ClickEngine(), lambda c, cps: clicks.append(c), lambda: done.__setitem__(0, True))
    w.start()
    w.join(timeout=2.0)
    assert done[0] is True
    assert 3 in clicks
run_test(17, "Finite click count execution", test_17)

# 18. Infinite mode
def test_18():
    settings = {"total_seconds": 1.0, "repeat_mode": "Infinite", "repeat_count": 0, "mouse_button": "Left", "click_type": "Single", "position_mode": "Current Position"}
    w = ClickWorker(settings, ClickEngine())
    w.start()
    time.sleep(0.1)
    w.stop()
    w.join(timeout=1.0)
    assert not w.is_alive()
run_test(18, "Infinite mode start & stop", test_18)

# 19. F6 start/stop
def test_19():
    f6_called = [False]
    hm = HotkeyManager(on_toggle_start_stop=lambda: f6_called.__setitem__(0, True))
    hm.start()
    from pynput import keyboard
    hm._on_press(keyboard.Key.f6)
    assert f6_called[0] is True
    hm.stop()
run_test(19, "F6 global hotkey toggle", test_19)

# 20. F7 emergency stop
def test_20():
    f7_called = [False]
    hm = HotkeyManager(on_emergency_stop=lambda: f7_called.__setitem__(0, True))
    hm.start()
    from pynput import keyboard
    hm._on_press(keyboard.Key.f7)
    assert f7_called[0] is True
    hm.stop()
run_test(20, "F7 emergency stop hotkey", test_20)

# 21. Application shutdown
def test_21():
    assert hasattr(app, "on_closing")
run_test(21, "Application shutdown handlers", test_21)

# 22. Settings save/load
def test_22():
    test_path = APP_DIR / "test_suite_cfg.json"
    sm = SettingsManager(test_path)
    sm.save_settings({"seconds": 12, "mouse_button": "Right"})
    loaded = sm.load_settings()
    assert loaded["seconds"] == 12
    assert loaded["mouse_button"] == "Right"
    if test_path.exists(): test_path.unlink()
run_test(22, "Settings save/load", test_22)

# 23. Corrupted settings
def test_23():
    test_path = APP_DIR / "test_corrupt_cfg.json"
    sm = SettingsManager(test_path)
    with open(test_path, "w") as f: f.write("BAD JSON")
    loaded = sm.load_settings()
    assert loaded == DEFAULT_SETTINGS
    if test_path.exists(): test_path.unlink()
    corrupt_backup = test_path.with_suffix(".corrupted")
    if corrupt_backup.exists(): corrupt_backup.unlink()
run_test(23, "Corrupted settings recovery", test_23)

# 24. Invalid input
def test_24():
    app.hours_var.set("INVALID")
    assert app.validate_inputs() is None
    assert app.error_banner.cget("text") == "Interval fields must be integers."
run_test(24, "Invalid non-integer input rejection", test_24)

# 25. LOCALAPPDATA Centralized Paths Verification
def test_25():
    ensure_app_directories()
    assert APP_DIR.exists()
    assert LOG_DIR.exists()
    assert PROFILE_DIR.exists()
    assert str(APP_DIR).endswith("AutoClicker")
run_test(25, "LOCALAPPDATA paths creation & verification", test_25)

app.destroy()

print("==================================================")
print(f"   TOTAL TESTS PASSED: {len(passed_tests)} / 25")
print("==================================================")

if len(passed_tests) == 25:
    print("ALL 25 TEST SUITE SCENARIOS VERIFIED SUCCESSFULLY!")
    sys.exit(0)
else:
    sys.exit(1)
