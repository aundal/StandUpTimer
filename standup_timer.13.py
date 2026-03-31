import sys
import random
import os
import math
import time
import json
import re
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, 
                             QHBoxLayout, QSpinBox, QDoubleSpinBox, QLineEdit, 
                             QPushButton, QFileDialog, QMenu, QFormLayout, QCheckBox, QTimeEdit, QLabel, QComboBox,
                             QInputDialog, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRect, QRectF, QSettings, QTime
from PyQt6.QtGui import (QPainter, QColor, QPen, QPixmap, QPainterPath, 
                         QFont, QAction, QFontMetrics, QConicalGradient, QImage, QIcon)

# Global Font Preference
UI_FONT = "Segoe UI"
MAX_TICK_DELTA_SECONDS = 1.0
TIMER_MODE_COUNTDOWN = "countdown"
TIMER_MODE_COUNTUP = "countup"
APP_USER_MODEL_ID = "MyCompany.StandUpTimer"

def get_base_path():
    """ Get the absolute path to the directory of the running process. """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def set_windows_app_user_model_id(app_id):
    if os.name != "nt":
        return
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(app_id))

def load_application_icon():
    base_path = get_base_path()
    candidate_paths = [os.path.join(base_path, "ikon.ico")]
    if getattr(sys, "frozen", False):
        candidate_paths.append(sys.executable)
    for candidate in candidate_paths:
        if not candidate or not os.path.exists(candidate):
            continue
        icon = QIcon(candidate)
        if not icon.isNull():
            return icon
    return QIcon()

def parse_name_from_filename(filename):
    base_name = os.path.basename(filename)
    stem, ext = os.path.splitext(base_name)
    if not ext and "." in base_name:
        stem = base_name.rsplit(".", 1)[0]
    parts = [p for p in re.split(r"[_.\-\s]+", stem) if p]
    if not parts:
        return "Unknown", "Unknown"
    formatted_parts = [part[:1].upper() + part[1:].lower() for part in parts]
    full_name = " ".join(formatted_parts)
    return full_name, formatted_parts[0]

def default_profile_name_from_dir(directory, index=None):
    base_name = os.path.basename(os.path.normpath(str(directory).strip()))
    if base_name:
        return base_name
    if index is not None:
        return f"Profile {index + 1}"
    return "Profile"

def profile_folder_name(directory):
    base_name = os.path.basename(os.path.normpath(str(directory).strip()))
    return base_name or "No folder"

def format_profile_display_label(profile, index):
    safe_profile = sanitize_profile(profile, fallback_index=index)
    folder_name = profile_folder_name(safe_profile["image_dir"])
    return f"{index + 1}. {safe_profile['name']} ({folder_name})"

def normalize_profile_id(profile_id):
    if isinstance(profile_id, str):
        cleaned = profile_id.strip()
        if cleaned:
            return cleaned
    return None

def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def normalize_int(value, default_value, min_value, max_value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default_value
    return max(min_value, min(max_value, parsed))

def sanitize_profile(
    profile,
    fallback_dir="",
    fallback_auto_start_enabled=False,
    fallback_auto_start_time="09:00",
    fallback_index=None,
):
    if not isinstance(profile, dict):
        profile = {}
    image_dir = str(profile.get("image_dir", fallback_dir) or fallback_dir)
    auto_start_enabled = coerce_bool(profile.get("auto_start_enabled", fallback_auto_start_enabled))
    auto_start_time = normalize_hhmm(profile.get("auto_start_time", fallback_auto_start_time))
    name = str(profile.get("name", "") or "").strip()
    if not name:
        name = default_profile_name_from_dir(image_dir, fallback_index)
    profile_id = normalize_profile_id(profile.get("profile_id"))
    return {
        "profile_id": profile_id,
        "name": name,
        "image_dir": image_dir,
        "auto_start_enabled": auto_start_enabled,
        "auto_start_time": auto_start_time,
    }

def ensure_profiles_have_ids(profiles):
    if not isinstance(profiles, list):
        return []
    used_ids = set()
    next_counter = 1
    normalized_profiles = []
    for idx, profile in enumerate(profiles):
        profile_copy = sanitize_profile(profile, fallback_index=idx)
        profile_id = normalize_profile_id(profile_copy.get("profile_id"))
        if profile_id in used_ids:
            profile_id = None
        if profile_id is None:
            while f"profile-{next_counter}" in used_ids:
                next_counter += 1
            profile_id = f"profile-{next_counter}"
            next_counter += 1
        profile_copy["profile_id"] = profile_id
        used_ids.add(profile_id)
        normalized_profiles.append(profile_copy)
    return normalized_profiles

def load_profiles(raw_value, fallback_dir, fallback_auto_start_enabled=False, fallback_auto_start_time="09:00"):
    if isinstance(raw_value, list):
        raw_profiles = raw_value
    elif isinstance(raw_value, dict):
        raw_profiles = [raw_value]
    else:
        try:
            loaded = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            loaded = []
        if isinstance(loaded, list):
            raw_profiles = loaded
        elif isinstance(loaded, dict):
            raw_profiles = [loaded]
        else:
            raw_profiles = []

    profiles = []
    for idx, profile in enumerate(raw_profiles):
        profiles.append(
            sanitize_profile(
                profile,
                fallback_dir=fallback_dir,
                fallback_auto_start_enabled=fallback_auto_start_enabled,
                fallback_auto_start_time=fallback_auto_start_time,
                fallback_index=idx,
            )
        )

    if not profiles:
        profiles = [
            sanitize_profile(
                {
                    "name": default_profile_name_from_dir(fallback_dir, 0),
                    "image_dir": fallback_dir,
                    "auto_start_enabled": fallback_auto_start_enabled,
                    "auto_start_time": fallback_auto_start_time,
                },
                fallback_dir=fallback_dir,
                fallback_auto_start_enabled=fallback_auto_start_enabled,
                fallback_auto_start_time=fallback_auto_start_time,
                fallback_index=0,
            )
        ]
    return ensure_profiles_have_ids(profiles)

def remove_profile_by_index(profiles, index):
    if not isinstance(profiles, list):
        return [], 0
    sanitized_profiles = [
        sanitize_profile(profile, fallback_dir="", fallback_index=i)
        for i, profile in enumerate(profiles)
    ]
    if len(sanitized_profiles) <= 1:
        return sanitized_profiles, 0
    safe_index = normalize_int(index, default_value=0, min_value=0, max_value=len(sanitized_profiles) - 1)
    sanitized_profiles.pop(safe_index)
    next_index = safe_index
    if next_index >= len(sanitized_profiles):
        next_index = len(sanitized_profiles) - 1
    return ensure_profiles_have_ids(sanitized_profiles), max(0, next_index)

def load_person_totals(raw_value):
    if isinstance(raw_value, dict):
        data = raw_value
    elif raw_value is None:
        data = {}
    else:
        try:
            data = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            data = {}
    if not isinstance(data, dict):
        return {}
    normalized = {}
    for name, seconds in data.items():
        if not isinstance(name, str) or not name.strip():
            continue
        normalized[name.strip()] = normalize_int(seconds, default_value=0, min_value=0, max_value=10**9)
    return normalized

def merge_person_totals(existing_totals, meeting_breakdown):
    merged = load_person_totals(existing_totals)
    for name, seconds in meeting_breakdown:
        if not isinstance(name, str) or not name.strip():
            continue
        safe_seconds = normalize_int(seconds, default_value=0, min_value=0, max_value=10**9)
        if safe_seconds <= 0:
            continue
        merged[name.strip()] = merged.get(name.strip(), 0) + safe_seconds
    return merged

def load_profile_person_totals(raw_value):
    if isinstance(raw_value, dict):
        loaded = raw_value
    else:
        try:
            loaded = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            loaded = {}
    if not isinstance(loaded, dict):
        return {}
    normalized = {}
    for profile_id, totals in loaded.items():
        safe_profile_id = normalize_profile_id(profile_id)
        if safe_profile_id is None:
            continue
        normalized[safe_profile_id] = load_person_totals(totals)
    return normalized

def merge_profile_person_totals(existing_profile_totals, profile_id, meeting_breakdown):
    all_totals = load_profile_person_totals(existing_profile_totals)
    safe_profile_id = normalize_profile_id(profile_id)
    if safe_profile_id is None:
        return all_totals
    current_profile_totals = all_totals.get(safe_profile_id, {})
    all_totals[safe_profile_id] = merge_person_totals(current_profile_totals, meeting_breakdown)
    return all_totals

def reset_profile_person_totals(existing_profile_totals, profile_id):
    all_totals = load_profile_person_totals(existing_profile_totals)
    safe_profile_id = normalize_profile_id(profile_id)
    if safe_profile_id is None:
        return all_totals
    all_totals[safe_profile_id] = {}
    return all_totals

def get_profile_person_totals(existing_profile_totals, profile_id):
    all_totals = load_profile_person_totals(existing_profile_totals)
    safe_profile_id = normalize_profile_id(profile_id)
    if safe_profile_id is None:
        return {}
    return load_person_totals(all_totals.get(safe_profile_id, {}))

def parse_hhmm(value):
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute

def normalize_hhmm(value, default_value="09:00"):
    parsed = parse_hhmm(value)
    if parsed is None:
        parsed = parse_hhmm(default_value)
    if parsed is None:
        parsed = (9, 0)
    return f"{parsed[0]:02d}:{parsed[1]:02d}"

def normalize_timer_mode(mode):
    if mode == TIMER_MODE_COUNTUP:
        return TIMER_MODE_COUNTUP
    return TIMER_MODE_COUNTDOWN

def format_duration_clock(seconds):
    safe_seconds = max(0, int(seconds))
    hours = safe_seconds // 3600
    minutes = (safe_seconds % 3600) // 60
    remaining_seconds = safe_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes}:{remaining_seconds:02d}"

