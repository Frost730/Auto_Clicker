import sys
import os
import ctypes
from ctypes import wintypes
import logging
import customtkinter as ctk
from click_engine import ClickEngine, ClickWorker
from hotkeys import HotkeyManager
from settings import SettingsManager, ProfileManager
from recorder import PositionRecorder
from tray import SystemTrayManager

# --- SINGLE INSTANCE MUTEX CHECK ---
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "AutoClicker_SingleInstance_Mutex_v1"

def check_single_instance():
    try:
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "AUTO CLICKER")
            if hwnd:
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
            return False, mutex
        return True, mutex
    except Exception:
        return True, None


# --- LOGGING SETUP ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=os.path.join("logs", "autoclicker.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Default appearance mode to Light
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class DeleteProfileDialog(ctk.CTkToplevel):
    """
    Modal dialog allowing the user to select and delete any custom profile.
    """
    def __init__(self, parent, deletable_profiles: list, on_confirm_delete):
        super().__init__(parent)
        self.title("Delete Profile")
        self.geometry("380 x 220")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()

        self.on_confirm_delete = on_confirm_delete
        self.selected_profile_var = ctk.StringVar(value=deletable_profiles[0])

        ctk.CTkLabel(
            self,
            text="Select Profile to Delete:",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(22, 10))

        self.dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.selected_profile_var,
            values=deletable_profiles,
            width=260,
            height=34,
            corner_radius=8
        )
        self.dropdown.pack(pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=18)

        ctk.CTkButton(
            btn_frame,
            text="Delete Profile",
            width=120, height=32, corner_radius=8,
            fg_color="#E11D48", hover_color="#BE123C", text_color="#FFFFFF",
            command=self.confirm_delete
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100, height=32, corner_radius=8,
            fg_color="#64748B", hover_color="#475569", text_color="#FFFFFF",
            command=self.destroy
        ).pack(side="left", padx=10)

    def confirm_delete(self):
        target = self.selected_profile_var.get()
        self.destroy()
        if self.on_confirm_delete:
            self.on_confirm_delete(target)


class AutoClickerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        logging.info("Application starting up")

        self.title("AUTO CLICKER")
        
        # Window dimensions & resizable configuration
        self.geometry("690 x 920")
        self.minsize(540, 750)
        self.resizable(True, True)

        # Application Icon
        icon_path = os.path.abspath("assets/icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Core engine, worker, hotkeys, settings, recorder & tray managers
        self.click_engine = ClickEngine()
        self.settings_manager = SettingsManager()
        self.profile_manager = ProfileManager()
        self.position_recorder = PositionRecorder()
        self.worker = None

        self.hotkey_manager = HotkeyManager(
            on_toggle_start_stop=lambda: self.after(0, self.toggle_start_stop),
            on_emergency_stop=lambda: self.after(0, self.emergency_stop)
        )

        self.tray_manager = SystemTrayManager(
            icon_path=icon_path,
            on_show=lambda: self.after(0, self.restore_from_tray),
            on_start=lambda: self.after(0, self.start_clicking),
            on_stop=lambda: self.after(0, self.stop_clicking),
            on_emergency_stop=lambda: self.after(0, self.emergency_stop),
            on_exit=lambda: self.after(0, self.exit_app)
        )

        # Application state variables
        self.status = "STOPPED"  # STOPPED, RUNNING, COMPLETED, ERROR
        self.click_count = 0

        # UI Variables & Card references list for dynamic theme styling
        self.card_frames = []

        self.active_profile_var = ctk.StringVar(value="Default")
        self.theme_mode_var = ctk.StringVar(value="Light")

        self.hours_var = ctk.StringVar(value="0")
        self.minutes_var = ctk.StringVar(value="0")
        self.seconds_var = ctk.StringVar(value="1")
        self.milliseconds_var = ctk.StringVar(value="500")

        self.mouse_button_var = ctk.StringVar(value="Left")
        self.click_type_var = ctk.StringVar(value="Single")

        self.repeat_mode_var = ctk.StringVar(value="Infinite")
        self.repeat_count_var = ctk.StringVar(value="1000")

        self.position_mode_var = ctk.StringVar(value="Current Position")
        self.pos_x_var = ctk.StringVar(value="0")
        self.pos_y_var = ctk.StringVar(value="0")
        self.recorded_seq_label_var = ctk.StringVar(value="Recorded: 0 points")

        # Create GUI layout
        self.create_widgets()

        # Load initial profiles catalog & settings
        self.refresh_profiles_ui()

        # Start background managers
        self.hotkey_manager.start()
        self.tray_manager.start()

        # Clean window close handler
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def create_widgets(self):
        # Container frame with scrolling / padding
        main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=18, pady=18)

        # Header Title & Theme Switcher (Light / Dark only)
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 12))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text="AUTO CLICKER",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(side="left")

        # Theme Switcher Segmented Control (Light & Dark)
        header_actions = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_actions.pack(side="right")

        ctk.CTkLabel(
            header_actions, text="Theme:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 6))

        self.theme_segmented_btn = ctk.CTkSegmentedButton(
            header_actions,
            values=["Light", "Dark"],
            variable=self.theme_mode_var,
            command=self.on_theme_changed,
            height=30, corner_radius=8
        )
        self.theme_segmented_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            header_actions, text="Minimize to Tray", width=125, height=30, corner_radius=8,
            command=self.minimize_to_tray
        ).pack(side="left")

        # --- 0. PROFILES SELECTOR BAR CARD ---
        profile_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        profile_frame.pack(fill="x", pady=6)
        self.card_frames.append(profile_frame)

        ctk.CTkLabel(
            profile_frame, text="Preset Profile",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        prof_controls = ctk.CTkFrame(profile_frame, fg_color="transparent")
        prof_controls.pack(fill="x", padx=14, pady=(0, 12))

        self.profile_dropdown = ctk.CTkOptionMenu(
            prof_controls, variable=self.active_profile_var,
            values=["Default"], command=self.on_profile_selected,
            width=210, height=34, corner_radius=8
        )
        self.profile_dropdown.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            prof_controls, text="Save Profile", width=115, height=34, corner_radius=8,
            fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF",
            command=self.prompt_save_new_profile
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            prof_controls, text="Delete Profile", width=115, height=34, corner_radius=8,
            fg_color="#E11D48", hover_color="#BE123C", text_color="#FFFFFF",
            command=self.prompt_delete_profile
        ).pack(side="left", padx=5)

        # --- 1. CLICK INTERVAL CARD ---
        interval_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        interval_frame.pack(fill="x", pady=6)
        self.card_frames.append(interval_frame)

        ctk.CTkLabel(
            interval_frame, text="Click Interval",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        fields_grid = ctk.CTkFrame(interval_frame, fg_color="transparent")
        fields_grid.pack(fill="x", padx=14, pady=(0, 12))

        units = [
            ("Hours", self.hours_var),
            ("Minutes", self.minutes_var),
            ("Seconds", self.seconds_var),
            ("Milliseconds", self.milliseconds_var)
        ]

        for i, (label_text, var) in enumerate(units):
            col_frame = ctk.CTkFrame(fields_grid, fg_color="transparent")
            col_frame.grid(row=0, column=i, padx=6, sticky="ew")
            fields_grid.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(col_frame, text=label_text, font=ctk.CTkFont(size=12, weight="bold")).pack()
            entry = ctk.CTkEntry(col_frame, textvariable=var, justify="center", height=34, corner_radius=8, font=ctk.CTkFont(size=14))
            entry.pack(pady=4, fill="x")

        # --- 2. MOUSE BUTTON CARD ---
        button_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        button_frame.pack(fill="x", pady=6)
        self.card_frames.append(button_frame)

        ctk.CTkLabel(
            button_frame, text="Mouse Button",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        btn_options_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        btn_options_frame.pack(fill="x", padx=14, pady=(0, 12))

        for btn_name in ["Left", "Right", "Middle"]:
            ctk.CTkRadioButton(
                btn_options_frame, text=btn_name,
                variable=self.mouse_button_var, value=btn_name,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(side="left", expand=True, anchor="w", padx=12)

        # --- 3. CLICK TYPE CARD ---
        type_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        type_frame.pack(fill="x", pady=6)
        self.card_frames.append(type_frame)

        ctk.CTkLabel(
            type_frame, text="Click Type",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        type_options_frame = ctk.CTkFrame(type_frame, fg_color="transparent")
        type_options_frame.pack(fill="x", padx=14, pady=(0, 12))

        for type_name in ["Single", "Double"]:
            ctk.CTkRadioButton(
                type_options_frame, text=f"{type_name} Click",
                variable=self.click_type_var, value=type_name,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(side="left", expand=True, anchor="w", padx=12)

        # --- 4. REPEAT MODE CARD ---
        repeat_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        repeat_frame.pack(fill="x", pady=6)
        self.card_frames.append(repeat_frame)

        ctk.CTkLabel(
            repeat_frame, text="Repeat Mode",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        rep_inf_rb = ctk.CTkRadioButton(
            repeat_frame, text="Infinite",
            variable=self.repeat_mode_var, value="Infinite",
            command=self.toggle_repeat_entry,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        rep_inf_rb.pack(anchor="w", padx=20, pady=4)

        rep_count_subframe = ctk.CTkFrame(repeat_frame, fg_color="transparent")
        rep_count_subframe.pack(fill="x", padx=20, pady=(2, 10))

        rep_num_rb = ctk.CTkRadioButton(
            rep_count_subframe, text="Number of clicks",
            variable=self.repeat_mode_var, value="Count",
            command=self.toggle_repeat_entry,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        rep_num_rb.pack(side="left")

        self.repeat_count_entry = ctk.CTkEntry(
            rep_count_subframe, textvariable=self.repeat_count_var,
            width=120, height=32, corner_radius=8, justify="center"
        )
        self.repeat_count_entry.pack(side="left", padx=14)
        self.repeat_count_entry.configure(state="disabled")

        # --- 5. CLICK POSITION CARD ---
        pos_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        pos_frame.pack(fill="x", pady=6)
        self.card_frames.append(pos_frame)

        ctk.CTkLabel(
            pos_frame, text="Click Position",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        pos_curr_rb = ctk.CTkRadioButton(
            pos_frame, text="Current Cursor Position",
            variable=self.position_mode_var, value="Current Position",
            command=self.toggle_position_entries,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        pos_curr_rb.pack(anchor="w", padx=20, pady=4)

        pos_fixed_rb = ctk.CTkRadioButton(
            pos_frame, text="Fixed Position",
            variable=self.position_mode_var, value="Fixed Position",
            command=self.toggle_position_entries,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        pos_fixed_rb.pack(anchor="w", padx=20, pady=4)

        fixed_inputs_frame = ctk.CTkFrame(pos_frame, fg_color="transparent")
        fixed_inputs_frame.pack(fill="x", padx=20, pady=(2, 6))

        ctk.CTkLabel(fixed_inputs_frame, text="X:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 4))
        self.x_entry = ctk.CTkEntry(fixed_inputs_frame, textvariable=self.pos_x_var, width=85, height=32, corner_radius=8, justify="center")
        self.x_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(fixed_inputs_frame, text="Y:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 4))
        self.y_entry = ctk.CTkEntry(fixed_inputs_frame, textvariable=self.pos_y_var, width=85, height=32, corner_radius=8, justify="center")
        self.y_entry.pack(side="left", padx=(0, 18))

        self.capture_btn = ctk.CTkButton(
            fixed_inputs_frame, text="Capture Position",
            width=150, height=32, corner_radius=8, command=self.capture_position_clicked
        )
        self.capture_btn.pack(side="left")

        # Recorded Positions Radio & Sequence Controls
        pos_rec_rb = ctk.CTkRadioButton(
            pos_frame, text="Recorded Positions Sequence",
            variable=self.position_mode_var, value="Recorded Positions",
            command=self.toggle_position_entries,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        pos_rec_rb.pack(anchor="w", padx=20, pady=(8, 4))

        rec_ctrl_frame = ctk.CTkFrame(pos_frame, fg_color="transparent")
        rec_ctrl_frame.pack(fill="x", padx=20, pady=(2, 10))

        # High Contrast Add Position Button
        self.add_pos_btn = ctk.CTkButton(
            rec_ctrl_frame, text="+ Add Position", width=145, height=34, corner_radius=8,
            fg_color="#6366F1", hover_color="#4F46E5",
            text_color="#FFFFFF", text_color_disabled="#64748B",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.add_current_pos_to_recorder
        )
        self.add_pos_btn.pack(side="left", padx=(0, 10))

        self.clear_pos_btn = ctk.CTkButton(
            rec_ctrl_frame, text="Clear Sequence", width=145, height=34, corner_radius=8,
            fg_color="#64748B", hover_color="#475569",
            text_color="#FFFFFF", text_color_disabled="#64748B",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clear_recorded_positions
        )
        self.clear_pos_btn.pack(side="left", padx=5)

        self.rec_status_label = ctk.CTkLabel(
            rec_ctrl_frame, textvariable=self.recorded_seq_label_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10B981"
        )
        self.rec_status_label.pack(side="left", padx=12)

        self.toggle_position_entries()

        # --- 6. ACTION & PERFORMANCE MONITOR SECTION ---
        action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=10)

        self.start_stop_btn = ctk.CTkButton(
            action_frame, text="START",
            font=ctk.CTkFont(size=22, weight="bold"),
            height=56, corner_radius=14, fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF",
            command=self.toggle_start_stop
        )
        self.start_stop_btn.pack(fill="x", pady=4)

        stats_frame = ctk.CTkFrame(action_frame, corner_radius=10)
        stats_frame.pack(fill="x", pady=6, ipady=4)
        self.card_frames.append(stats_frame)

        self.counter_label = ctk.CTkLabel(
            stats_frame, text="Clicks: 0",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#0284C7"
        )
        self.counter_label.pack(side="left", padx=14)

        self.cps_label = ctk.CTkLabel(
            stats_frame, text="Speed: 0.0 CPS",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#10B981"
        )
        self.cps_label.pack(side="left", expand=True)

        self.status_badge = ctk.CTkLabel(
            stats_frame, text="Status: STOPPED",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#E11D48"
        )
        self.status_badge.pack(side="right", padx=14)

        # --- 7. SETTINGS ACTIONS & HOTKEYS LEGEND ---
        cfg_bar = ctk.CTkFrame(main_frame, fg_color="transparent")
        cfg_bar.pack(fill="x", pady=4)

        ctk.CTkButton(
            cfg_bar, text="Save Settings", width=140, height=32, corner_radius=8,
            fg_color="#0284C7", hover_color="#0369A1", text_color="#FFFFFF",
            command=self.save_current_settings
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            cfg_bar, text="Reset Defaults", width=140, height=32, corner_radius=8,
            command=self.reset_default_settings
        ).pack(side="right", padx=5)

        hotkeys_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        hotkeys_frame.pack(fill="x", pady=(8, 4))
        self.card_frames.append(hotkeys_frame)

        ctk.CTkLabel(
            hotkeys_frame,
            text="F6 — Start / Stop      |      F7 — Emergency Stop",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=10)

        # Error notification banner
        self.error_banner = ctk.CTkLabel(
            main_frame, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#E11D48"
        )
        self.error_banner.pack(pady=4)

    def on_theme_changed(self, new_theme: str):
        """
        Handles dynamic switching between Light and Dark mode.
        """
        self.apply_theme_mode(new_theme)
        self.show_error(f"Appearance mode set to '{new_theme}'")
        logging.info(f"Appearance mode changed to: {new_theme}")

    def apply_theme_mode(self, new_theme: str):
        if new_theme not in ["Light", "Dark"]:
            new_theme = "Light"

        ctk.set_appearance_mode(new_theme)

        if new_theme == "Light":
            for card in self.card_frames:
                card.configure(fg_color="#F8FAFC", border_width=1, border_color="#CBD5E1")
            self.title_label.configure(text_color="#0284C7")
        else:  # Dark
            for card in self.card_frames:
                card.configure(fg_color="#1E293B", border_width=0)
            self.title_label.configure(text_color="#38BDF8")

    def restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def minimize_to_tray(self):
        self.withdraw()
        self.show_error("Minimized to System Tray. Use F6/F7 or tray icon.")

    def refresh_profiles_ui(self):
        profiles, active = self.profile_manager.load_profiles()
        profile_names = list(profiles.keys())
        self.profile_dropdown.configure(values=profile_names)
        self.active_profile_var.set(active)
        
        current_profile_data = profiles.get(active, {})
        theme_mode = current_profile_data.get("appearance_mode", "Light")
        if theme_mode not in ["Light", "Dark"]:
            theme_mode = "Light"

        self.theme_mode_var.set(theme_mode)
        self.apply_theme_mode(theme_mode)

        self.apply_profile_settings(current_profile_data)

    def apply_profile_settings(self, settings: dict):
        if not settings:
            return
        self.hours_var.set(str(settings.get("hours", 0)))
        self.minutes_var.set(str(settings.get("minutes", 0)))
        self.seconds_var.set(str(settings.get("seconds", 1)))
        self.milliseconds_var.set(str(settings.get("milliseconds", 500)))

        self.mouse_button_var.set(settings.get("mouse_button", "Left"))
        self.click_type_var.set(settings.get("click_type", "Single"))

        self.repeat_mode_var.set(settings.get("repeat_mode", "Infinite"))
        self.repeat_count_var.set(str(settings.get("click_count", 1000)))

        self.position_mode_var.set(settings.get("position_mode", "Current Position"))
        self.pos_x_var.set(str(settings.get("x", 0)))
        self.pos_y_var.set(str(settings.get("y", 0)))

        mode = settings.get("appearance_mode", "Light")
        if mode not in ["Light", "Dark"]:
            mode = "Light"

        self.theme_mode_var.set(mode)
        self.apply_theme_mode(mode)

        self.toggle_repeat_entry()
        self.toggle_position_entries()

    def on_profile_selected(self, selected_profile: str):
        profiles, active = self.profile_manager.set_active_profile(selected_profile)
        self.apply_profile_settings(profiles.get(active, {}))
        self.show_error(f"Loaded Profile: {active}")

    def prompt_save_new_profile(self):
        settings = self.validate_inputs()
        if not settings:
            return

        dialog = ctk.CTkInputDialog(
            text="Enter a name for the profile:",
            title="Save Profile"
        )
        profile_name = dialog.get_input()

        if profile_name is None:
            return

        profile_name = profile_name.strip()
        if not profile_name:
            self.show_error("Profile name cannot be empty.")
            return

        saved_dict = {
            "hours": settings["hours"],
            "minutes": settings["minutes"],
            "seconds": settings["seconds"],
            "milliseconds": settings["milliseconds"],
            "mouse_button": settings["mouse_button"],
            "click_type": settings["click_type"],
            "repeat_mode": settings["repeat_mode"],
            "click_count": settings["repeat_count"],
            "position_mode": settings["position_mode"],
            "x": settings["x"],
            "y": settings["y"],
            "appearance_mode": self.theme_mode_var.get()
        }
        profiles, active = self.profile_manager.save_profile(profile_name, saved_dict)
        self.refresh_profiles_ui()
        self.show_error(f"Saved new profile: '{profile_name}'")
        logging.info(f"Saved new custom profile: {profile_name}")

    def prompt_delete_profile(self):
        profiles, active = self.profile_manager.load_profiles()
        deletable_profiles = [name for name in profiles.keys() if name != "Default"]

        if not deletable_profiles:
            self.show_error("No custom profiles available to delete (Default cannot be deleted).")
            return

        DeleteProfileDialog(self, deletable_profiles, self.execute_profile_deletion)

    def execute_profile_deletion(self, target_profile_name: str):
        profiles, new_active, success = self.profile_manager.delete_profile(target_profile_name)
        if success:
            self.refresh_profiles_ui()
            self.show_error(f"Deleted profile '{target_profile_name}'. Active: {new_active}")
            logging.info(f"Deleted profile: {target_profile_name}")
        else:
            self.show_error("Cannot delete Default profile.")

    def save_current_settings(self):
        active = self.active_profile_var.get()
        settings = self.validate_inputs()
        if settings:
            saved_dict = {
                "hours": settings["hours"],
                "minutes": settings["minutes"],
                "seconds": settings["seconds"],
                "milliseconds": settings["milliseconds"],
                "mouse_button": settings["mouse_button"],
                "click_type": settings["click_type"],
                "repeat_mode": settings["repeat_mode"],
                "click_count": settings["repeat_count"],
                "position_mode": settings["position_mode"],
                "x": settings["x"],
                "y": settings["y"],
                "appearance_mode": self.theme_mode_var.get()
            }
            self.profile_manager.save_profile(active, saved_dict)
            self.show_error(f"Saved configuration to profile '{active}'")

    def reset_default_settings(self):
        self.settings_manager.reset_defaults()
        self.refresh_profiles_ui()
        self.show_error("Settings reset to defaults.")

    def toggle_repeat_entry(self):
        if self.repeat_mode_var.get() == "Count":
            self.repeat_count_entry.configure(state="normal")
        else:
            self.repeat_count_entry.configure(state="disabled")

    def toggle_position_entries(self):
        mode = self.position_mode_var.get()
        if mode == "Fixed Position":
            self.x_entry.configure(state="normal")
            self.y_entry.configure(state="normal")
            self.capture_btn.configure(state="normal")
            self.add_pos_btn.configure(state="disabled")
            self.clear_pos_btn.configure(state="disabled")
        elif mode == "Recorded Positions":
            self.x_entry.configure(state="disabled")
            self.y_entry.configure(state="disabled")
            self.capture_btn.configure(state="disabled")
            self.add_pos_btn.configure(state="normal")
            self.clear_pos_btn.configure(state="normal")
        else:
            self.x_entry.configure(state="disabled")
            self.y_entry.configure(state="disabled")
            self.capture_btn.configure(state="disabled")
            self.add_pos_btn.configure(state="disabled")
            self.clear_pos_btn.configure(state="disabled")

    def show_error(self, message: str):
        self.error_banner.configure(text=message)

    def clear_error(self):
        self.error_banner.configure(text="")

    def validate_inputs(self):
        self.clear_error()
        try:
            h = int(self.hours_var.get() or "0")
            m = int(self.minutes_var.get() or "0")
            s = int(self.seconds_var.get() or "0")
            ms = int(self.milliseconds_var.get() or "0")
        except ValueError:
            self.show_error("Interval fields must be integers.")
            logging.warning("Input validation failed: Non-integer interval")
            return None

        if h < 0:
            self.show_error("Hours cannot be negative.")
            return None
        if not (0 <= m <= 59):
            self.show_error("Minutes must be between 0 and 59.")
            return None
        if not (0 <= s <= 59):
            self.show_error("Seconds must be between 0 and 59.")
            return None
        if not (0 <= ms <= 999):
            self.show_error("Milliseconds must be between 0 and 999.")
            return None

        total_seconds = h * 3600 + m * 60 + s + (ms / 1000.0)
        if total_seconds <= 0:
            self.show_error("Click interval must be greater than 0.")
            logging.warning("Input validation failed: Interval is 0")
            return None

        repeat_count = 0
        if self.repeat_mode_var.get() == "Count":
            try:
                repeat_count = int(self.repeat_count_var.get())
                if repeat_count <= 0:
                    self.show_error("Click count must be a positive integer.")
                    return None
            except ValueError:
                self.show_error("Click count must be a valid integer.")
                return None

        x_pos, y_pos = 0, 0
        if self.position_mode_var.get() == "Fixed Position":
            try:
                x_pos = int(self.pos_x_var.get())
                y_pos = int(self.pos_y_var.get())
                if x_pos < 0 or y_pos < 0:
                    self.show_error("Coordinates X and Y must be >= 0.")
                    return None
            except ValueError:
                self.show_error("Coordinates X and Y must be valid integers.")
                return None

        recorded_positions = self.position_recorder.get_positions()
        if self.position_mode_var.get() == "Recorded Positions" and not recorded_positions:
            self.show_error("Please record at least 1 position before starting sequence.")
            return None

        return {
            "hours": h,
            "minutes": m,
            "seconds": s,
            "milliseconds": ms,
            "total_seconds": total_seconds,
            "mouse_button": self.mouse_button_var.get(),
            "click_type": self.click_type_var.get(),
            "repeat_mode": self.repeat_mode_var.get(),
            "repeat_count": repeat_count,
            "position_mode": self.position_mode_var.get(),
            "x": x_pos,
            "y": y_pos,
            "recorded_positions": recorded_positions
        }

    def capture_position_clicked(self):
        x, y = self.click_engine.get_current_position()
        self.pos_x_var.set(str(x))
        self.pos_y_var.set(str(y))
        self.clear_error()
        logging.info(f"Captured coordinate X={x}, Y={y}")

    def add_current_pos_to_recorder(self):
        x, y = self.click_engine.get_current_position()
        self.position_recorder.add_position(x, y)
        cnt = self.position_recorder.count()
        self.recorded_seq_label_var.set(f"Recorded: {cnt} points")
        self.show_error(f"Added Position #{cnt}: X={x}, Y={y}")

    def clear_recorded_positions(self):
        self.position_recorder.clear_positions()
        self.recorded_seq_label_var.set("Recorded: 0 points")
        self.show_error("Cleared recorded positions sequence.")

    def start_clicking(self):
        self.restore_from_tray()
        settings = self.validate_inputs()
        if settings is None:
            return

        self.save_current_settings()

        self.click_count = 0
        self.update_click_counter(0, 0.0)

        logging.info(f"Clicking started with interval {settings['total_seconds']}s, button={settings['mouse_button']}, type={settings['click_type']}, mode={settings['position_mode']}")

        # Instantiate thread worker
        self.worker = ClickWorker(
            settings=settings,
            click_engine=self.click_engine,
            on_click_callback=lambda count, cps: self.after(0, self.update_click_counter, count, cps),
            on_complete_callback=lambda: self.after(0, self.on_clicking_completed),
            on_error_callback=lambda err: self.after(0, self.on_clicking_error, err)
        )
        self.worker.start()

        self.status = "RUNNING"
        self.status_badge.configure(text="Status: RUNNING", text_color="#10B981")
        self.start_stop_btn.configure(text="STOP", fg_color="#E11D48", hover_color="#BE123C")

    def stop_clicking(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self.worker = None
            logging.info(f"Clicking stopped after {self.click_count} clicks")

        self.status = "STOPPED"
        self.status_badge.configure(text="Status: STOPPED", text_color="#E11D48")
        self.start_stop_btn.configure(text="START", fg_color="#10B981", hover_color="#059669")
        self.cps_label.configure(text="Speed: 0.0 CPS")

    def emergency_stop(self):
        logging.warning("EMERGENCY STOP (F7) triggered!")
        self.stop_clicking()
        self.restore_from_tray()
        self.show_error("EMERGENCY STOP TRIGGERED (F7)")

    def toggle_start_stop(self):
        if self.status == "RUNNING":
            self.stop_clicking()
        else:
            self.start_clicking()

    def on_clicking_completed(self):
        logging.info(f"Clicking completed target total of {self.click_count} clicks")
        self.status = "COMPLETED"
        self.status_badge.configure(text="Status: COMPLETED", text_color="#0284C7")
        self.start_stop_btn.configure(text="START", fg_color="#10B981", hover_color="#059669")
        self.cps_label.configure(text="Speed: 0.0 CPS")
        self.worker = None

    def on_clicking_error(self, err_msg: str):
        logging.error(f"Click engine error: {err_msg}")
        self.status = "ERROR"
        self.status_badge.configure(text="Status: ERROR", text_color="#E11D48")
        self.show_error(f"Click engine error: {err_msg}")
        self.stop_clicking()

    def update_click_counter(self, count: int, cps: float = 0.0):
        self.click_count = count
        self.counter_label.configure(text=f"Clicks: {count}")
        self.cps_label.configure(text=f"Speed: {cps:.1f} CPS")

    def exit_app(self):
        logging.info("Application exiting cleanly")
        self.save_current_settings()
        self.stop_clicking()
        self.hotkey_manager.stop()
        self.tray_manager.stop()
        self.destroy()

    def on_closing(self):
        self.minimize_to_tray()


if __name__ == "__main__":
    is_single_instance, mutex_handle = check_single_instance()
    if not is_single_instance and "--test-startup" not in sys.argv:
        sys.exit(0)

    app = AutoClickerGUI()
    if "--test-startup" in sys.argv:
        app.after(500, app.destroy)
    app.mainloop()
