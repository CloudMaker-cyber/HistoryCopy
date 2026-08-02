@echo off
REM 打包脚本:生成图标并用 PyInstaller 打成单个 exe
cd /d "%~dp0"

echo [1/2] 生成图标 icon.ico ...
python src\build_icon.py
if errorlevel 1 goto :err

echo [2/2] PyInstaller 打包(可能需要几分钟)...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name HistoryCopy --icon icon.ico ^
  --paths src ^
  --hidden-import app ^
  --hidden-import recorder ^
  --hidden-import clipboard_monitor ^
  --hidden-import storage ^
  --hidden-import settings ^
  --hidden-import autostart ^
  --hidden-import cleanup ^
  --hidden-import ui.theme ^
  --hidden-import ui.icon ^
  --hidden-import ui.card ^
  --hidden-import ui.preview ^
  --hidden-import ui.main_window ^
  --hidden-import ui.settings_dialog ^
  src\main.py
if errorlevel 1 goto :err

echo.
echo 打包完成!exe 位置: dist\HistoryCopy.exe
echo 使用方法见 docs\usage.md
pause
exit /b 0

:err
echo 打包失败,请检查上方报错信息。
pause
exit /b 1