def format_minutes_label(minutes):
    safe_minutes = max(0, int(minutes))
    minute_label = "minute" if safe_minutes == 1 else "minutes"
    return f"{safe_minutes} {minute_label}"

def active_name_rect_for_main_circle(main_circle_rect):
    return QRect(
        main_circle_rect.left(),
        main_circle_rect.top() - 36,
        main_circle_rect.width(),
        28,
    )

def build_finished_delta_message_lines(planned_seconds, actual_seconds):
    safe_planned = max(0, int(planned_seconds))
    safe_actual = max(0, int(actual_seconds))
    delta_seconds = safe_planned - safe_actual
    rounded_minutes = abs(delta_seconds) // 60
    if abs(delta_seconds) % 60 >= 30:
        rounded_minutes += 1
    if abs(delta_seconds) > 0 and rounded_minutes == 0:
        rounded_minutes = 1

    gained_minutes = rounded_minutes if delta_seconds >= 0 else 0
    lost_minutes = rounded_minutes if delta_seconds < 0 else 0
    first_line_segments = [
        ("You just got ", False),
        (format_minutes_label(gained_minutes), True),
        (" for free,", False),
    ]
    second_line_segments = [
        ("or you just lost ", False),
        (format_minutes_label(lost_minutes), True),
        (".", False),
    ]
    return first_line_segments, second_line_segments

def format_timer_value(seconds, timer_mode):
    mode = normalize_timer_mode(timer_mode)
    if mode == TIMER_MODE_COUNTUP:
        safe_seconds = max(0, int(seconds))
        return f"{safe_seconds // 60}:{safe_seconds % 60:02d}"
    sign = "-" if seconds < 0 else ""
    absolute = abs(int(seconds))
    return f"{sign}{absolute // 60}:{absolute % 60:02d}"

def seconds_until_next_auto_start(auto_start_enabled, auto_start_time_hhmm, now_dt, last_auto_start_date=None):
    if not auto_start_enabled:
        return None
    parsed_time = parse_hhmm(auto_start_time_hhmm)
    if parsed_time is None:
        return None
    target_time = now_dt.replace(hour=parsed_time[0], minute=parsed_time[1], second=0, microsecond=0)
    if last_auto_start_date == now_dt.date() or now_dt > target_time:
        target_time = target_time + timedelta(days=1)
    seconds_until = int((target_time - now_dt).total_seconds())
    if seconds_until > 24 * 3600:
        seconds_until -= 24 * 3600
    return max(0, seconds_until)

def should_auto_start_now(auto_start_enabled, auto_start_time_hhmm, now_dt, last_auto_start_date, running, finished):
    if not auto_start_enabled or running:
        return False
    if last_auto_start_date == now_dt.date():
        return False
    parsed_time = parse_hhmm(auto_start_time_hhmm)
    if parsed_time is None:
        return False
    return (now_dt.hour, now_dt.minute) == parsed_time

def should_skip_today_autostart_on_launch(auto_start_enabled, auto_start_time_hhmm, now_dt):
    if not auto_start_enabled:
        return False
    parsed_time = parse_hhmm(auto_start_time_hhmm)
    if parsed_time is None:
        return False
    return (now_dt.hour, now_dt.minute) >= parsed_time

def should_evaluate_autostart(last_observed_minute, now_dt):
    current_minute = now_dt.replace(second=0, microsecond=0)
    if last_observed_minute is None:
        return False, current_minute
    if current_minute != last_observed_minute:
        return True, current_minute
    return False, current_minute

def get_active_indices(colleagues):
    """Return indices for colleagues not marked as removed."""
    return [i for i, person in enumerate(colleagues) if not person.get("removed", False)]

def compute_avg_time_limit(total_seconds, active_count):
    """Compute per-person time limit for active participants."""
    if active_count <= 0:
        return total_seconds
    return total_seconds // active_count

def get_next_active_index(active_indices, current_index):
    """Return the next active index greater than current_index."""
    for idx in active_indices:
        if idx > current_index:
            return idx
    return None

def get_next_pending_index(active_indices, spoken_indices, current_index):
    """Return the first active colleague who has not spoken yet and is not current."""
    spoken_set = set(spoken_indices)
    for idx in active_indices:
        if idx != current_index and idx not in spoken_set:
            return idx
    return None

def get_queue_layout(colleagues, spoken_indices, current_index):
    """Compute indices for next-up, upcoming, spoken, and removed groups."""
    active_indices = get_active_indices(colleagues)
    spoken_set = set(spoken_indices)
    next_up_index = get_next_pending_index(active_indices, spoken_set, current_index)
    spoken_indices = [i for i in active_indices if i in spoken_set and i != current_index]
    upcoming_indices = [
        i for i in active_indices if i not in spoken_set and i != current_index and i != next_up_index
    ]
    removed_indices = [i for i, person in enumerate(colleagues) if person.get("removed", False)]
    return next_up_index, upcoming_indices, spoken_indices, removed_indices

def compute_orbit_angle(offset, angle_step, large_gap, anchor_angle=45):
    """Compute orbit angle for an offset from the fixed NEXT UP position."""
    if offset > 0:
        return anchor_angle - (large_gap + (offset - 1) * angle_step)
    if offset < 0:
        return anchor_angle + (large_gap + (abs(offset) - 1) * angle_step)
    return anchor_angle

def accumulate_elapsed_seconds(carry_seconds, delta_seconds, max_delta_seconds=None):
    """Convert elapsed delta and carry into whole seconds plus remaining fraction."""
    if carry_seconds < 0:
        carry_seconds = 0.0
    if delta_seconds < 0:
        delta_seconds = 0.0
    if max_delta_seconds is not None:
        if max_delta_seconds < 0:
            max_delta_seconds = 0.0
        delta_seconds = min(delta_seconds, max_delta_seconds)
    combined = carry_seconds + delta_seconds
    whole_seconds = int(combined)
    return whole_seconds, combined - whole_seconds

class SettingsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        current_time=600,
        current_dir="",
        current_scale=1.0,
        current_auto_start_enabled=False,
        current_auto_start_time="09:00",
        current_show_first_name=False,
        current_name_size_percent=10,
        current_name_position_percent=80,
        profiles=None,
        current_profile_index=0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Timer Settings")
        self.setModal(True)
        self.resize(420, 400)

        self.profiles = ensure_profiles_have_ids([
            sanitize_profile(profile, fallback_dir=current_dir, fallback_index=i)
            for i, profile in enumerate(profiles or [])
        ])
        if not self.profiles:
            self.profiles = ensure_profiles_have_ids([
                sanitize_profile({"image_dir": current_dir}, fallback_dir=current_dir, fallback_index=0)
            ])
        self.current_profile_index = normalize_int(
            current_profile_index, default_value=0, min_value=0, max_value=max(0, len(self.profiles) - 1)
        )

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.profile_combo = QComboBox()
        self.refresh_profile_combo_items()
        self.profile_combo.setCurrentIndex(self.current_profile_index)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        form_layout.addRow("Profiles:", self.profile_combo)

        self.add_profile_btn = QPushButton("Add profile")
        self.add_profile_btn.clicked.connect(self.add_profile_with_prompt)
        self.delete_profile_btn = QPushButton("Remove profile")
        self.delete_profile_btn.clicked.connect(self.delete_current_profile)
        profiles_button_layout = QHBoxLayout()
        profiles_button_layout.addWidget(self.add_profile_btn)
        profiles_button_layout.addWidget(self.delete_profile_btn)
        form_layout.addRow("", profiles_button_layout)

        self.profiles_separator = QFrame()
        self.profiles_separator.setFrameShape(QFrame.Shape.HLine)
        self.profiles_separator.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", self.profiles_separator)

        self.time_spinbox = QSpinBox()
        self.time_spinbox.setRange(10, 7200) 
        self.time_spinbox.setValue(current_time)
        self.time_spinbox.setSuffix(" seconds")
        form_layout.addRow("Total Standup Time:", self.time_spinbox)

        self.scale_spinbox = QDoubleSpinBox()
        self.scale_spinbox.setRange(0.5, 3.0)
        self.scale_spinbox.setSingleStep(0.1)
        self.scale_spinbox.setValue(current_scale)
        form_layout.addRow("UI Scale:", self.scale_spinbox)

        self.ui_scale_separator = QFrame()
        self.ui_scale_separator.setFrameShape(QFrame.Shape.HLine)
        self.ui_scale_separator.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", self.ui_scale_separator)

        self.auto_start_checkbox = QCheckBox()
        self.auto_start_checkbox.setChecked(coerce_bool(current_auto_start_enabled))
        form_layout.addRow("Enable Start at:", self.auto_start_checkbox)

        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        initial_time = QTime.fromString(normalize_hhmm(current_auto_start_time), "HH:mm")
        if not initial_time.isValid():
            initial_time = QTime(9, 0)
        self.start_time_edit.setTime(initial_time)
        self.start_time_edit.setEnabled(self.auto_start_checkbox.isChecked())
        self.auto_start_checkbox.toggled.connect(self.start_time_edit.setEnabled)
        form_layout.addRow("Start at:", self.start_time_edit)

        self.start_at_separator = QFrame()
        self.start_at_separator.setFrameShape(QFrame.Shape.HLine)
        self.start_at_separator.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", self.start_at_separator)

        self.show_first_name_checkbox = QCheckBox()
        self.show_first_name_checkbox.setChecked(coerce_bool(current_show_first_name))
        form_layout.addRow("Show first name on non-speakers:", self.show_first_name_checkbox)

        self.name_size_spinbox = QSpinBox()
        self.name_size_spinbox.setRange(8, 60)
        self.name_size_spinbox.setSuffix(" %")
        self.name_size_spinbox.setValue(
            normalize_int(current_name_size_percent, default_value=10, min_value=8, max_value=60)
        )
        form_layout.addRow("Name size:", self.name_size_spinbox)

        self.name_position_spinbox = QSpinBox()
        self.name_position_spinbox.setRange(0, 100)
        self.name_position_spinbox.setSuffix(" %")
        self.name_position_spinbox.setValue(
            normalize_int(current_name_position_percent, default_value=80, min_value=0, max_value=100)
        )
        form_layout.addRow("Name position from top:", self.name_position_spinbox)

        self.name_size_spinbox.setEnabled(self.show_first_name_checkbox.isChecked())
        self.name_position_spinbox.setEnabled(self.show_first_name_checkbox.isChecked())
        self.show_first_name_checkbox.toggled.connect(self.name_size_spinbox.setEnabled)
        self.show_first_name_checkbox.toggled.connect(self.name_position_spinbox.setEnabled)
        self.update_delete_button_state()

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.on_profile_changed(self.current_profile_index)

    def refresh_profile_combo_items(self):
        labels = [format_profile_display_label(profile, idx) for idx, profile in enumerate(self.profiles)]
        self.profile_combo.clear()
        self.profile_combo.addItems(labels)

    def store_current_profile_inputs(self):
        if not (0 <= self.current_profile_index < len(self.profiles)):
            return
        self.profiles[self.current_profile_index]["auto_start_enabled"] = self.auto_start_checkbox.isChecked()
        self.profiles[self.current_profile_index]["auto_start_time"] = self.start_time_edit.time().toString("HH:mm")

    def on_profile_changed(self, index):
        self.store_current_profile_inputs()
        if not (0 <= index < len(self.profiles)):
            return
        self.current_profile_index = index
        profile = self.profiles[index]
        self.auto_start_checkbox.setChecked(profile["auto_start_enabled"])
        profile_time = QTime.fromString(profile["auto_start_time"], "HH:mm")
        if not profile_time.isValid():
            profile_time = QTime(9, 0)
        self.start_time_edit.setTime(profile_time)

    def add_profile_with_prompt(self):
        self.store_current_profile_inputs()
        suggested_name = f"Profile {len(self.profiles) + 1}"
        profile_name, ok = QInputDialog.getText(self, "Add profile", "Profile name:", text=suggested_name)
        if not ok:
            return
        profile_name = profile_name.strip()
        if not profile_name:
            profile_name = suggested_name
        start_dir = ""
        if 0 <= self.current_profile_index < len(self.profiles):
            start_dir = self.profiles[self.current_profile_index]["image_dir"]
        directory = QFileDialog.getExistingDirectory(self, "Select Profile Folder", start_dir)
        if not directory:
            return
        new_index = len(self.profiles)
        profile = sanitize_profile(
            {"image_dir": directory, "name": profile_name},
            fallback_dir=directory,
            fallback_auto_start_enabled=False,
            fallback_auto_start_time="09:00",
            fallback_index=new_index,
        )
        self.profiles.append(profile)
        self.refresh_profile_combo_items()
        self.profile_combo.setCurrentIndex(new_index)
        self.update_delete_button_state()

    def update_delete_button_state(self):
        self.delete_profile_btn.setEnabled(len(self.profiles) > 1)

    def delete_current_profile(self):
        updated_profiles, next_index = remove_profile_by_index(self.profiles, self.current_profile_index)
        if len(updated_profiles) <= 1 and len(self.profiles) <= 1:
            self.update_delete_button_state()
            return
        if updated_profiles == self.profiles:
            self.update_delete_button_state()
            return
        self.profiles = updated_profiles
        self.refresh_profile_combo_items()
        self.current_profile_index = next_index
        self.profile_combo.setCurrentIndex(self.current_profile_index)
        self.on_profile_changed(self.current_profile_index)
        self.update_delete_button_state()

    def get_settings(self):
        self.store_current_profile_inputs()

        sanitized_profiles = ensure_profiles_have_ids([
            sanitize_profile(
                profile,
                fallback_dir=profile.get("image_dir", ""),
                fallback_auto_start_enabled=False,
                fallback_auto_start_time="09:00",
                fallback_index=i,
            )
            for i, profile in enumerate(self.profiles)
        ])

        return {
            "time_limit": self.time_spinbox.value(),
            "ui_scale": self.scale_spinbox.value(),
            "image_dir": sanitized_profiles[self.current_profile_index]["image_dir"],
            "auto_start_enabled": sanitized_profiles[self.current_profile_index]["auto_start_enabled"],
            "auto_start_time": sanitized_profiles[self.current_profile_index]["auto_start_time"],
            "show_first_name_overlay": self.show_first_name_checkbox.isChecked(),
            "name_overlay_size_percent": self.name_size_spinbox.value(),
            "name_overlay_position_percent": self.name_position_spinbox.value(),
            "profiles": sanitized_profiles,
            "active_profile_index": self.current_profile_index,
        }


