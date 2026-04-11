from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import can_import_module


# Windows에서 tzdata는 선택 의존성이다.
# 설치돼 있을 때만 포함해서 불필요한 warning을 없앤다.
if is_win and can_import_module("tzdata"):
    hiddenimports = ["tzdata"]
