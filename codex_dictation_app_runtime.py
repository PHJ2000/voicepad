from __future__ import annotations

import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf
from tkinter import messagebox

from codex_dictation_audio import trim_silence
from codex_dictation_diagnostics import doctor, first_run_guidance
from codex_dictation_settings import (
    APP_NAME,
    DATA_ROOT,
    LOG_PATH,
    SETTINGS_PATH,
    app_hotkey_items,
    audio_preset_label,
    hotkey_conflicts,
    hotkey_items,
    language_label,
    launcher_hotkey_items,
    llm_profile_label,
    normalize_audio_preset_value,
    normalize_hotkey_value,
    normalize_language_value,
    normalize_llm_profile_value,
    normalize_output_mode_value,
    resolve_llm_model,
    save_settings,
)
from codex_dictation_targeting import APP_PID, fg_info, focus_best_terminal, focus_window, is_target_window, target_context_key
from codex_dictation_utils import append_history, normalize_text

def hotkey_display_text(value: str) -> str:
    parts = [part for part in (value or "").split("+") if part]
    formatted: list[str] = []
    for part in parts:
        lowered = part.lower()
        if lowered == "ctrl":
            formatted.append("Ctrl")
        elif lowered == "alt":
            formatted.append("Alt")
        elif lowered == "shift":
            formatted.append("Shift")
        elif lowered == "win":
            formatted.append("Win")
        elif re.fullmatch(r"f\d{1,2}", lowered):
            formatted.append(lowered.upper())
        elif len(lowered) == 1:
            formatted.append(lowered.upper())
        else:
            formatted.append(lowered.capitalize())
    return "+".join(formatted) if formatted else "미설정"


def summarize_hotkey_group(prefix: str, items: tuple[dict[str, str], ...]) -> str:
    details = ", ".join(f"{item['label']} {hotkey_display_text(item['value'])}" for item in items)
    return f"{prefix} | {details}"


def describe_model_prepare_state(
    model_name: str,
    phase: str,
    *,
    first_attempt: bool = False,
    error: str = "",
) -> tuple[str, str]:
    name = model_name or "unknown"
    if phase == "loading":
        hint = (
            "첫 준비라면 모델 다운로드 때문에 시간이 더 걸릴 수 있습니다."
            if first_attempt
            else "로컬에 준비된 모델을 메모리에 불러오는 중입니다."
        )
        return (
            f"모델 다운로드/로드 중 ({name})",
            f"Model prepare stage: loading {name}. {hint}",
        )
    if phase == "warming":
        return (
            f"모델 워밍업 중 ({name})",
            f"Model prepare stage: warmup sample for {name}",
        )
    if phase == "ready":
        return (
            f"모델 준비됨 ({name})",
            f"Model prepare stage: ready {name}",
        )
    if phase == "load_failed":
        return (
            f"모델 다운로드/로드 실패 ({error or name})",
            f"Model prepare stage failed while loading {name}: {error or 'unknown error'}",
        )
    if phase == "warmup_failed":
        return (
            f"모델 워밍업 실패 ({error or name})",
            f"Model prepare stage failed during warmup for {name}: {error or 'unknown error'}",
        )
    return (
        f"모델 준비 중 ({name})",
        f"Model prepare stage: pending {name}",
    )


def describe_hotkey_update(previous_values: dict[str, str], settings) -> str:
    current_items = hotkey_items(settings)
    changed = [
        item
        for item in current_items
        if normalize_hotkey_value(previous_values.get(item["field"], ""), fallback=item["default"]) != item["value"]
    ]
    launcher_fields = {item["field"] for item in launcher_hotkey_items(settings)}
    conflicts = hotkey_conflicts(settings)

    messages: list[str] = []
    if changed:
        changed_text = ", ".join(f"{item['label']} {hotkey_display_text(item['value'])}" for item in changed)
        if any(item["field"] in launcher_fields for item in changed):
            messages.append(f"핫키 저장됨: {changed_text}. 런처가 실행 중이면 잠시 뒤 새 설정을 다시 읽습니다.")
        else:
            messages.append(f"핫키 저장됨: {changed_text}.")
    else:
        messages.append("핫키 설정을 저장했습니다. 현재 적용값은 아래 요약에서 바로 확인할 수 있습니다.")

    if conflicts:
        item_map = {item["field"]: item["label"] for item in current_items}
        warning_parts = []
        for hotkey, fields in conflicts.items():
            labels = ", ".join(item_map.get(field, field) for field in fields)
            warning_parts.append(f"{hotkey_display_text(hotkey)} 중복({labels})")
        messages.append("충돌 주의: " + " | ".join(warning_parts))
    return " ".join(messages)
