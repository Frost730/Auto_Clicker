# ⚡ Auto Clicker

A modern, high-performance, feature-rich Windows Auto Clicker application built with Python, CustomTkinter, and pynput. Designed with an ultra-sleek user interface, real-time CPS performance monitoring, multi-point coordinate sequence recording, customizable preset profiles, single-instance process locking, and background system tray integration.

---

## 📐 Architecture & Workflow

```
Your GitHub Repository
        │
        ├── Source Code
        │
        ├── README & Specs
        │
        ├── GitHub Actions (CI/CD)
        │       ↓
        │   Auto Build
        │       ↓
        │   AutoClicker.exe
        │
        └── GitHub Releases
                ↓
         Download .exe
```

---

## ✨ Features

- **⚡ Sub-Millisecond High Precision**: Supports custom intervals in Hours, Minutes, Seconds, and Milliseconds (down to 1 ms).
- **🖱️ Mouse Controls**: Left, Right, and Middle mouse buttons with Single and Double click types.
- **📍 Flexible Positioning**:
  - *Current Cursor Position*: Clicks wherever the mouse is pointing.
  - *Fixed Coordinate Position*: Clicks exact screen `(X, Y)` coordinates captured in real time.
  - *Recorded Sequence*: Multi-point sequence clicking recorded across multiple screen locations.
- **📊 Real-time Performance Gauge**: Live CPS (Clicks Per Second) gauge and counter monitor.
- **⚙️ Profile Presets**: Save, load, and delete custom named profiles (e.g. *Fast Clicker*, *Game Profile*).
- **🔒 Single-Instance Protection**: Named Win32 mutex lock prevents duplicate processes or stacking tray icons. Clicking the executable while running brings the existing window to focus.
- **☀️ Light & 🌙 Dark Mode**: Real-time theme toggle persisted across sessions.
- **📌 Global Hotkeys**:
  - **`F6`**: Start / Stop Clicking
  - **`F7`**: Emergency Stop (restores window immediately)
- **📥 System Tray Minimization**: Run seamlessly in the background with tray icon controls.

---

## 🚀 Running Locally with Python

### Prerequisites
- Windows 10 or 11
- Python 3.10+ installed

### Setup & Execution
1. **Clone or Download Repository**:
   ```bash
   git clone https://github.com/your-username/Auto_Clicker.git
   cd Auto_Clicker
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python main.py
   ```

4. **Run Full Test Suite**:
   ```bash
   python tests/test_full_suite.py
   ```

---

## 🛠️ Building Standalone Windows Executable (.exe)

To build a zero-dependency standalone `AutoClicker.exe` executable for Windows:

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name="AutoClicker" --icon=assets/icon.ico --collect-all customtkinter main.py
```

The compiled `AutoClicker.exe` file will be generated inside the `dist/` directory.

---

## 🤖 GitHub Actions CI/CD & Release Automation

This repository contains automated GitHub Actions workflows located in `.github/workflows/`:

1. **Automated Windows Build (`build.yml`)**:
   - Triggers on every `push` and `pull_request`.
   - Provisions a `windows-latest` runner.
   - Installs dependencies and runs the 24-test suite.
   - Builds `AutoClicker.exe` using PyInstaller.
   - Uploads `AutoClicker.exe` as a workflow artifact.

2. **Automated Release Publishing (`release.yml`)**:
   - Triggers when a version tag (e.g. `v1.0.0`) is pushed to GitHub.
   - Builds the standalone executable and attaches `AutoClicker.exe` directly to the GitHub Release downloads!

---

## ⌨️ Hotkey Quick Reference

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`F6`** | **Start / Stop** | Toggles auto-clicking on/off |
| **`F7`** | **Emergency Stop** | Immediately halts clicking & restores main window |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
