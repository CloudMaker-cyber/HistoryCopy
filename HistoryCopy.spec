# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 只收集 rapidocr 的数据(模型 .onnx / config.yaml 等),避免其可选依赖(如 matplotlib)
# 拖入多余的 Qt 绑定导致与 PySide6 冲突。
datas = collect_data_files('rapidocr')
hiddenimports = ['onnxruntime'] + collect_submodules('rapidocr.inference_engine.onnxruntime')

a = Analysis(
    ['src\\main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=['app', 'recorder', 'clipboard_monitor', 'storage', 'settings', 'autostart', 'cleanup', 'ocr', 'ui.theme', 'ui.icon', 'ui.card', 'ui.preview', 'ui.ocr_dialog', 'ui.main_window', 'ui.settings_dialog'] + hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'PyQt5', 'PyQt6', 'PySide2', 'pandas', 'scipy', 'sklearn'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HistoryCopy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
