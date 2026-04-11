from __future__ import annotations

import sys

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
    if "실패" in model_detail or "건너뜀" in model_detail:
        failure_hints.append("모델 준비가 느리면 첫 다운로드 또는 warmup 로그를 확인")
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
