param(
    [string]$PythonPath = "",
    [switch]$SkipTests,
    [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"

function Find-PythonInAncestorVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StartDirectory
    )

    $current = (Resolve-Path $StartDirectory).Path
    while ($true) {
        $candidate = Join-Path $current ".venv\Scripts\python.exe"
        if (Test-Path $candidate) {
            return $candidate
        }

        $parent = Split-Path $current -Parent
        if (-not $parent -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    return $null
}

function Find-PythonInGitCommonDirVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StartDirectory
    )

    $gitCommonDir = $null
    try {
        $gitCommonDir = (& git -C $StartDirectory rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1).Trim()
    } catch {
        return $null
    }

    if (-not $gitCommonDir) {
        return $null
    }

    if (-not (Test-Path $gitCommonDir)) {
        return $null
    }

    $repoRoot = Split-Path $gitCommonDir -Parent
    if (-not $repoRoot) {
        return $null
    }

    $candidate = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path $candidate) {
        return $candidate
    }

    return $null
}

function Resolve-VoicepadPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptDirectory,
        [string]$ExplicitPythonPath = ""
    )

    if ($ExplicitPythonPath) {
        return (Resolve-Path $ExplicitPythonPath).Path
    }

    $python = Find-PythonInAncestorVenv -StartDirectory $ScriptDirectory
    if (-not $python) {
        $python = Find-PythonInGitCommonDirVenv -StartDirectory $ScriptDirectory
    }
    if (-not $python) {
        throw ".venv\\Scripts\\python.exe 를 찾지 못했습니다. 저장소 루트 또는 연결된 worktree의 원본 저장소에서 가상환경을 먼저 준비하거나 -PythonPath로 직접 지정해주세요."
    }
    return $python
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,
        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    Write-Host ""
    Write-Host "== $Name =="
    $output = & $Action 2>&1
    $outputText = ($output | Out-String).TrimEnd()
    if ($outputText) {
        $outputText | Tee-Object -FilePath $LogPath | Out-Host
    } else {
        "" | Set-Content -Encoding UTF8 $LogPath
    }

    if ($LASTEXITCODE -ne 0) {
        throw "$Name 단계가 실패했습니다. 로그: $LogPath"
    }

    return $outputText
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Resolve-VoicepadPython -ScriptDirectory $scriptDir -ExplicitPythonPath $PythonPath
$smokeRoot = Join-Path $scriptDir "outputs\release-smoke"
$localAppData = Join-Path $smokeRoot "localappdata"
$summaryPath = Join-Path $smokeRoot "summary.txt"

New-Item -ItemType Directory -Path $smokeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $localAppData -Force | Out-Null

$originalLocalAppData = $env:LOCALAPPDATA
$originalHfHome = $env:HF_HOME
$originalDisableXet = $env:HF_HUB_DISABLE_XET
$originalDisableTelemetry = $env:HF_HUB_DISABLE_TELEMETRY

try {
    $env:LOCALAPPDATA = $localAppData
    $env:HF_HOME = Join-Path $smokeRoot "huggingface"
    $env:HF_HUB_DISABLE_XET = "1"
    $env:HF_HUB_DISABLE_TELEMETRY = "1"

    $summaryLines = @(
        "Voicepad 릴리즈 전 스모크 테스트",
        "실행 시각: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")",
        "Python: $python",
        "LOCALAPPDATA: $localAppData"
    )

    if (-not $SkipTests) {
        Invoke-Step -Name "unittest" -Action { & $python -m unittest discover -s tests -v } -LogPath (Join-Path $smokeRoot "unittest.txt") | Out-Null
        $summaryLines += "unittest: OK"
    } else {
        $summaryLines += "unittest: skipped"
    }

    $versionOutput = Invoke-Step -Name "--version" -Action { & $python (Join-Path $scriptDir "codex_dictation.py") --version } -LogPath (Join-Path $smokeRoot "version.txt")
    $summaryLines += "--version: $versionOutput"

    Invoke-Step -Name "--doctor" -Action { & $python (Join-Path $scriptDir "codex_dictation.py") --doctor } -LogPath (Join-Path $smokeRoot "doctor.txt") | Out-Null
    $summaryLines += "--doctor: OK"

    if (-not $SkipPackage) {
        Invoke-Step -Name "release package" -Action { & (Join-Path $scriptDir "package_codex_dictation_release.ps1") -PythonPath $python } -LogPath (Join-Path $smokeRoot "package.txt") | Out-Null
        $summaryLines += "package: OK"
    } else {
        $summaryLines += "package: skipped"
    }

    $summaryLines += "로그 폴더: $smokeRoot"
    $summaryLines -join "`r`n" | Set-Content -Encoding UTF8 $summaryPath

    Write-Host ""
    Write-Host "릴리즈 전 스모크 테스트 완료"
    Write-Host " - 요약: $summaryPath"
    Write-Host " - 로그: $smokeRoot"
} finally {
    $env:LOCALAPPDATA = $originalLocalAppData
    $env:HF_HOME = $originalHfHome
    $env:HF_HUB_DISABLE_XET = $originalDisableXet
    $env:HF_HUB_DISABLE_TELEMETRY = $originalDisableTelemetry
}
