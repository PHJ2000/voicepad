#Requires AutoHotkey v2.0
#SingleInstance Force
#UseHook True
InstallKeybdHook
DetectHiddenWindows True
SetTitleMatchMode 2

projectDir := A_ScriptDir
dictationTitle := "Voicepad"
dictationLauncher := projectDir "\run_codex_dictation.bat"
dictationScript := projectDir "\codex_dictation.py"
dictationExe := projectDir "\dist\Voicepad.exe"
launcherHotkeyDefaults := Map(
    "launcher_toggle_hotkey", "f1",
    "launcher_show_hotkey", "f2",
    "launcher_hide_hotkey", "f3",
    "launcher_exit_hotkey", "f4"
)
launcherHotkeys := Map()
registeredLauncherHotkeys := Map()
launcherConfigSignature := ""

LoadLauncherHotkeys(settingsText := "")
{
    global launcherHotkeyDefaults

    if settingsText = ""
        settingsText := ReadLauncherSettingsText()
    resolved := Map()
    usedHotkeys := Map()
    for field, defaultValue in launcherHotkeyDefaults
    {
        candidate := NormalizeLauncherHotkeyValue(ExtractLauncherSetting(settingsText, field), defaultValue)
        if !candidate || usedHotkeys.Has(candidate)
            candidate := ResolveLauncherHotkeyFallback(defaultValue, usedHotkeys)
        resolved[field] := candidate
        usedHotkeys[candidate] := field
    }
    return resolved
}

ReadLauncherSettingsText()
{
    global projectDir

    localAppData := Trim(EnvGet("LOCALAPPDATA"))
    candidates := Array()
    if localAppData
    {
        candidates.Push(localAppData "\Voicepad\codex_dictation.settings.json")
        candidates.Push(localAppData "\CodexDictation\codex_dictation.settings.json")
    }
    candidates.Push(projectDir "\codex_dictation.settings.json")

    for candidate in candidates
    {
        if FileExist(candidate)
        {
            try return FileRead(candidate, "UTF-8")
        }
    }
    return ""
}

ExtractLauncherSetting(settingsText, fieldName)
{
    if !settingsText
        return ""
    pattern := '"' fieldName '"\s*:\s*"((?:\\.|[^"])*)"'
    if !RegExMatch(settingsText, pattern, &match)
        return ""
    return StrReplace(match[1], '\"', '"')
}

NormalizeLauncherHotkeyValue(value, fallback := "")
{
    normalized := NormalizeLauncherHotkeyCore(value)
    if normalized
        return normalized
    return NormalizeLauncherHotkeyCore(fallback)
}

NormalizeLauncherHotkeyCore(value)
{
    raw := StrLower(Trim(value))
    if !raw
        return ""

    modifiers := Array()
    primary := ""
    tokens := Array()
    if RegExMatch(raw, "^[\^\!\#\+]+[^+]+$")
    {
        pos := 1
        while (pos <= StrLen(raw))
        {
            char := SubStr(raw, pos, 1)
            normalizedModifier := NormalizeLauncherHotkeyToken(char)
            if !normalizedModifier
                break
            tokens.Push(normalizedModifier)
            pos += 1
        }
        keyToken := Trim(SubStr(raw, pos))
        if keyToken
            tokens.Push(keyToken)
    }
    else
    {
        normalizedSeparators := RegExReplace(raw, "\s*\+\s*", "+")
        for token in StrSplit(normalizedSeparators, "+")
        {
            trimmed := Trim(token)
            if trimmed
                tokens.Push(trimmed)
        }
    }

    if !tokens.Length
        return ""

    for token in tokens
    {
        normalized := NormalizeLauncherHotkeyToken(token)
        if !normalized
            continue
        if normalized = "ctrl" || normalized = "alt" || normalized = "shift" || normalized = "win"
        {
            if !ArrayHasValue(modifiers, normalized)
                modifiers.Push(normalized)
            continue
        }
        if primary
            return ""
        primary := normalized
    }

    if !primary
        return ""

    ordered := Array()
    for modifier in ["ctrl", "alt", "shift", "win"]
    {
        if ArrayHasValue(modifiers, modifier)
            ordered.Push(modifier)
    }
    ordered.Push(primary)
    return JoinHotkeyTokens(ordered)
}