class AppRuntimeMixin:
    def set_model_prepare_state(
        self,
        phase: str,
        *,
        first_attempt: bool = False,
        error: str = "",
        log_message: bool = True,
    ):
        brief, detail = describe_model_prepare_state(
            self.s.whisper_model,
            phase,
            first_attempt=first_attempt,
            error=error,
        )
        self.model_status_brief = brief
        self.refresh_quick_start()
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        if log_message:
            self.log(detail)

    def summarize_all_hotkeys(self) -> str:
        return summarize_hotkey_group("현재 앱 단축키", app_hotkey_items(self.s))

    def refresh_hotkey_overview(self, feedback: str | None = None):
        self.quick_start_hotkeys.set(summarize_hotkey_group("현재 런처 단축키", launcher_hotkey_items(self.s)))
        self.app_hotkey_summary.set(self.summarize_all_hotkeys())
        if feedback is not None:
            self.hotkey_feedback.set(feedback)

    def refresh_quick_start(self):
        summary, checklist, paths, trouble = first_run_guidance(
            self.s,
            input_device_count=len(getattr(self, "devices", [])),
            model_status=self.model_status_brief,
            hotkey_status=self.hotkey_status_brief,
        )
        self.quick_start_summary.set(summary)
        self.quick_start_checklist.set(checklist)
        self.quick_start_paths.set(paths)
        self.quick_start_trouble.set(trouble)
        self.refresh_hotkey_overview()

    def refresh_tuning_status(self):
        suggestion = self.listen.tuning_snapshot()
        if suggestion.ready:
            detail = suggestion.describe_changes()
            self.tuning_status.set(f"Always-listen Tuning | {detail}")
        else:
            self.tuning_status.set(f"Always-listen Tuning | {suggestion.summary}")

    def refresh_status(self, activity="Idle"):
        queue_depth = self.jobs.qsize()
        pipeline_parts = []
        if self.transcribing:
            source_label = self.active_transcription_source.replace("_", "-") if self.active_transcription_source else "active"
            pipeline_parts.append(f"STT {source_label}")
        if queue_depth > 0:
            pipeline_parts.append(f"QUEUE {queue_depth}")
        pipeline_suffix = f" | {' | '.join(pipeline_parts)}" if pipeline_parts else ""
        self.status.set(
            f"{activity} | {self.s.output_mode.upper()} | {language_label(self.s.language)}"
            f"{' | LLM ' + llm_profile_label(self.s.llm_profile) if self.s.llm_correction_enabled else ''}"
            f"{' + ENTER' if self.s.auto_enter else ''}"
            f"{' | ALWAYS-ON' if self.listen.on else ''}"
            f"{pipeline_suffix}"
        )

    def refresh_audio_status(self):
        source = "manual" if self.rec.on else ("always-listen" if self.listen.on else "idle")
        rms, peak, threshold, voice, updated = self.rec.meter_snapshot() if self.rec.on else self.listen.meter_snapshot()
        waiting = "waiting for input" if updated <= 0 else f"rms={rms:.4f} | peak={peak:.4f} | threshold={threshold:.4f} | voice={'yes' if voice else 'no'}"
        self.audio_status.set(f"Audio | source={source} | preset={audio_preset_label(self.s.audio_preset)} | gain={self.s.input_gain:.2f} | gate={self.s.noise_gate_threshold:.3f} | {waiting}")

    def refresh_target(self):
        self.target.set("Target: focused terminal or input field")

    def bootstrap_after_launch(self):
        self.minimize_after_startup()
        self.restore_launch_target_after_startup()
        self.refresh_status("Warming up")
        self.warmup_model()
        self.register_hotkeys()
        self.sync_listener()
        self.log("Ready")

    def minimize_after_startup(self):
        self.log("Startup minimize skipped")
        return

    def ensure_window_visible_on_startup(self):
        if not self.show_window:
            return
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.after(250, lambda: self.root.attributes("-topmost", self.s.keep_window_on_top))
            self.log("Startup window shown")
        except Exception as exc:
            self.log(f"Startup window show failed: {exc}")

    def restore_launch_target_after_startup(self):
        try:
            if self.show_window:
                return
            if self.target_active():
                return
            if self.launch_target and self.launch_target.pid != APP_PID and focus_window(self.launch_target.hwnd):
                self.log("Focused previous window after startup")
                return
            if focus_best_terminal():
                self.log("Focused terminal after startup")
        except Exception as exc:
            self.log(f"Startup target focus skipped: {exc}")

    def save_from_ui(self):
        previous_hotkeys = {item["field"]: item["value"] for item in hotkey_items(self.s)}
        for key, var in self.vars.items():
            current = getattr(self.s, key)
            raw = var.get().strip()
            if key == "language":
                setattr(self.s, key, normalize_language_value(raw))
                self.vars["language"].set(language_label(self.s.language))
            elif key == "audio_preset":
                setattr(self.s, key, normalize_audio_preset_value(raw))
                self.vars["audio_preset"].set(audio_preset_label(self.s.audio_preset))
            elif key == "llm_profile":
                setattr(self.s, key, normalize_llm_profile_value(raw))
                self.vars["llm_profile"].set(llm_profile_label(self.s.llm_profile))
            elif key == "output_mode":
                setattr(self.s, key, normalize_output_mode_value(raw))
                self.vars["output_mode"].set(self.s.output_mode)
            elif key.endswith("_hotkey"):
                setattr(self.s, key, normalize_hotkey_value(raw, fallback=str(current)))
                self.vars[key].set(getattr(self.s, key))
            elif isinstance(current, int):
                setattr(self.s, key, int(raw or "0"))
            elif isinstance(current, float):
                setattr(self.s, key, float(raw or "0"))
            else:
                setattr(self.s, key, raw)
        self.s.input_gain = max(float(self.s.input_gain), 0.0)
        self.s.noise_gate_threshold = max(float(self.s.noise_gate_threshold), 0.0)
        self.vars["input_gain"].set(str(self.s.input_gain))
        self.vars["noise_gate_threshold"].set(str(self.s.noise_gate_threshold))
        for key, var in self.bools.items():
            setattr(self.s, key, bool(var.get()))
        save_settings(self.s)
        self.rec.s = self.s
        self.listen.s = self.s
        self.root.attributes("-topmost", self.s.keep_window_on_top)
        self.refresh_target()
        self.refresh_status()
        self.refresh_audio_status()
        self.refresh_tuning_status()
        self.refresh_quick_start()
        self._sync_llm_status_idle()
        feedback = describe_hotkey_update(previous_hotkeys, self.s)
        self.refresh_hotkey_overview(feedback=feedback)
        self.log(feedback)
        self.log("Settings saved")

    def apply_always_listen_tuning(self):
        suggestion = self.listen.tuning_snapshot()
        if not suggestion.ready:
            self.log(f"Always-listen tuning skipped: {suggestion.summary}")
            self.refresh_tuning_status()
            return
        backup = {
            "input_gain": self.s.input_gain,
            "always_listen_preroll_seconds": self.s.always_listen_preroll_seconds,
            "auto_stop_silence_seconds": self.s.auto_stop_silence_seconds,
        }
        self.last_always_listen_tuning_backup = backup
        for key, value in suggestion.changes.items():
            setattr(self.s, key, value)
            if key in self.vars:
                self.vars[key].set(str(value))
        save_settings(self.s)
        self.listen.s = self.s
        self.rec.s = self.s
        self.listen.reset_tuning_stats()
        self.refresh_audio_status()
        self.refresh_tuning_status()
        self.log(f"Applied always-listen tuning: {suggestion.describe_changes()}")

    def revert_always_listen_tuning(self):
        if not self.last_always_listen_tuning_backup:
            self.log("Always-listen tuning revert skipped: no previous tuning snapshot")
            return
        for key, value in self.last_always_listen_tuning_backup.items():
            setattr(self.s, key, value)
            if key in self.vars:
                self.vars[key].set(str(value))
        save_settings(self.s)
        self.listen.s = self.s
        self.rec.s = self.s
        self.listen.reset_tuning_stats()
        self.refresh_audio_status()
        self.refresh_tuning_status()
        self.log("Reverted last always-listen tuning suggestion")
        self.last_always_listen_tuning_backup = None

    def reset_always_listen_tuning_stats(self):
        self.listen.reset_tuning_stats()
        self.refresh_tuning_status()
        self.log("Reset always-listen tuning stats")

    def register_hotkeys(self):
        self.save_from_ui()
        try:
            import keyboard
        except Exception as exc:
            self.hotkey_status_brief = f"단축키 사용 불가 ({exc})"
            self.refresh_quick_start()
            self.log(f"Hotkeys unavailable: {exc}")
            return
        try:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception as exc:
                self.log(f"Hotkey cleanup skipped: {exc}")
            keyboard.add_hotkey(self.s.always_listen_hotkey, self.toggle_always_listen, suppress=False, trigger_on_release=False)
            keyboard.add_hotkey(self.s.record_hotkey, self.toggle_recording, suppress=False, trigger_on_release=False)
            keyboard.add_hotkey(self.s.paste_last_hotkey, self.paste_last, suppress=False, trigger_on_release=False)
            keyboard.add_hotkey(self.s.toggle_output_hotkey, self.cycle_output, suppress=False, trigger_on_release=False)
            keyboard.add_hotkey(self.s.toggle_enter_hotkey, self.toggle_enter, suppress=False, trigger_on_release=False)
            self.hotkey_status_brief = "단축키 등록됨"
            self.refresh_quick_start()
            self.log("Hotkeys registered")
        except Exception as exc:
            self.hotkey_status_brief = f"단축키 등록 실패 ({exc})"
            self.refresh_quick_start()
            self.log(f"Hotkey registration failed: {exc}")

    def beep(self, kind):
        if not self.s.beep_feedback:
            return
        try:
            import winsound

            for current, freq, dur in [("start", 880, 90), ("stop", 660, 110), ("done", 1040, 120), ("error", 330, 160)]:
                if kind == current:
                    winsound.Beep(freq, dur)
                    return
        except Exception:
            pass

    def target_active(self) -> bool:
        info = fg_info()
        if not info:
            return False
        return is_target_window(info)

    def sync_listener(self):
        if self.s.always_listen_enabled and not self.listen.on:
            try:
                self.listen.start()
            except Exception as exc:
                self.s.always_listen_enabled = False
                self.bools["always_listen_enabled"].set(False)
                save_settings(self.s)
                self.beep("error")
                self.log(f"Failed to start always-listen: {exc}")
        elif not self.s.always_listen_enabled and self.listen.on:
            self.listen.stop()
        self.refresh_status()

    def toggle_always_listen(self):
        if self.rec.on:
            self.log("Stop manual recording before enabling always-listen")
            return
        self.s.always_listen_enabled = not self.s.always_listen_enabled
        self.bools["always_listen_enabled"].set(self.s.always_listen_enabled)
        save_settings(self.s)
        self.sync_listener()
        self.log(f"Always-listen enabled: {self.s.always_listen_enabled}")

    def toggle_recording(self):
        if self.listen.on:
            self.log("Manual recording is disabled while always-listen is running")
            return
        if self.rec.on:
            self.stop_recording()
        else:
            try:
                self.save_from_ui()
                self.rec.start()
                self.beep("start")
                self.refresh_status("Recording")
            except Exception as exc:
                self.beep("error")
                self.log(f"Failed to start recording: {exc}")
                messagebox.showerror(APP_NAME, str(exc))

    def stop_recording(self):
        audio = self.rec.stop()
        self.beep("stop")
        self.queue_audio(audio, "manual")
        self.refresh_status()

    def enqueue_audio(self, audio, source):
        self.res_q.put(("captured", {"audio": audio, "source": source}))

    def queue_audio(self, audio, source):
        duration = len(audio) / max(self.s.sample_rate, 1)
        if duration < self.s.min_record_seconds:
            self.log(f"Ignored {source} audio because it was too short")
            return
        if self.s.trim_silence and source != "always_listen":
            trimmed = trim_silence(audio, self.s.trim_threshold)
            if trimmed.size:
                audio = trimmed
        self.jobs.put((audio, source))
        queue_depth = self.jobs.qsize()
        if self.transcribing or queue_depth > 1:
            self.log(f"Queued {source} audio for background transcription ({queue_depth} waiting)")
        self.refresh_status("Queued")

    def _transcription_loop(self):
        while True:
            audio, source = self.jobs.get()
            started = time.perf_counter()
            path = None
            try:
                self.res_q.put(("started", {"source": source}))
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                    path = Path(handle.name)
                sf.write(path, audio, self.s.sample_rate)
                raw_text = self.backend.transcribe(path, self.s)
                raw_text = normalize_text(raw_text) if self.s.normalize_whitespace else raw_text
                self.res_q.put(
                    (
                        "done",
                        {
                            "text": raw_text,
                            "raw_text": raw_text,
                            "elapsed": time.perf_counter() - started,
                            "audio_seconds": len(audio) / self.s.sample_rate,
                            "source": source,
                        },
                    )
                )
            except Exception as exc:
                self.res_q.put(("error", {"source": source, "traceback": "".join(traceback.format_exception(exc))}))
            finally:
                if path is not None:
                    try:
                        path.unlink(missing_ok=True)
                    except Exception:
                        pass
                self.jobs.task_done()

    def warmup_model(self):
        started = time.perf_counter()
        path = None
        first_attempt = not bool(getattr(self.backend, "cache", {}))
        try:
            self.set_model_prepare_state("loading", first_attempt=first_attempt)
            self.backend._model(self.s)
            self.set_model_prepare_state("warming", log_message=False)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                path = Path(handle.name)
            sf.write(path, np.zeros(max(int(self.s.sample_rate * 0.35), 1), dtype=np.float32), self.s.sample_rate)
            self.backend.transcribe(path, self.s)
            self.set_model_prepare_state("ready", log_message=False)
            self.log(f"Model warmup finished in {time.perf_counter() - started:.2f}s")
        except Exception as exc:
            if path is None:
                self.set_model_prepare_state("load_failed", error=str(exc), log_message=False)
            else:
                self.set_model_prepare_state("warmup_failed", error=str(exc), log_message=False)
            self.log(f"Model warmup failed: {exc}")
        finally:
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
            self.refresh_quick_start()
            self.refresh_status()

    def show_doctor(self):
        self.last_doctor_report = doctor(self.s)
        self.log_text.insert("end", "\n" + self.last_doctor_report + "\n")
        self.log_text.see("end")

    def copy_doctor_report(self):
        self.last_doctor_report = doctor(self.s)
        self.copy_clip(self.last_doctor_report)
        self.log("Doctor report copied to clipboard")

    def _open_path(self, path: Path, *, fallback_to_parent: bool = False, label: str = "path") -> bool:
        target = path
        if fallback_to_parent and not target.exists():
            target = target.parent
        try:
            if os.name == "nt":
                os.startfile(str(target))
            elif target.is_dir():
                subprocess.Popen(["xdg-open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target.parent)])
            self.log(f"Opened {label}: {target}")
            return True
        except Exception as exc:
            self.log(f"Failed to open {label}: {exc}")
            messagebox.showerror(APP_NAME, f"{label} 열기에 실패했습니다.\n{exc}")
            return False

    def open_settings_path(self):
        return self._open_path(SETTINGS_PATH, fallback_to_parent=True, label="settings")

    def open_log_path(self):
        return self._open_path(LOG_PATH, fallback_to_parent=True, label="log")

    def open_data_root(self):
        return self._open_path(DATA_ROOT, fallback_to_parent=False, label="data root")

    def poll(self):
        try:
            while True:
                self.log_text.insert("end", self.log_q.get_nowait() + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        try:
            while True:
                kind, payload = self.res_q.get_nowait()
                if kind == "captured":
                    self.queue_audio(payload["audio"], payload["source"])
                elif kind == "started":
                    self.transcribing = True
                    self.active_transcription_source = payload["source"]
                    self.refresh_status("Transcribing")
                elif kind == "done":
                    self.transcribing = False
                    self.active_transcription_source = ""
                    self.refresh_status()
                    if not payload["text"]:
                        self.beep("error")
                        self.log(f"No speech detected from {payload['source']}")
                        continue
                    if self.is_voice_command_text(payload["text"]):
                        if self.handle_voice_command(payload["text"]):
                            self.beep("done")
                        else:
                            self.beep("error")
                        continue
                    self._update_latest_transcript(payload["text"])
                    append_history(
                        self.last,
                        {
                            "elapsed_seconds": round(float(payload["elapsed"]), 3),
                            "audio_seconds": round(float(payload["audio_seconds"]), 3),
                            "output_mode": self.s.output_mode,
                            "source": payload["source"],
                            "raw_text": payload.get("raw_text", ""),
                        },
                    )
                    self.refresh_history_browser()
                    self.emit_text(self.last)
                    self.beep("done")
                    self.log(f"Transcript ready from {payload['source']} in {float(payload['elapsed']):.2f}s for {float(payload['audio_seconds']):.2f}s audio")
                elif kind == "error":
                    self.transcribing = False
                    self.active_transcription_source = ""
                    self.refresh_status()
                    self.beep("error")
                    self.log(f"Transcription failed for {payload['source']}")
                    self.log(payload["traceback"])
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def poll_record(self):
        if self.rec.on:
            duration = self.rec.duration()
            self.refresh_status(f"Recording {duration:.1f}s")
            if duration >= self.s.max_record_seconds:
                self.log("Max recording length reached")
                self.stop_recording()
            elif self.rec.should_stop():
                self.log("Silence timeout reached")
                self.stop_recording()
        self.root.after(120, self.poll_record)

    def poll_diagnostics(self):
        self.refresh_audio_status()
        self.refresh_tuning_status()
        self.refresh_quick_start()
        self.root.after(120, self.poll_diagnostics)

    def poll_target(self):
        info = fg_info()
        active = is_target_window(info)
        context = target_context_key(info) if active else None
        state = self.output_state
        if state.pending_text and state.pending_context and context != state.pending_context:
            now = time.monotonic()
            if now >= state.output_grace_until:
                if not state.pending_context_mismatch_since:
                    state.pending_context_mismatch_since = now
                elif now - state.pending_context_mismatch_since >= 0.45:
                    self._clear_pending_state(clear_last_emitted=False, clear_last_submitted=False)
                    state.reset_context_mismatch()
                    self.log("Pending input cleared: focused input context changed")
            else:
                state.reset_context_mismatch()
        else:
            state.reset_context_mismatch()
        if active != self.last_target:
            self.last_target = active
            self.log("Target window active" if active else "Target window inactive")
        if active:
            self.last_target_window = info
        self.last_target_context = context
        self.root.after(150, self.poll_target)

    def close(self):
        if self.rec.on:
            try:
                self.rec.stop()
            except Exception:
                pass
        if self.listen.on:
            try:
                self.listen.stop()
            except Exception:
                pass
        try:
            import keyboard

            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.root.destroy()
