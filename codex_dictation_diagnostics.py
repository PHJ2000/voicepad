from __future__ import annotations

import json
import os
import sys
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from codex_dictation_audio import get_input_devices
from codex_dictation_settings import (
    APP_NAME,
    APP_VERSION,
    DATA_ROOT,
    HISTORY_PATH,
    LEGACY_HISTORY_PATH,
    LEGACY_LOG_PATH,
    LEGACY_ROOT,
    LEGACY_SETTINGS_PATH,
    LOG_PATH,
    SETTINGS_PATH,
    Settings,
    audio_preset_label,
    display_path,
    language_label,
    llm_profile_label,
    normalize_audio_preset_value,
    normalize_language_value,
    normalize_llm_profile_value,
    resolve_llm_model,
)
from codex_dictation_targeting import (
    fg_info,
    fmt_info,
    gui_focus_info,
    is_codex_terminal,
    is_general_input_target,
    is_target_window,
    is_terminal,
)


DIAGNOSTIC_BUNDLE_DIR = DATA_ROOT / "diagnostic-bundles"


def first_run_guidance(
    settings: Settings,
    *,
    input_device_count: int | None,
    model_status: str = "",
    hotkey_status: str = "",
) -> tuple[str, str, str, str]:
    if input_device_count is None:
        microphone_status = "마이크 감지 확인 전"
    elif input_device_count <= 0:
        microphone_status = "마이크 확인 필요"
    else:
        microphone_status = f"마이크 {input_device_count}개 감지"

    configured_input = settings.input_device.strip() or "자동 선택"
    model_detail = model_status or f"모델 {settings.whisper_model} 준비 중"
    hotkey_detail = hotkey_status or "단축키 등록 대기"
    summary = f"빠른 점검 | {microphone_status} | {model_detail} | {hotkey_detail}"
    checklist = (
        f"입력 장치: {configured_input} | "
        "1. Input Device 확인  2. F8 또는 F7로 짧게 말해보기  3. 결과가 없으면 Doctor 실행"
    )
    paths = (
        f"설정 {display_path(SETTINGS_PATH)} | "
        f"로그 {display_path(LOG_PATH)} | "
        f"데이터 {display_path(DATA_ROOT, base=DATA_ROOT.parent)}"
    )

    failure_hints: list[str] = []
    if input_device_count is not None and input_device_count <= 0:
        failure_hints.append("마이크가 안 보이면 장치 연결 후 Doctor의 Input devices를 확인")
    if "다운로드/로드 중" in model_detail:
        failure_hints.append("첫 실행이면 모델 다운로드가 길 수 있으니 로그가 계속 갱신되는지 확인")
    if "워밍업 중" in model_detail:
        failure_hints.append("모델 워밍업 중에는 첫 응답이 잠시 느릴 수 있습니다")
    if "실패" in model_detail or "건너뜀" in model_detail:
        failure_hints.append("모델 준비가 느리면 첫 다운로드 또는 warmup 로그를 확인")
        failure_hints.append("모델 준비에 실패하면 로그와 네트워크 또는 저장공간 상태를 함께 확인")
    if "실패" in hotkey_detail or "불가" in hotkey_detail:
        failure_hints.append("단축키가 안 먹으면 keyboard 모듈과 실행 권한을 확인")
    if not failure_hints:
        failure_hints.append("문제가 생기면 Doctor -> 로그 -> 설정 순서로 확인")
    trouble = "대표 실패: " + " | ".join(failure_hints)
    return summary, checklist, paths, trouble


def doctor(settings: Settings | None = None) -> str:
    lines = [
        f"{APP_NAME} doctor",
        "-" * 40,
        f"Version: {APP_VERSION}",
        f"Python: {sys.version.split()[0]}",
        f"Data root: {display_path(DATA_ROOT, base=DATA_ROOT.parent)}",
        f"Settings: {display_path(SETTINGS_PATH)}",
        f"History: {display_path(HISTORY_PATH)}",
        f"Log: {display_path(LOG_PATH)}",
    ]
    legacy_files = [
        name
        for name, path in (
            ("settings", LEGACY_SETTINGS_PATH),
            ("history", LEGACY_HISTORY_PATH),
            ("log", LEGACY_LOG_PATH),
        )
        if path.exists()
    ]
    if legacy_files:
        lines.append(f"Legacy runtime files: {display_path(LEGACY_ROOT, base=LEGACY_ROOT.parent)} ({', '.join(legacy_files)})")
    if settings:
        lines += [
            f"Always listen enabled: {settings.always_listen_enabled}",
            f"Audio preset: {audio_preset_label(settings.audio_preset)} ({normalize_audio_preset_value(settings.audio_preset)})",
            f"Input gain: {float(settings.input_gain):.2f}",
            f"Noise gate threshold: {float(settings.noise_gate_threshold):.4f}",
            f"Language: {language_label(settings.language)} ({normalize_language_value(settings.language)})",
            f"LLM correction enabled: {settings.llm_correction_enabled}",
            f"LLM profile: {llm_profile_label(settings.llm_profile)} ({normalize_llm_profile_value(settings.llm_profile)})",
            f"LLM model: {resolve_llm_model(settings)}",
            f"LLM base URL: {settings.llm_base_url}",
        ]
    try:
        devices = get_input_devices()
        lines.append(f"Input devices: {len(devices)}")
        for device in devices[:10]:
            lines.append(f"  - [{device['index']}] {device['name']} ({device['sample_rate']} Hz)")
    except Exception as exc:
        lines.append(f"Input devices: failed ({exc})")
    info = fg_info()
    focus = gui_focus_info(info)
    lines += [
        f"Foreground window: {fmt_info(info)}",
        f"Focused child hwnd: {getattr(focus, 'focus_hwnd', 0)} | class={getattr(focus, 'focus_cls', '') or 'none'}",
        f"Caret hwnd: {getattr(focus, 'caret_hwnd', 0)} | class={getattr(focus, 'caret_cls', '') or 'none'} | visible={getattr(focus, 'caret_visible', False)}",
        f"Looks like terminal: {is_terminal(info)}",
        f"Looks like Codex terminal: {is_codex_terminal(info)}",
        f"Looks like general input target: {is_general_input_target(info)}",
        f"Accepts as target window: {is_target_window(info)}",
    ]
    for name, module_name in [("keyboard", "keyboard"), ("faster-whisper", "faster_whisper"), ("psutil", "psutil")]:
        try:
            __import__(module_name)
            lines.append(f"{name}: OK")
        except Exception as exc:
            lines.append(f"{name}: missing ({exc})")
    try:
        import torch

        lines += [f"torch: {torch.__version__}", f"torch cuda available: {torch.cuda.is_available()}"]
        if torch.cuda.is_available():
            lines.append(f"torch cuda device: {torch.cuda.get_device_name(0)}")
    except Exception as exc:
        lines.append(f"torch: unavailable ({exc})")
    return "\n".join(lines)