NormalizeLauncherHotkeyToken(token)
{
    normalized := StrLower(Trim(token))
    compact := StrReplace(normalized, " ", "")
    static aliases := Map(
        "^", "ctrl",
        "ctrl", "ctrl",
        "control", "ctrl",
        "!", "alt",
        "alt", "alt",
        "option", "alt",
        "+", "shift",
        "shift", "shift",
        "#", "win",
        "win", "win",
        "windows", "win",
        "meta", "win",
        "command", "win",
        "cmd", "win",
        "esc", "escape",
        "return", "enter",
        "del", "delete",
        "ins", "insert",
        "pgup", "pageup",
        "pgdn", "pagedown",
        "spacebar", "space"
    )
    if aliases.Has(compact)
        return aliases[compact]
    return compact
}

ResolveLauncherHotkeyFallback(defaultValue, usedHotkeys)
{
    global launcherHotkeyDefaults

    normalizedDefault := NormalizeLauncherHotkeyValue(defaultValue)
    if normalizedDefault && !usedHotkeys.Has(normalizedDefault)
        return normalizedDefault

    for _, candidate in launcherHotkeyDefaults
    {
        normalizedCandidate := NormalizeLauncherHotkeyValue(candidate)
        if normalizedCandidate && !usedHotkeys.Has(normalizedCandidate)
            return normalizedCandidate
    }
    return normalizedDefault
}

ArrayHasValue(items, expected)
{
    for item in items
    {
        if item = expected
            return true
    }
    return false
}

JoinHotkeyTokens(tokens)
{
    joined := ""
    for index, token in tokens
    {
        if index > 1
            joined .= "+"
        joined .= token
    }
    return joined
}

CanonicalHotkeyToAhk(value)
{
    modifiers := ""
    key := ""
    for token in StrSplit(value, "+")
    {
        if token = "ctrl"
        {
            modifiers .= "^"
            continue
        }
        if token = "alt"
        {
            modifiers .= "!"
            continue
        }
        if token = "shift"
        {
            modifiers .= "+"
            continue
        }
        if token = "win"
        {
            modifiers .= "#"
            continue
        }
        key := token
    }
    return modifiers . key
}

RegisterLauncherHotkeys()
{
    global launcherHotkeys, registeredLauncherHotkeys

    UnregisterLauncherHotkeys()
    registeredLauncherHotkeys := Map()
    registeredLauncherHotkeys["launcher_toggle_hotkey"] := "$" . CanonicalHotkeyToAhk(launcherHotkeys["launcher_toggle_hotkey"])
    Hotkey registeredLauncherHotkeys["launcher_toggle_hotkey"], HandleLauncherToggle
    registeredLauncherHotkeys["launcher_show_hotkey"] := "$" . CanonicalHotkeyToAhk(launcherHotkeys["launcher_show_hotkey"])
    Hotkey registeredLauncherHotkeys["launcher_show_hotkey"], HandleLauncherShow
    registeredLauncherHotkeys["launcher_hide_hotkey"] := "$" . CanonicalHotkeyToAhk(launcherHotkeys["launcher_hide_hotkey"])
    Hotkey registeredLauncherHotkeys["launcher_hide_hotkey"], HandleLauncherHide
    registeredLauncherHotkeys["launcher_exit_hotkey"] := "$" . CanonicalHotkeyToAhk(launcherHotkeys["launcher_exit_hotkey"])
    Hotkey registeredLauncherHotkeys["launcher_exit_hotkey"], HandleLauncherExit
}

UnregisterLauncherHotkeys()
{
    global registeredLauncherHotkeys

    for _, hotkeySpec in registeredLauncherHotkeys
    {
        try Hotkey hotkeySpec, "Off"
    }
}

