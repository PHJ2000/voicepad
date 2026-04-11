from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from codex_dictation_settings import APP_NAME, APP_VERSION, AUDIO_PRESET_UI_LABELS, audio_preset_label


class AppUIMixin:
    def _ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(5, weight=1)
        head = ttk.Frame(self.root, padding=12)
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text=APP_NAME, font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(head, text=f"v{APP_VERSION}", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(head, textvariable=self.status, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="e")
        ttk.Label(head, textvariable=self.target).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(
            head,
            textvariable=self.app_hotkey_summary,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(
            head,
            text="음성 명령: 보내, 지워, 다 지워, 전체 비워, 다시 ..., 복사, 붙여넣기, 잘라, 취소, 되돌려, 자동/한국어/영어, 최대화/최소화/복원, 이스케이프/나가기, 일시정지/재생, 앞으로/뒤로 감기",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))
        qs = ttk.LabelFrame(self.root, text="Quick Start", padding=12)
        qs.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        qs.columnconfigure(0, weight=1)
        ttk.Label(qs, textvariable=self.quick_start_summary, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(qs, textvariable=self.quick_start_hotkeys, wraplength=920, justify="left").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(qs, textvariable=self.quick_start_checklist, wraplength=920, justify="left").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(qs, textvariable=self.quick_start_paths, font=("Consolas", 9), wraplength=920, justify="left").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Label(qs, textvariable=self.quick_start_trouble, wraplength=920, justify="left").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Label(qs, textvariable=self.hotkey_feedback, wraplength=920, justify="left").grid(row=5, column=0, sticky="w", pady=(6, 0))
        quick_btn = ttk.Frame(qs)
        quick_btn.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        for index in range(5):
            quick_btn.columnconfigure(index, weight=1)
        ttk.Button(quick_btn, text="Doctor 보기", command=self.show_doctor).grid(row=0, column=0, sticky="ew")
        ttk.Button(quick_btn, text="Doctor 복사", command=self.copy_doctor_report).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(quick_btn, text="설정 열기", command=self.open_settings_path).grid(row=0, column=2, sticky="ew")
        ttk.Button(quick_btn, text="로그 열기", command=self.open_log_path).grid(row=0, column=3, sticky="ew", padx=6)
        ttk.Button(quick_btn, text="데이터 폴더", command=self.open_data_root).grid(row=0, column=4, sticky="ew")
        ttk.Label(head, textvariable=self.audio_status, font=("Consolas", 9)).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(head, textvariable=self.llm_status, font=("Consolas", 9)).grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        top = ttk.Frame(self.root, padding=(12, 0, 12, 0))
        top.grid(row=2, column=0, sticky="nsew")
        top.columnconfigure((0, 1), weight=1)
        left = ttk.LabelFrame(top, text="Recording", padding=12)
        right = ttk.LabelFrame(top, text="Output, Target, Hotkeys", padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._combo(left, "Input Device", "input_device", self.devices, 0)
        self._entry(left, "Sample Rate", "sample_rate", 1)
        self._entry(left, "Input Gain", "input_gain", 2)
        self._combo(left, "Audio Preset", "audio_preset", [audio_preset_label(key) for key in AUDIO_PRESET_UI_LABELS], 3)
        self._entry(left, "Noise Gate Threshold", "noise_gate_threshold", 4)
        self._combo(left, "Whisper Model", "whisper_model", ["tiny", "base", "small", "medium", "large-v3-turbo"], 5)
        self._combo(left, "Whisper Device", "whisper_device", ["auto", "cpu", "cuda"], 6)
        self._combo(left, "Compute Type", "whisper_compute_type", ["auto", "int8", "int8_float16", "float16", "float32"], 7)
        self._combo(left, "Language", "language", ["자동", "한국어", "영어"], 8)
        self._entry(left, "Initial Prompt", "initial_prompt", 9)
        self._entry(left, "Max Record Seconds", "max_record_seconds", 10)
        self._entry(left, "Speech End Silence Seconds", "auto_stop_silence_seconds", 11)
        self._entry(left, "Always Listen Pre-roll Seconds", "always_listen_preroll_seconds", 12)
        self._check(left, "Trim leading and trailing silence", "trim_silence", 13)
        self._check(left, "Normalize whitespace", "normalize_whitespace", 14)
        self._check(left, "Enable manual mode auto stop", "enable_auto_stop", 15)
        self._check(left, "Play feedback beeps", "beep_feedback", 16)
        self._check(left, "Keep window on top", "keep_window_on_top", 17)
        ttk.Button(left, text="Apply Audio Preset", command=self.apply_audio_preset).grid(row=18, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(left, text="Apply Always-Listen Tuning", command=self.apply_always_listen_tuning).grid(row=19, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(left, text="Revert Last Tuning", command=self.revert_always_listen_tuning).grid(row=20, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(left, text="Reset Tuning Stats", command=self.reset_always_listen_tuning_stats).grid(row=21, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        apf = ttk.LabelFrame(left, text="Audio Profiles", padding=8)
        apf.grid(row=22, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        apf.columnconfigure(1, weight=1)
        ttk.Label(apf, text="Saved Profile").grid(row=0, column=0, sticky="w")
        self.audio_profile_combo = ttk.Combobox(apf, textvariable=self.vars["selected_audio_profile"], values=[], state="normal")
        self.audio_profile_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(apf, text="Profile Name").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(apf, textvariable=self.audio_profile_name).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        profile_btn = ttk.Frame(apf)
        profile_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for index in range(3):
            profile_btn.columnconfigure(index, weight=1)
        ttk.Button(profile_btn, text="Apply Profile", command=self.apply_selected_audio_profile).grid(row=0, column=0, sticky="ew")
        ttk.Button(profile_btn, text="Save Current", command=self.save_audio_profile).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(profile_btn, text="Delete Profile", command=self.delete_selected_audio_profile).grid(row=0, column=2, sticky="ew")
        self._combo(right, "Output Mode", "output_mode", ["auto", "paste", "clipboard", "type"], 0)
        self._entry(right, "Paste Hotkey", "paste_hotkey", 1)
        self._check(right, "Press Enter after output", "auto_enter", 2)
        self._check(right, "Always listen when target input window is focused", "always_listen_enabled", 3)
        self._entry(right, "Always Listen Hotkey", "always_listen_hotkey", 4)
        self._entry(right, "Record Hotkey", "record_hotkey", 5)
        self._entry(right, "Paste Last Hotkey", "paste_last_hotkey", 6)
        self._entry(right, "Toggle Output Hotkey", "toggle_output_hotkey", 7)
        self._entry(right, "Toggle Enter Hotkey", "toggle_enter_hotkey", 8)
        ttk.Label(right, text="Launcher Hotkeys", font=("Segoe UI", 9, "bold")).grid(row=9, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._entry(right, "Launcher Toggle Hotkey", "launcher_toggle_hotkey", 10)
        self._entry(right, "Launcher Show Hotkey", "launcher_show_hotkey", 11)
        self._entry(right, "Launcher Hide Hotkey", "launcher_hide_hotkey", 12)
        self._entry(right, "Launcher Exit Hotkey", "launcher_exit_hotkey", 13)
        self._check(right, "Enable local LLM correction command", "llm_correction_enabled", 14)
        self._combo(right, "LLM Profile", "llm_profile", ["균형", "정확도", "직접지정"], 15)
        self._entry(right, "LLM Model", "llm_model", 16)
        self._entry(right, "LLM Base URL", "llm_base_url", 17)
        self._entry(right, "LLM Timeout Seconds", "llm_timeout_seconds", 18)
        btn = ttk.Frame(right)
        btn.grid(row=19, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        [btn.columnconfigure(i, weight=1) for i in range(3)]
        for row, col, text, cmd in [
            (0, 0, "Start / Stop Manual", self.toggle_recording),
            (0, 1, "Toggle Always Listen", self.toggle_always_listen),
            (0, 2, "Paste Last", self.paste_last),
            (1, 0, "Save Settings", self.save_from_ui),
            (1, 1, "Doctor", self.show_doctor),
            (1, 2, "Refresh Hotkeys", self.register_hotkeys),
            (2, 0, "Copy Last", self.copy_last),
        ]:
            ttk.Button(btn, text=text, command=cmd).grid(row=row, column=col, sticky="ew", padx=6 if col == 1 else (0 if col == 0 else 6), pady=(8 if row else 0, 0))
        tf = ttk.LabelFrame(self.root, text="Latest Transcript", padding=12)
        tf.grid(row=3, column=0, sticky="nsew", padx=12, pady=(12, 6))
        tf.columnconfigure(0, weight=1)
        self.txt = tk.Text(tf, wrap="word", height=8, font=("Segoe UI", 10))
        self.txt.grid(row=0, column=0, sticky="nsew")
        hf = ttk.LabelFrame(self.root, text="History Browser", padding=12)
        hf.grid(row=4, column=0, sticky="nsew", padx=12, pady=6)
        hf.columnconfigure(0, weight=1)
        ttk.Label(hf, text="Search").grid(row=0, column=0, sticky="w")
        ttk.Entry(hf, textvariable=self.history_query).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(hf, text="Refresh", command=self.refresh_history_browser).grid(row=0, column=2, sticky="ew")
        self.history_list = tk.Listbox(hf, height=6, font=("Consolas", 10))
        self.history_list.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        self.history_list.bind("<Double-Button-1>", lambda _event: self.paste_selected_history())
        ttk.Label(hf, textvariable=self.history_empty).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        history_btn = ttk.Frame(hf)
        history_btn.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        for index in range(3):
            history_btn.columnconfigure(index, weight=1)
        ttk.Button(history_btn, text="Load Selected", command=self.load_selected_history).grid(row=0, column=0, sticky="ew")
        ttk.Button(history_btn, text="Copy Selected", command=self.copy_selected_history).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(history_btn, text="Paste Selected", command=self.paste_selected_history).grid(row=0, column=2, sticky="ew")
        lf = ttk.LabelFrame(self.root, text="Activity", padding=12)
        lf.grid(row=5, column=0, sticky="nsew", padx=12, pady=(6, 12))
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.log_text = tk.Text(lf, wrap="word", font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")

    def _entry(self, parent, label, key, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", pady=(6, 0), padx=(8, 0))
        parent.columnconfigure(1, weight=1)

    def _combo(self, parent, label, key, values, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="normal").grid(row=row, column=1, sticky="ew", pady=(6, 0), padx=(8, 0))
        parent.columnconfigure(1, weight=1)

    def _check(self, parent, label, key, row):
        ttk.Checkbutton(parent, text=label, variable=self.bools[key]).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8 if row in {2, 3, 10} else 0, 0))

