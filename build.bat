@echo off
REM 打包脚本:生成图标并用 PyInstaller 按 HistoryCopy.spec 打包(含 OCR 模型)
cd /d "%~dp0"

echo [1/2] 生成图标 icon.ico ...
python src\build_icon.py
if errorlevel 1 goto :err

echo [2/2] PyInstaller 打包(可能需要几分钟)...
python -m PyInstaller --noconfirm HistoryCopy.spec
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