RefreshLauncherHotkeys(*)
{
    global launcherConfigSignature, launcherHotkeys

    settingsText := ReadLauncherSettingsText()
    nextSignature := settingsText ? settingsText : "__defaults__"
    if nextSignature = launcherConfigSignature
        return
    launcherConfigSignature := nextSignature
    launcherHotkeys := LoadLauncherHotkeys(settingsText)
    RegisterLauncherHotkeys()
}

HandleLauncherToggle(*)
{
    StartOrMinimizeDictation()
}

HandleLauncherShow(*)
{
    global dictationTitle

    if WinExist(dictationTitle)
    {
        WinShow dictationTitle
        try WinRestore(dictationTitle)
        WinActivate dictationTitle
        return
    }

    StartDictation(true)
    if WinWait(dictationTitle, , 8)
    {
        WinShow dictationTitle
        try WinRestore(dictationTitle)
        WinActivate dictationTitle
    }
}

HandleLauncherHide(*)
{
    global dictationTitle

    if WinExist(dictationTitle)
        WinMinimize dictationTitle
}

HandleLauncherExit(*)
{
    global dictationTitle

    if WinExist(dictationTitle)
        WinClose dictationTitle
}

StartDictation(showWindow := false)
{
    global dictationLauncher, projectDir

    args := showWindow ? " --show-window" : ""
    Run Format('"{1}"{2}', dictationLauncher, args), projectDir
}

CanRestoreWindow(hwnd)
{
    global dictationTitle

    if !hwnd
        return false
    try
    {
        if !WinExist("ahk_id " hwnd)
            return false
        if WinGetTitle("ahk_id " hwnd) == dictationTitle
            return false
        return true
    }
    catch
    {
        return false
    }
}

IsDictationProcessRunning()
{
    global dictationScript, dictationExe
    escapedScript := StrReplace(dictationScript, "\", "\\")
    escapedExe := StrReplace(dictationExe, "\", "\\")
    query := "Select ProcessId from Win32_Process where Name='pythonw.exe' or Name='python.exe' or Name='Voicepad.exe' or Name='CodexDictation.exe'"
    for proc in ComObjGet("winmgmts:").ExecQuery(query)
    {
        cmd := ""
        try cmd := proc.CommandLine
        exePath := ""
        try exePath := proc.ExecutablePath
        if InStr(StrLower(cmd), StrLower(escapedScript)) || InStr(StrLower(cmd), StrLower(dictationScript))
            return true
        if InStr(StrLower(cmd), StrLower(escapedExe)) || InStr(StrLower(cmd), StrLower(dictationExe))
            return true
        if InStr(StrLower(exePath), StrLower(escapedExe)) || InStr(StrLower(exePath), StrLower(dictationExe))
            return true
    }
    return false
}

RestorePreviousWindow(hwnd)
{
    if !CanRestoreWindow(hwnd)
        return false

    try WinShow("ahk_id " hwnd)
    state := 0
    try state := WinGetMinMax("ahk_id " hwnd)
    if (state = -1)
        try WinRestore("ahk_id " hwnd)
    try WinActivate("ahk_id " hwnd)
    return true
}

StartOrMinimizeDictation()
{
    global dictationTitle, dictationLauncher, projectDir
    previousHwnd := WinExist("A")

    if WinExist(dictationTitle)
    {
        WinMinimize dictationTitle
        RestorePreviousWindow(previousHwnd)
        return
    }

    if IsDictationProcessRunning()
    {
        RestorePreviousWindow(previousHwnd)
        return
    }

    if !FileExist(dictationLauncher)
    {
        MsgBox "Voicepad launcher not found.", "Voicepad", "Icon!"
        return
    }

    StartDictation(false)
    if WinWait(dictationTitle, , 8)
    {
        Sleep 800
        WinMinimize dictationTitle
    }
    RestorePreviousWindow(previousHwnd)
}

EnsureDictationRunning()
{
    global dictationTitle
    if !WinExist(dictationTitle) && !IsDictationProcessRunning()
        StartDictation(false)
}

RefreshLauncherHotkeys()
SetTimer EnsureDictationRunning, 5000
SetTimer RefreshLauncherHotkeys, 1500
