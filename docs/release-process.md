# 릴리즈 절차

Voicepad 릴리즈는 `beta 검증 -> prerelease 배포 -> 피드백 반영 -> 정식 release` 흐름을 기본으로 합니다.
이 문서는 실제 배포 순서를 빠르게 확인할 수 있는 운영 메모이고, beta 종료 판단 기준은 [beta-release-gate.md](./beta-release-gate.md)에서 따로 관리합니다.

## 문서 역할

- 이 문서: 릴리즈를 만들 때 어떤 순서로 확인하고 배포할지 정리
- [beta-release-gate.md](./beta-release-gate.md): beta를 끝내고 정식 릴리즈로 넘어가도 되는지 판단하는 기준 정리
- [README.md](../README.md): 사용자 설치, 실행, 첫 점검, 문제 해결 안내

## 릴리즈 전 기본 흐름

1. `main` 기준으로 릴리즈 후보를 확정합니다.
2. `run_release_smoke.ps1`로 기본 검증을 실행합니다.
3. 변경점이 사용자 안내에 영향을 주면 `README.md`를 먼저 갱신합니다.
4. beta 상태라면 prerelease 자산만 올리고 실제 사용자 피드백을 받습니다.
5. 정식 release 후보라면 [beta-release-gate.md](./beta-release-gate.md)의 체크리스트를 모두 다시 확인합니다.
6. `Voicepad-win64.zip`을 GitHub Releases 자산으로 업로드합니다.
7. 릴리즈 노트에는 새 기능보다 설치/호환성/주의사항을 먼저 적습니다.

## prerelease 운영 원칙

- 제목이나 태그에 `beta`를 명시합니다.
- 알려진 제한사항이 있으면 릴리즈 노트 첫 부분에 바로 적습니다.
- 피드백 수집 대상은 설치, 첫 실행, 장치 인식, 타겟 앱별 입력 안정성입니다.
- 치명도가 높은 회귀가 확인되면 다음 beta를 먼저 내고 정식 release는 미룹니다.

## 정식 release 직전 확인

- [beta-release-gate.md](./beta-release-gate.md)의 `정식 릴리즈 게이트`가 모두 충족되었는지 확인합니다.
- `README.md`만 보고도 설치와 첫 실행이 가능해야 합니다.
- 공유용 로그 수집 경로와 문제 해결 링크를 릴리즈 노트에 적습니다.
- 릴리즈 자산 이름과 문서 표기가 서로 일치해야 합니다.

## 배포 자산 기준

- 기본 자산: `Voicepad-win64.zip`
- 포함 파일:
  - `dist\Voicepad.exe`
  - `run_codex_dictation.bat`
  - `run_codex_hotkeys.bat`
  - `run_codex_terminal.bat`
  - `launch_codex_dictation.ahk`
  - `tools\AutoHotkey\`
  - `README.md`
  - `LICENSE`
  - `codex_dictation.settings.example.json`

## 릴리즈 노트 최소 항목

- 이번 버전의 핵심 변화 2~5개
- 새 사용자 기준 설치/실행 시 주의할 점
- 알려진 제한사항
- 로그 공유 또는 문제 제보 방법

## 참고

- beta 종료 기준: [beta-release-gate.md](./beta-release-gate.md)
- 사용자 설치/실행 안내: [README.md](../README.md)