def mask_diagnostic_text(
    text: str,
    *,
    data_root: Path = DATA_ROOT,
    settings_path: Path = SETTINGS_PATH,
    history_path: Path = HISTORY_PATH,
    log_path: Path = LOG_PATH,
) -> str:
    masked = text or ""

    def _path_variants(path: Path | str) -> set[str]:
        raw = str(path)
        variants = {
            raw,
            os.path.normpath(raw),
            os.path.realpath(raw),
        }
        try:
            variants.add(str(Path(path).resolve()))
        except Exception:
            pass
        expanded: set[str] = set()
        for item in variants:
            expanded.add(item)
            expanded.add(item.replace("\\", "/"))
        return {item for item in expanded if item}

    replacements: dict[str, str] = {}
    for raw in _path_variants(Path.home()):
        replacements[raw] = "<USER_HOME>"
    for raw in _path_variants(data_root):
        replacements[raw] = "<DATA_ROOT>"
    for raw in _path_variants(settings_path):
        replacements[raw] = "<DATA_ROOT>/codex_dictation.settings.json"
    for raw in _path_variants(history_path):
        replacements[raw] = "<DATA_ROOT>/codex_dictation.history.jsonl"
    for raw in _path_variants(log_path):
        replacements[raw] = "<DATA_ROOT>/codex_dictation.log"
    env_home = os.environ.get("USERPROFILE", "").strip() or os.environ.get("HOME", "").strip()
    if env_home:
        replacements[env_home] = "<USER_HOME>"
    for raw, token in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if not raw:
            continue
        masked = masked.replace(raw, token)
    return masked


def diagnostic_bundle_readme(exported_at: str) -> str:
    return "\n".join(
        [
            "Voicepad 진단 번들",
            "--------------------",
            f"생성 시각: {exported_at}",
            "",
            "포함 파일:",
            "- doctor.txt: 현재 환경 점검 결과",
            "- settings.json: 민감값을 일부 마스킹한 설정 스냅샷",
            "- recent-log.txt: 최근 로그 일부",
            "",
            "마스킹 기준:",
            "- 사용자 홈 경로는 <USER_HOME> 으로 치환",
            "- Voicepad 데이터 루트와 대표 파일 경로는 <DATA_ROOT> 기준으로 치환",
            "- Initial Prompt 값은 실제 문장 대신 <configured> 로 치환",
        ]
    )


def diagnostic_settings_snapshot(settings: Settings, *, exported_at: str) -> str:
    payload = asdict(settings)
    if (payload.get("initial_prompt") or "").strip():
        payload["initial_prompt"] = "<configured>"
    return json.dumps(
        {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "exported_at": exported_at,
            "masked": True,
            "settings": payload,
        },
        ensure_ascii=False,
        indent=2,
    )


def read_recent_log(log_path: Path = LOG_PATH, *, max_lines: int = 200) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return "로그 파일이 아직 없습니다."
    except Exception as exc:
        return f"로그를 읽지 못했습니다: {exc}"
    if not lines:
        return "로그 파일이 비어 있습니다."
    return "\n".join(lines[-max_lines:])


def create_diagnostic_bundle(
    settings: Settings,
    *,
    doctor_report: str | None = None,
    bundle_root: Path = DIAGNOSTIC_BUNDLE_DIR,
    log_path: Path = LOG_PATH,
    max_log_lines: int = 200,
    now: datetime | None = None,
) -> Path:
    exported_at = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target_root = Path(bundle_root)
    target_root.mkdir(parents=True, exist_ok=True)
    bundle_path = target_root / f"voicepad-diagnostics-{stamp}.zip"

    doctor_text = mask_diagnostic_text(doctor_report or doctor(settings))
    settings_text = diagnostic_settings_snapshot(settings, exported_at=exported_at)
    log_text = mask_diagnostic_text(read_recent_log(log_path, max_lines=max_log_lines))
    readme_text = diagnostic_bundle_readme(exported_at)

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", readme_text)
        archive.writestr("doctor.txt", doctor_text)
        archive.writestr("settings.json", settings_text)
        archive.writestr("recent-log.txt", log_text)
    return bundle_path