class StatisticsDialog(QDialog):
    def __init__(self, parent=None, profile_name="Profile", person_totals=None, on_reset=None):
        super().__init__(parent)
        self.setWindowTitle("Statistics")
        self.setModal(True)
        self.resize(380, 460)
        self.profile_name = str(profile_name or "Profile")
        self.on_reset = on_reset
        self.person_totals = load_person_totals(person_totals)

        layout = QVBoxLayout(self)

        title_label = QLabel(f"Cumulative time per person ({self.profile_name})")
        title_label.setFont(QFont(UI_FONT, 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        self.content_label = QLabel("")
        self.content_label.setFont(QFont(UI_FONT, 10))
        self.content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.content_label, 1)

        button_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset statistics")
        self.reset_btn.clicked.connect(self.reset_statistics)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.refresh_content()

    def refresh_content(self):
        totals = load_person_totals(self.person_totals)
        if not totals:
            stats_text = "No statistics yet."
        else:
            sorted_totals = sorted(totals.items(), key=lambda item: (-item[1], item[0].lower()))
            lines = [f"{name}: {format_duration_clock(seconds)}" for name, seconds in sorted_totals]
            total_seconds = sum(seconds for _, seconds in sorted_totals)
            lines.append("")
            lines.append(f"Total tracked time: {format_duration_clock(total_seconds)}")
            stats_text = "\n".join(lines)
        self.content_label.setText(stats_text)
        self.reset_btn.setEnabled(bool(totals) and callable(self.on_reset))

    def reset_statistics(self):
        if not callable(self.on_reset):
            return
        confirmation = QMessageBox.question(
            self,
            "Reset statistics",
            f"Reset all statistics for '{self.profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return
        self.person_totals = load_person_totals(self.on_reset())
        self.refresh_content()


class StandupTimer(QWidget):
    def __init__(self):
        super().__init__()

        self.settings = QSettings("MyCompany", "StandupTimer")
        self.base_time_limit = int(self.settings.value("time_limit", 600)) 
        self.ui_scale = float(self.settings.value("ui_scale", 1.0))
        
        default_img_dir = os.path.join(get_base_path(), "colleagues")
        self.image_dir = self.settings.value("image_dir", default_img_dir)
        self.count_mode = normalize_timer_mode(self.settings.value("count_mode", TIMER_MODE_COUNTDOWN))
        self.auto_start_enabled = coerce_bool(self.settings.value("auto_start_enabled", False))
        self.auto_start_time = normalize_hhmm(self.settings.value("auto_start_time", "09:00"))
        self.profiles = load_profiles(
            self.settings.value("profiles", "[]"),
            fallback_dir=self.image_dir,
            fallback_auto_start_enabled=self.auto_start_enabled,
            fallback_auto_start_time=self.auto_start_time,
        )
        self.active_profile_index = normalize_int(
            self.settings.value("active_profile_index", 0),
            default_value=0,
            min_value=0,
            max_value=max(0, len(self.profiles) - 1),
        )
        self.apply_active_profile()
        self.show_first_name_overlay = coerce_bool(self.settings.value("show_first_name_overlay", False))
        self.name_overlay_size_percent = normalize_int(
            self.settings.value("name_overlay_size_percent", 10), default_value=10, min_value=8, max_value=60
        )
        self.name_overlay_position_percent = normalize_int(
            self.settings.value("name_overlay_position_percent", 80), default_value=80, min_value=0, max_value=100
        )
        self.last_auto_start_date = None
        self.last_observed_minute = None
        self.initialize_auto_start_state()
        self.cumulative_person_totals_by_profile = load_profile_person_totals(
            self.settings.value("person_totals_by_profile", "{}")
        )
        legacy_totals = load_person_totals(self.settings.value("person_totals", "{}"))
        if legacy_totals:
            active_profile_id = self.get_active_profile_id()
            if active_profile_id is not None:
                self.cumulative_person_totals_by_profile = merge_profile_person_totals(
                    self.cumulative_person_totals_by_profile,
                    active_profile_id,
                    list(legacy_totals.items()),
                )
                self.settings.setValue(
                    "person_totals_by_profile",
                    json.dumps(self.cumulative_person_totals_by_profile, sort_keys=True),
                )
            self.settings.remove("person_totals")
        self.meeting_stats_recorded = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        app_icon = load_application_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(app_icon)
        
        self.base_size = 540
        self.resize(int(self.base_size * self.ui_scale), int(self.base_size * self.ui_scale))

        # State
        self.person_seconds_list =[] 
        self.total_seconds = 0
        self.render_ticks = 0 
        self.run_ticks = 0    
        self.elapsed_carry_seconds = 0.0
        self.last_tick_perf = time.perf_counter()
        self.running = False
        self.finished = False
        
        # Decoupled State Logic
        self.current_index = -1  
        self.spoken_indices = set()
        
        self.colleagues =[]
        self.current_time_limit = self.base_time_limit
        self.avg_time_limit = 0
        self.person_time_limits = []
        self.face_hitboxes = {}
        
        self.load_colleagues()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)

        self.oldPos = self.pos()
        self.drag_start_pos = QPoint()

    def create_circular_pixmap(self, pixmap, size):
        """Hardware optimization: Pre-cuts images into transparent circles to eliminate render lag."""
        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x_offset = (size - scaled.width()) // 2
        y_offset = (size - scaled.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled)
        
        painter.end()
        return target

    def save_profiles(self):
        self.profiles = ensure_profiles_have_ids(self.profiles)
        self.active_profile_index = normalize_int(
            self.active_profile_index,
            default_value=0,
            min_value=0,
            max_value=max(0, len(self.profiles) - 1),
        )
        self.settings.setValue("profiles", json.dumps(self.profiles, sort_keys=True))
        self.settings.setValue("active_profile_index", self.active_profile_index)

    def apply_active_profile(self):
        if not self.profiles:
            return
        self.profiles = ensure_profiles_have_ids(self.profiles)
        self.active_profile_index = normalize_int(
            self.active_profile_index,
            default_value=0,
            min_value=0,
            max_value=max(0, len(self.profiles) - 1),
        )
        profile = sanitize_profile(
            self.profiles[self.active_profile_index],
            fallback_dir=self.image_dir,
            fallback_auto_start_enabled=self.auto_start_enabled,
            fallback_auto_start_time=self.auto_start_time,
            fallback_index=self.active_profile_index,
        )
        self.profiles[self.active_profile_index] = profile
        self.image_dir = profile["image_dir"]
        self.auto_start_enabled = profile["auto_start_enabled"]
        self.auto_start_time = profile["auto_start_time"]

    def get_active_profile_id(self):
        if not self.profiles:
            return None
        self.active_profile_index = normalize_int(
            self.active_profile_index,
            default_value=0,
            min_value=0,
            max_value=max(0, len(self.profiles) - 1),
        )
        return normalize_profile_id(self.profiles[self.active_profile_index].get("profile_id"))

    def get_active_profile_name(self):
        if not self.profiles:
            return "Profile"
        self.active_profile_index = normalize_int(
            self.active_profile_index,
            default_value=0,
            min_value=0,
            max_value=max(0, len(self.profiles) - 1),
        )
        profile = self.profiles[self.active_profile_index]
        profile_name = str(profile.get("name", "") or "").strip()
        if profile_name:
            return profile_name
        return default_profile_name_from_dir(profile.get("image_dir", ""), self.active_profile_index)

    def get_active_profile_totals(self):
        return get_profile_person_totals(
            self.cumulative_person_totals_by_profile,
            self.get_active_profile_id(),
        )

    def reset_active_profile_statistics(self):
        self.cumulative_person_totals_by_profile = reset_profile_person_totals(
            self.cumulative_person_totals_by_profile,
            self.get_active_profile_id(),
        )
        self.settings.setValue(
            "person_totals_by_profile",
            json.dumps(self.cumulative_person_totals_by_profile, sort_keys=True),
        )
        return self.get_active_profile_totals()

    def set_active_profile(self, index):
        if not (0 <= index < len(self.profiles)):
            return
        self.active_profile_index = index
        self.apply_active_profile()
        self.save_profiles()
        self.initialize_auto_start_state()
        self.load_colleagues()

    def load_colleagues(self):
        self.colleagues.clear()
        
        if os.path.exists(self.image_dir):
            for f in os.listdir(self.image_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    name, first_name = parse_name_from_filename(f)
                    path = os.path.join(self.image_dir, f)

                    self.colleagues.append({
                        "name": name, 
                        "first_name": first_name,
                        "path": path, 
                        "has_image": True,
                        "pixmap_cache": {},
                        "raw_pixmap": None,
                        "gray_raw_pixmap": None,
                        "removed": False
                    })
                    
        if not self.colleagues:
            for i in range(5):
                self.colleagues.append({
                    "name": f"Person {chr(65+i)}", 
                    "first_name": f"Person {chr(65+i)}".split()[0],
                    "path": None, 
                    "has_image": False,
                    "removed": False
                })
                
        self.restart_standup(shuffle=True)

    def restart_standup(self, shuffle=True):
        if shuffle:
            random.shuffle(self.colleagues)
            
        self.current_time_limit = self.base_time_limit
        self.person_seconds_list =[0] * len(self.colleagues)
        
        self.recalculate_time_limits()

        self.current_index = -1
        self.spoken_indices = set()
        self.running = False
        self.finished = False
        self.total_seconds = 0
        self.render_ticks = 0
        self.run_ticks = 0
        self.elapsed_carry_seconds = 0.0
        self.last_tick_perf = time.perf_counter()
        self.meeting_stats_recorded = False
        self.face_hitboxes.clear()
        self.update()

    def recalculate_time_limits(self):
        """Recalculate per-person limits using only active participants."""
        active_indices = get_active_indices(self.colleagues)
        active_count = len(active_indices)
        self.avg_time_limit = compute_avg_time_limit(self.current_time_limit, active_count)
        self.person_time_limits = [0] * len(self.colleagues)
        for idx in active_indices:
            self.person_time_limits[idx] = self.avg_time_limit

    def start_timer(self):
        """Start the timer and lock in current average limits."""
        if not self.running:
            self.recalculate_time_limits()
            self.elapsed_carry_seconds = 0.0
            self.last_tick_perf = time.perf_counter()
            self.running = True

    def set_count_mode(self, mode):
        self.count_mode = normalize_timer_mode(mode)
        self.settings.setValue("count_mode", self.count_mode)
        self.update()

    def initialize_auto_start_state(self):
        now_dt = datetime.now()
        self.last_observed_minute = now_dt.replace(second=0, microsecond=0)
        if should_skip_today_autostart_on_launch(self.auto_start_enabled, self.auto_start_time, now_dt):
            self.last_auto_start_date = now_dt.date()
        else:
            self.last_auto_start_date = None

    def maybe_auto_start(self):
        now_dt = datetime.now()
        should_check, self.last_observed_minute = should_evaluate_autostart(self.last_observed_minute, now_dt)
        if not should_check:
            return
        if should_auto_start_now(
            self.auto_start_enabled,
            self.auto_start_time,
            now_dt,
            self.last_auto_start_date,
            self.running,
            self.finished,
        ):
            if self.finished:
                self.restart_standup(shuffle=True)
            self.start_timer()
            self.last_auto_start_date = now_dt.date()

    def get_meeting_person_breakdown(self):
        breakdown = []
        for idx, person in enumerate(self.colleagues):
            if idx >= len(self.person_seconds_list):
                continue
            seconds = normalize_int(self.person_seconds_list[idx], default_value=0, min_value=0, max_value=10**9)
            if seconds <= 0:
                continue
            name = person.get("name", f"Person {idx + 1}")
            breakdown.append((name, seconds))
        breakdown.sort(key=lambda item: (-item[1], item[0].lower()))
        return breakdown

    def persist_meeting_stats(self):
        if self.meeting_stats_recorded:
            return
        meeting_breakdown = self.get_meeting_person_breakdown()
        self.cumulative_person_totals_by_profile = merge_profile_person_totals(
            self.cumulative_person_totals_by_profile,
            self.get_active_profile_id(),
            meeting_breakdown,
        )
        self.settings.setValue(
            "person_totals_by_profile",
            json.dumps(self.cumulative_person_totals_by_profile, sort_keys=True),
        )
        self.meeting_stats_recorded = True

    def finish_meeting(self):
        self.current_index = len(self.colleagues)
        self.finished = True
        self.running = False
        self.persist_meeting_stats()
        self.update()

    def open_statistics(self):
        dialog = StatisticsDialog(
            self,
            profile_name=self.get_active_profile_name(),
            person_totals=self.get_active_profile_totals(),
            on_reset=self.reset_active_profile_statistics,
        )
        dialog.exec()

    def add_time(self, seconds):
        new_total = self.current_time_limit + seconds
        actual_added = seconds
        if new_total < 10:
            actual_added = 10 - self.current_time_limit
            self.current_time_limit = 10
        else:
            self.current_time_limit = new_total
            
        if self.current_index == -1 and not self.running:
            self.recalculate_time_limits()
        else:
            if 0 <= self.current_index < len(self.colleagues):
                self.person_time_limits[self.current_index] += actual_added
                
        self.update()

    def toggle_removed(self, idx):
        """Toggle the removed state for a colleague."""
        if 0 <= idx < len(self.colleagues):
            person = self.colleagues[idx]
            person["removed"] = not person.get("removed", False)
            if not self.running or self.current_index == -1:
                self.recalculate_time_limits()
            self.update()

    def contextMenuEvent(self, event):
        local_pos = event.pos()
        unscaled_pos = QPointF(local_pos.x() / self.ui_scale, local_pos.y() / self.ui_scale)
        face_idx = self.get_face_index_at(unscaled_pos)
        if face_idx is not None:
            self.toggle_removed(face_idx)
            return

        context_menu = QMenu(self)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        context_menu.addAction(settings_action)

        statistics_action = QAction("Statistics", self)
        statistics_action.triggered.connect(self.open_statistics)
        context_menu.addAction(statistics_action)

        profiles_menu = context_menu.addMenu("Profiles")
        for idx, profile in enumerate(self.profiles):
            action = profiles_menu.addAction(format_profile_display_label(profile, idx))
            action.setCheckable(True)
            action.setChecked(idx == self.active_profile_index)
            action.triggered.connect(lambda checked=False, profile_index=idx: self.set_active_profile(profile_index))

        mode_menu = context_menu.addMenu("Mode")
        count_down_action = mode_menu.addAction("Count down")
        count_down_action.setCheckable(True)
        count_down_action.setChecked(self.count_mode == TIMER_MODE_COUNTDOWN)
        count_down_action.triggered.connect(lambda: self.set_count_mode(TIMER_MODE_COUNTDOWN))

        count_up_action = mode_menu.addAction("Count up")
        count_up_action.setCheckable(True)
        count_up_action.setChecked(self.count_mode == TIMER_MODE_COUNTUP)
        count_up_action.triggered.connect(lambda: self.set_count_mode(TIMER_MODE_COUNTUP))
        
        context_menu.addSeparator()
        
        restart_menu = context_menu.addMenu("Restart")
        restart_shuffle_action = restart_menu.addAction("Shuffle")
        restart_shuffle_action.triggered.connect(lambda: self.restart_standup(shuffle=True))
        restart_noshuffle_action = restart_menu.addAction("No Shuffle")
        restart_noshuffle_action.triggered.connect(lambda: self.restart_standup(shuffle=False))
        
        time_menu = context_menu.addMenu("Time")
        add_1m_action = time_menu.addAction("Add 1 minute")
        add_1m_action.triggered.connect(lambda: self.add_time(60))
        add_5m_action = time_menu.addAction("Add 5 minutes")
        add_5m_action.triggered.connect(lambda: self.add_time(300))
        time_menu.addSeparator()
        sub_1m_action = time_menu.addAction("Subtract 1 minute")
        sub_1m_action.triggered.connect(lambda: self.add_time(-60))
        sub_5m_action = time_menu.addAction("Subtract 5 minutes")
        sub_5m_action.triggered.connect(lambda: self.add_time(-300))

        context_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        context_menu.addAction(exit_action)
        
        context_menu.exec(event.globalPos())

    def open_settings(self):
        dialog = SettingsDialog(
            self,
            self.base_time_limit,
            self.image_dir,
            self.ui_scale,
            self.auto_start_enabled,
            self.auto_start_time,
            self.show_first_name_overlay,
            self.name_overlay_size_percent,
            self.name_overlay_position_percent,
            self.profiles,
            self.active_profile_index,
        )
        if dialog.exec():
            new_settings = dialog.get_settings()
            
            self.base_time_limit = new_settings["time_limit"]
            self.ui_scale = new_settings["ui_scale"]
            self.image_dir = new_settings["image_dir"]
            self.auto_start_enabled = coerce_bool(new_settings["auto_start_enabled"])
            self.auto_start_time = normalize_hhmm(new_settings["auto_start_time"])
            self.profiles = load_profiles(
                new_settings.get("profiles", []),
                fallback_dir=self.image_dir,
                fallback_auto_start_enabled=self.auto_start_enabled,
                fallback_auto_start_time=self.auto_start_time,
            )
            self.active_profile_index = normalize_int(
                new_settings.get("active_profile_index", 0),
                default_value=0,
                min_value=0,
                max_value=max(0, len(self.profiles) - 1),
            )
            self.apply_active_profile()
            self.show_first_name_overlay = coerce_bool(new_settings["show_first_name_overlay"])
            self.name_overlay_size_percent = normalize_int(
                new_settings["name_overlay_size_percent"], default_value=10, min_value=8, max_value=60
            )
            self.name_overlay_position_percent = normalize_int(
                new_settings["name_overlay_position_percent"], default_value=80, min_value=0, max_value=100
            )
            
            self.settings.setValue("time_limit", self.base_time_limit)
            self.settings.setValue("ui_scale", self.ui_scale)
            self.settings.setValue("image_dir", self.image_dir)
            self.settings.setValue("auto_start_enabled", self.auto_start_enabled)
            self.settings.setValue("auto_start_time", self.auto_start_time)
            self.save_profiles()
            self.settings.setValue("show_first_name_overlay", self.show_first_name_overlay)
            self.settings.setValue("name_overlay_size_percent", self.name_overlay_size_percent)
            self.settings.setValue("name_overlay_position_percent", self.name_overlay_position_percent)
            self.initialize_auto_start_state()

            self.resize(int(self.base_size * self.ui_scale), int(self.base_size * self.ui_scale))
            self.load_colleagues()

    def get_face_index_at(self, unscaled_pos):
        """Return the face index at the given unscaled position."""
        for idx, rect in self.face_hitboxes.items():
            if rect.contains(unscaled_pos):
                return idx
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.globalPosition().toPoint()
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            release_pos = event.globalPosition().toPoint()
            local_pos = event.position() 
            
            unscaled_pos = QPointF(local_pos.x() / self.ui_scale, local_pos.y() / self.ui_scale)
            
            if (release_pos - self.drag_start_pos).manhattanLength() < 5:
                if self.finished:
                    self.restart_standup(shuffle=True)
                    return

                face_idx = self.get_face_index_at(unscaled_pos)
                if face_idx is not None:
                    if self.colleagues[face_idx].get("removed", False):
                        return
                    self.start_timer()
                    if (
                        0 <= self.current_index < len(self.colleagues)
                        and self.current_index != face_idx
                        and not self.colleagues[self.current_index].get("removed", False)
                    ):
                        self.spoken_indices.add(self.current_index)
                    self.current_index = face_idx
                    self.finished = False
                    self.running = True
                    self.update()
                    return

                self.next_person()

    def next_person(self):
        if self.finished:
            return 
            
        active_indices = get_active_indices(self.colleagues)
        if not active_indices:
            self.finish_meeting()
            return

        if self.current_index == -1 and not self.running:
            self.start_timer()
            self.update()
            return
            
        if (
            0 <= self.current_index < len(self.colleagues)
            and not self.colleagues[self.current_index].get("removed", False)
        ):
            self.spoken_indices.add(self.current_index)

        new_index = get_next_pending_index(active_indices, self.spoken_indices, self.current_index)
        if new_index is None:
            self.finish_meeting()
            return
            
        self.current_index = new_index
        
        self.running = True
        self.finished = False
        self.update()

    def tick(self):
        self.maybe_auto_start()
        now_perf = time.perf_counter()
        self.render_ticks += 1
        
        if self.running:
            self.run_ticks += 1
            delta_seconds = now_perf - self.last_tick_perf
            elapsed_seconds, self.elapsed_carry_seconds = accumulate_elapsed_seconds(
                self.elapsed_carry_seconds, delta_seconds, MAX_TICK_DELTA_SECONDS
            )
            if elapsed_seconds > 0:
                self.total_seconds += elapsed_seconds
                if not self.finished and 0 <= self.current_index < len(self.colleagues):
                    self.person_seconds_list[self.current_index] += elapsed_seconds
        self.last_tick_perf = now_perf
                    
        self.update()

    def draw_outlined_text(self, painter, rect, alignment, text, font, inner_color, outline_color):
        painter.setFont(font)
        fm = QFontMetrics(font)
        
        bound_rect = fm.boundingRect(rect, alignment, text)
        
        x = bound_rect.x()
        y = bound_rect.y() + fm.ascent()
        
        path = QPainterPath()
        path.addText(float(x), float(y), font, text)
        
        outline_pen = QPen(outline_color, 2) 
        outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(inner_color)
        painter.drawPath(path)

    def draw_outlined_mixed_text(self, painter, rect, segments, font_size, inner_color, outline_color):
        prepared_segments = []
        total_width = 0
        max_ascent = 0
        max_descent = 0

        for text, is_bold in segments:
            if not text:
                continue
            font = QFont(UI_FONT, font_size, QFont.Weight.Bold if is_bold else QFont.Weight.Medium)
            fm = QFontMetrics(font)
            width = fm.horizontalAdvance(text)
            prepared_segments.append((text, font, width))
            total_width += width
            max_ascent = max(max_ascent, fm.ascent())
            max_descent = max(max_descent, fm.descent())

        if not prepared_segments:
            return

        start_x = rect.x() + (rect.width() - total_width) / 2.0
        baseline_y = rect.y() + (rect.height() + max_ascent - max_descent) / 2.0

        for text, font, width in prepared_segments:
            path = QPainterPath()
            path.addText(float(start_x), float(baseline_y), font, text)

            outline_pen = QPen(outline_color, 2)
            outline_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(outline_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(inner_color)
            painter.drawPath(path)

            start_x += width

    def get_person_pixmap(self, person, variant):
        if not person.get("has_image", False):
            return None

        pixmap_cache = person.setdefault("pixmap_cache", {})
        cached_pixmap = pixmap_cache.get(variant)
        if cached_pixmap is not None:
            return cached_pixmap

        image_path = person.get("path")
        if not image_path:
            person["has_image"] = False
            return None

        raw_pixmap = person.get("raw_pixmap")
        if raw_pixmap is None:
            raw_pixmap = QPixmap(image_path)
            if raw_pixmap.isNull():
                person["has_image"] = False
                return None
            person["raw_pixmap"] = raw_pixmap

        if variant == "center":
            pixmap = self.create_circular_pixmap(raw_pixmap, 300)
        elif variant == "nextup":
            pixmap = self.create_circular_pixmap(raw_pixmap, 100)
        elif variant == "orbit":
            pixmap = self.create_circular_pixmap(raw_pixmap, 50)
        elif variant == "orbit_gray":
            gray_raw_pixmap = person.get("gray_raw_pixmap")
            if gray_raw_pixmap is None:
                gray_image = raw_pixmap.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
                gray_raw_pixmap = QPixmap.fromImage(gray_image)
                person["gray_raw_pixmap"] = gray_raw_pixmap
            pixmap = self.create_circular_pixmap(gray_raw_pixmap, 50)
        else:
            return None

        pixmap_cache[variant] = pixmap
        return pixmap

    def draw_red_cross(self, painter, rect):
        """Draw a red cross overlay inside the given rectangle."""
        pen = QPen(QColor(220, 40, 40, 220), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        margin = rect.width() * 0.2
        painter.drawLine(QPointF(rect.left() + margin, rect.top() + margin),
                         QPointF(rect.right() - margin, rect.bottom() - margin))
        painter.drawLine(QPointF(rect.left() + margin, rect.bottom() - margin),
                         QPointF(rect.right() - margin, rect.top() + margin))

    def draw_beacon(self, painter, path, center_x, center_y):
        angle = (self.render_ticks * 12) % 360
        grad = QConicalGradient(float(center_x), float(center_y), float(angle))
        
        grad.setColorAt(0.0, QColor(255, 0, 0, 150))      
        grad.setColorAt(0.25, QColor(0, 0, 0, 0))         
        grad.setColorAt(0.5, QColor(0, 0, 255, 150))      
        grad.setColorAt(0.75, QColor(0, 0, 0, 0))         
        grad.setColorAt(1.0, QColor(255, 0, 0, 150))      
        
        painter.fillPath(path, grad)

    def draw_first_name_overlay(self, painter, rect, first_name):
        if not first_name:
            return
        font_ratio = self.name_overlay_size_percent / 100.0
        position_ratio = self.name_overlay_position_percent / 100.0
        font_size = max(8, int(rect.height() * font_ratio))
        overlay_height = max(font_size * 2, int(rect.height() * 0.25))
        center_y = rect.y() + rect.height() * position_ratio
        top_y = center_y - (overlay_height / 2)
        top_y = max(rect.y(), min(rect.y() + rect.height() - overlay_height, top_y))
        overlay_rect = QRectF(rect.x(), top_y, rect.width(), overlay_height)
        self.draw_outlined_text(
            painter,
            overlay_rect.toRect(),
            Qt.AlignmentFlag.AlignCenter,
            first_name,
            QFont(UI_FONT, font_size, QFont.Weight.Bold),
            QColor(255, 255, 255, 230),
            QColor(0, 0, 0, 240),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.scale(self.ui_scale, self.ui_scale)

        person_seconds = 0
        person_limit = self.avg_time_limit
        if not self.finished and self.current_index >= 0:
            person_seconds = self.person_seconds_list[self.current_index]
            if self.current_index < len(self.person_time_limits):
                person_limit = self.person_time_limits[self.current_index]
            
        total_seconds = self.total_seconds
        countdown_mode = self.count_mode == TIMER_MODE_COUNTDOWN
        if countdown_mode:
            person_display_seconds = person_limit - person_seconds
            total_display_seconds = self.current_time_limit - total_seconds
        else:
            person_display_seconds = person_seconds
            total_display_seconds = total_seconds

        cx, cy = 270, 270
        main_circle_rect = QRect(120, 120, 300, 300)

        # 1. Draw Main Large Circle
        path = QPainterPath()
        path.addEllipse(QRectF(main_circle_rect)) 
        painter.setClipPath(path)

        if self.finished:
            painter.fillPath(path, QColor(50, 205, 50)) 
            painter.setClipping(False)
            painter.setPen(QPen(Qt.GlobalColor.black, 4))
            painter.drawEllipse(main_circle_rect)

            center_y = main_circle_rect.center().y()
            final_time_str = f"Total time: {format_duration_clock(total_seconds)}"
            self.draw_outlined_text(
                painter, QRect(main_circle_rect.left(), center_y - 34, main_circle_rect.width(), 30),
                Qt.AlignmentFlag.AlignCenter, 
                final_time_str, QFont(UI_FONT, 18, QFont.Weight.Bold), 
                QColor(255, 255, 255), QColor(0, 0, 0)
            )

            first_line_segments, second_line_segments = build_finished_delta_message_lines(
                self.current_time_limit,
                total_seconds,
            )
            self.draw_outlined_mixed_text(
                painter,
                QRect(main_circle_rect.left() + 8, center_y - 4, main_circle_rect.width() - 16, 24),
                first_line_segments,
                10,
                QColor(255, 255, 255),
                QColor(0, 0, 0),
            )
            self.draw_outlined_mixed_text(
                painter,
                QRect(main_circle_rect.left() + 8, center_y + 20, main_circle_rect.width() - 16, 24),
                second_line_segments,
                10,
                QColor(255, 255, 255),
                QColor(0, 0, 0),
            )

            self.draw_outlined_text(
                painter,
                QRect(main_circle_rect.left(), main_circle_rect.bottom() - 38, main_circle_rect.width(), 28),
                Qt.AlignmentFlag.AlignCenter,
                "Click to restart",
                QFont(UI_FONT, 11, QFont.Weight.Bold),
                QColor(255, 255, 255),
                QColor(0, 0, 0)
            )

        elif self.current_index == -1:
            painter.fillPath(path, QColor(40, 40, 40))
            
            if not self.running:
                painter.setPen(QPen(QColor(255, 255, 255, 128), 5))
                painter.setFont(QFont(UI_FONT, 22, QFont.Weight.Bold))
                painter.drawText(main_circle_rect.adjusted(0, -20, 0, -20), Qt.AlignmentFlag.AlignCenter, "Click to Start")
                
                painter.setFont(QFont(UI_FONT, 14, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(200, 200, 200, 128), 5))
                if self.auto_start_enabled:
                    countdown_seconds = seconds_until_next_auto_start(
                        self.auto_start_enabled,
                        self.auto_start_time,
                        datetime.now(),
                        self.last_auto_start_date,
                    )
                    if countdown_seconds is not None:
                        countdown_text = format_duration_clock(countdown_seconds)
                        painter.drawText(
                            main_circle_rect.adjusted(0, 30, 0, 30),
                            Qt.AlignmentFlag.AlignCenter,
                            f"Starts in: {countdown_text}",
                        )
                    else:
                        painter.drawText(
                            main_circle_rect.adjusted(0, 30, 0, 30),
                            Qt.AlignmentFlag.AlignCenter,
                            f"Start at: {self.auto_start_time}",
                        )
                elif countdown_mode:
                    time_str = format_timer_value(self.current_time_limit, TIMER_MODE_COUNTDOWN)
                    painter.drawText(main_circle_rect.adjusted(0, 30, 0, 30), Qt.AlignmentFlag.AlignCenter, f"Duration: {time_str}")
                else:
                    painter.drawText(main_circle_rect.adjusted(0, 30, 0, 30), Qt.AlignmentFlag.AlignCenter, "Mode: Count up")
            else:
                if countdown_mode and total_display_seconds <= 0:
                    self.draw_beacon(painter, path, main_circle_rect.center().x(), main_circle_rect.center().y())

                elapsed_str = format_timer_value(total_display_seconds, self.count_mode)
                
                self.draw_outlined_text(
                    painter, main_circle_rect.adjusted(0, -30, 0, -30), Qt.AlignmentFlag.AlignCenter, 
                    elapsed_str, QFont(UI_FONT, 65, QFont.Weight.Bold), 
                    QColor(255, 50, 50, 140) if countdown_mode else QColor(255, 255, 255, 170),
                    QColor(0, 0, 0, 255)
                )
                
                self.draw_outlined_text(
                    painter, main_circle_rect.adjusted(0, 70, 0, 70), Qt.AlignmentFlag.AlignCenter, 
                    "Meeting Active", QFont(UI_FONT, 22, QFont.Weight.Bold), 
                    QColor(255, 255, 255, 140), QColor(0, 0, 0, 255)
                )
        else:
            person = self.colleagues[self.current_index]
            
            if person["has_image"]:
                pixmap = self.get_person_pixmap(person, "center")
                if pixmap is not None:
                    x_offset = (300 - pixmap.width()) // 2
                    y_offset = (300 - pixmap.height()) // 2
                    painter.drawPixmap(120 + x_offset, 120 + y_offset, pixmap)
                else:
                    person["has_image"] = False
            if not person["has_image"]:
                painter.fillPath(path, QColor(100, 150, 250))
                painter.setPen(QColor(255, 255, 255, 128))
                painter.setFont(QFont(UI_FONT, 40, QFont.Weight.Bold))
                initial_rect = main_circle_rect.adjusted(0, 0, 0, -120)
                painter.drawText(initial_rect, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, person["name"][0])

            if countdown_mode and total_display_seconds <= 0:
                self.draw_beacon(painter, path, main_circle_rect.center().x(), main_circle_rect.center().y())
            elif countdown_mode and 0 < person_display_seconds <= 10:
                blink_color = QColor(255, 0, 0, 64) if (self.render_ticks // 10) % 2 == 0 else QColor(255, 255, 0, 64)
                painter.fillPath(path, blink_color)
            elif countdown_mode and person_display_seconds <= 0:
                painter.fillPath(path, QColor(255, 0, 0, 128))

        if not self.finished:
            painter.setClipping(False)
            painter.setPen(QPen(Qt.GlobalColor.black, 4))
            painter.drawEllipse(main_circle_rect)

        # 2. Draw Orbiting Colleagues
        painter.setClipping(False)
        self.face_hitboxes.clear()
        
        N = len(self.colleagues)
        if N > 0:
            orbit_R = 185
            next_up_index, upcoming_indices, spoken_indices, removed_indices = get_queue_layout(
                self.colleagues, self.spoken_indices, self.current_index
            )
            spoken_removed_indices = spoken_indices + removed_indices
            upcoming_offsets = {idx: pos + 1 for pos, idx in enumerate(upcoming_indices)}
            spoken_offsets = {idx: -(pos + 1) for pos, idx in enumerate(spoken_removed_indices)}

            N_visible = len(upcoming_indices) + len(spoken_removed_indices)
            if next_up_index is not None:
                N_visible += 1

            angle_step = 16
            large_gap = 25
            if N_visible > 0:
                max_allowed_step = 300 / N_visible
                if angle_step > max_allowed_step:
                    angle_step = max_allowed_step
                    large_gap = angle_step * 1.5

            for i in range(N):
                if i == self.current_index and not self.finished and self.current_index != -1:
                    continue

                if i == next_up_index:
                    offset = 0
                    size = 100
                elif i in upcoming_offsets:
                    offset = upcoming_offsets[i]
                    size = 50
                elif i in spoken_offsets:
                    offset = spoken_offsets[i]
                    size = 50
                else:
                    continue

                angle_deg = compute_orbit_angle(offset, angle_step, large_gap)
                angle_rad = math.radians(angle_deg)
                x = cx + orbit_R * math.cos(angle_rad)
                y = cy + orbit_R * math.sin(angle_rad)

                person = self.colleagues[i]
                is_removed = person.get("removed", False)
                is_spoken = (i in spoken_indices)
                is_next_up = (i == next_up_index and not self.finished and not is_spoken and not is_removed)

                rect_small = QRectF(x - (size / 2), y - (size / 2), size, size)
                self.face_hitboxes[i] = rect_small

                path_small = QPainterPath()
                path_small.addEllipse(rect_small)

                if person["has_image"]:
                    if is_removed or is_spoken:
                        pixmap = self.get_person_pixmap(person, "orbit_gray")
                    elif is_next_up:
                        pixmap = self.get_person_pixmap(person, "nextup")
                    else:
                        pixmap = self.get_person_pixmap(person, "orbit")

                    if pixmap is not None:
                        px_x = x - pixmap.width() / 2
                        px_y = y - pixmap.height() / 2
                        painter.drawPixmap(int(px_x), int(px_y), pixmap)
                    else:
                        person["has_image"] = False
                if not person["has_image"]:
                    color = QColor(100, 100, 100) if is_spoken or is_removed else QColor(200, 200, 200)
                    painter.fillPath(path_small, color)
                    painter.setPen(QColor(0, 0, 0, 128))
                    font_size = 35 if size == 100 else 20
                    painter.setFont(QFont(UI_FONT, font_size, QFont.Weight.Bold))
                    painter.drawText(rect_small, Qt.AlignmentFlag.AlignCenter, person["name"][0])

                if (
                    self.show_first_name_overlay
                    and person.get("has_image", False)
                    and not is_removed
                ):
                    self.draw_first_name_overlay(painter, rect_small, person.get("first_name", ""))

                painter.setBrush(Qt.BrushStyle.NoBrush)
                if is_spoken:
                    painter.setPen(QPen(QColor(50, 205, 50), 3))
                    painter.drawEllipse(rect_small)
                    painter.setBrush(QColor(0, 0, 0, 120))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(rect_small)
                elif is_next_up:
                    painter.setPen(QPen(QColor(255, 215, 0), 4))
                    painter.drawEllipse(rect_small)

                    pill_rect = QRect(int(x) - 40, int(y) + 55, 80, 20)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(255, 255, 255, 220))
                    painter.drawRoundedRect(pill_rect, 10, 10)
                    painter.setPen(QColor(0, 0, 0, 200))
                    painter.setFont(QFont(UI_FONT, 8, QFont.Weight.Bold))
                    painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "NEXT UP")
                else:
                    painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                    painter.drawEllipse(rect_small)

                if countdown_mode and total_display_seconds <= 0 and (self.current_index != -1 or self.running) and not self.finished:
                    self.draw_beacon(painter, path_small, x, y)

                if is_removed:
                    self.draw_red_cross(painter, rect_small)


        # 3. Draw Main UI Timer Text Overlay
        if self.current_index != -1 and not self.finished:
            active_name = self.colleagues[self.current_index].get("name", f"Person {self.current_index + 1}")
            self.draw_outlined_text(
                painter,
                active_name_rect_for_main_circle(main_circle_rect),
                Qt.AlignmentFlag.AlignCenter,
                active_name,
                QFont(UI_FONT, 16, QFont.Weight.Bold),
                QColor(255, 255, 255, 235),
                QColor(0, 0, 0, 255),
            )

            time_str = format_timer_value(person_display_seconds, self.count_mode)
            
            self.draw_outlined_text(
                painter, main_circle_rect, Qt.AlignmentFlag.AlignCenter, 
                time_str, QFont(UI_FONT, 65, QFont.Weight.Bold), 
                QColor(255, 255, 255, 140), QColor(0, 0, 0, 255)
            )

            elapsed_str = format_timer_value(total_display_seconds, self.count_mode)
            
            self.draw_outlined_text(
                painter, main_circle_rect.adjusted(0, 100, 0, 100), Qt.AlignmentFlag.AlignCenter, 
                elapsed_str, QFont(UI_FONT, 22, QFont.Weight.Bold), 
                QColor(255, 50, 50, 140) if countdown_mode else QColor(255, 255, 255, 170),
                QColor(0, 0, 0, 255)
            )

if __name__ == "__main__":
    set_windows_app_user_model_id(APP_USER_MODEL_ID)
    app = QApplication(sys.argv)
    app_icon = load_application_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    timer = StandupTimer()
    timer.show()
    sys.exit(app.exec())
