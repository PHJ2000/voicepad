# GitHub Releases 배포 절차

`voicepad`는 Windows용 배포 패키지를 GitHub Releases에 올리는 흐름을 기본 배포 기준으로 사용합니다. 이 문서는 태그 규칙, 자산 이름, 릴리즈 노트 형식, 업로드 전 체크리스트를 한 번에 정리한 기준 문서입니다.

## 문서 역할

- 이 문서: 실제 릴리즈를 만들 때 어떤 순서로 확인하고 배포할지 정리
- [beta-release-gate.md](./beta-release-gate.md): beta 종료와 정식 릴리즈 가능 여부를 판단하는 기준 정리
- [README.md](../README.md): 사용자 설치, 실행, 첫 점검, 문제 해결 안내

## 릴리즈 운영 흐름

Voicepad 릴리즈는 기본적으로 아래 흐름을 따릅니다.

1. `beta` 검증
2. `pre-release` 배포
3. 피드백 반영
4. 정식 release 판단

정식 release 후보를 올릴 때는 이 문서의 배포 절차뿐 아니라 [beta-release-gate.md](./beta-release-gate.md)의 체크리스트를 함께 확인합니다.

## 기준 버전과 태그 규칙

- 앱 버전의 기준값은 [codex_dictation_settings.py](../codex_dictation_settings.py)의 `APP_VERSION`입니다.
- 코드 안 버전 문자열은 `0.1.0-beta.1`처럼 `v` 없는 SemVer 성격 표기를 사용합니다.
- Git 태그와 GitHub Release 태그는 항상 `v{APP_VERSION}` 형식을 사용합니다.
  - 예: `APP_VERSION = "0.1.0-beta.1"`이면 태그는 `v0.1.0-beta.1`
- 베타나 RC처럼 접미사가 붙은 버전은 GitHub Release 생성 시 `This is a pre-release`를 켭니다.
- 정식 버전은 접미사 없는 `x.y.z` 형식을 사용하고, GitHub Release도 일반 릴리즈로 발행합니다.

## prerelease 운영 원칙

- 제목이나 태그에 `beta`를 명시합니다.
- 알려진 제한사항이 있으면 릴리즈 노트 첫 부분에 바로 적습니다.
- 피드백 수집 대상은 설치, 첫 실행, 장치 인식, 타겟 앱별 입력 안정성입니다.
- 치명도가 높은 회귀가 확인되면 다음 beta를 먼저 내고 정식 release는 미룹니다.

## 릴리즈 자산 기준

현재 기본 자산은 아래 하나를 기준으로 둡니다.

- `Voicepad-win64.zip`

이 zip 안에는 최소 아래 구조가 들어 있어야 합니다.

```text
dist\Voicepad.exe
LICENSE
README.md
codex_dictation.settings.example.json
launch_codex_dictation.ahk
run_codex_dictation.bat
run_codex_hotkeys.bat
run_codex_terminal.bat
tools\AutoHotkey\
```

주의:

- 개인 설정 파일, 실제 로그, 기록 파일은 자산에 포함하지 않습니다.
- 자산 이름은 현재 패키징 스크립트 출력과 맞추기 위해 `Voicepad-win64.zip`을 유지합니다.
- 추가 자산이 생기더라도 `Voicepad-` 접두사를 유지하고, 사용 목적이 바로 드러나는 이름을 붙입니다.

## 릴리즈 전 준비 순서

1. `main` 기준으로 릴리즈 대상 커밋이 정리되었는지 확인합니다.
2. `APP_VERSION`과 문서 표기가 이번 릴리즈 버전과 맞는지 확인합니다.
3. 아래 기본 검증을 다시 실행합니다.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe .\codex_dictation.py --version
.venv\Scripts\python.exe .\codex_dictation.py --doctor
.\package_codex_dictation_release.ps1
```

4. `release\Voicepad-win64\` 폴더와 `release\Voicepad-win64.zip`이 정상 생성되었는지 확인합니다.
5. zip 안에 예시 설정 파일만 들어 있고, 개인 데이터가 섞이지 않았는지 확인합니다.
6. 정식 release 후보라면 [beta-release-gate.md](./beta-release-gate.md)의 `정식 릴리즈 게이트`를 다시 확인합니다.

## GitHub Release 생성 순서

1. GitHub의 `Releases` 화면에서 `Draft a new release`를 엽니다.
2. 태그는 `v{APP_VERSION}` 형식으로 입력합니다.
3. 릴리즈 제목은 `Voicepad v{APP_VERSION}` 형식을 기본으로 사용합니다.
   - 예: `Voicepad v0.1.0-beta.1`
4. 베타/RC 릴리즈면 `pre-release`를 켭니다.
5. 본문은 [release-notes-template.md](./release-notes-template.md)를 복사해 채웁니다.
6. 자산에는 `release\Voicepad-win64.zip`을 업로드합니다.
7. 마지막 체크리스트를 다시 보고 발행합니다.

## 릴리즈 노트 형식

릴리즈 노트는 아래 네 덩어리를 유지하는 것을 기본으로 합니다.

1. `요약`
   - 이번 릴리즈를 한두 문장으로 설명
2. `주요 변경`
   - 사용자 체감이 큰 변화 위주로 3~5개
3. `검증`
   - 실행한 테스트나 수동 확인 범위
4. `알려진 메모`
   - 첫 실행 다운로드, 제약사항, 남아 있는 주의점

링크가 필요하면 마지막에 관련 이슈나 PR을 붙여도 됩니다.

## 업로드 전 체크리스트

- [ ] `APP_VERSION`과 태그 이름이 일치한다.
- [ ] 릴리즈 제목이 `Voicepad v{APP_VERSION}` 형식이다.
- [ ] 베타/RC 여부에 맞게 `pre-release` 설정이 맞다.
- [ ] `Voicepad-win64.zip`이 최신 빌드 결과물이다.
- [ ] zip 안에 `Voicepad.exe`, 런처 배치 파일, `tools\AutoHotkey`, `README.md`, `LICENSE`가 있다.
- [ ] 개인 설정 파일, 로그, 기록 파일이 포함되지 않았다.
- [ ] 릴리즈 노트에 요약, 주요 변경, 검증, 알려진 메모가 들어 있다.
- [ ] 첫 실행 시 모델 다운로드 가능성과 Windows 전용 제약을 필요한 범위에서 적었다.

## 메모

- 릴리즈 노트는 자동 생성에 전부 맡기기보다, 사용자 관점에서 읽히는 요약을 직접 적는 쪽을 우선합니다.
- 정식 릴리즈 전까지는 베타 버전 흐름을 유지하고, 위험한 변화가 있으면 `알려진 메모`에 분명히 적습니다.
- 공유용 로그 수집 경로와 문제 해결 링크를 릴리즈 노트에도 함께 적어 두는 편이 좋습니다.
