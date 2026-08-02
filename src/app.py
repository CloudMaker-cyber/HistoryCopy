"""应用主控:组装存储、监听、记录器、托盘、主窗口与 Qt 事件循环。"""

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from autostart import disable as autostart_disable
from autostart import enable as autostart_enable
from cleanup import cleanup_expired
from clipboard_monitor import ClipboardMonitor
from recorder import ClipboardRecorder
from settings import Settings
from storage import Storage
from ui.icon import app_icon
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.theme import stylesheet

_MUTEX_HANDLE = None

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL,
                                   wintypes.LPCWSTR]


def _already_running() -> bool:
    """通过命名互斥量保证只有一个实例运行。"""
    global _MUTEX_HANDLE
    _MUTEX_HANDLE = _kernel32.CreateMutexW(
        None, False, "Local\\HistoryCopy_SingleInstance")
    return ctypes.get_last_error() == 183


class _Notifier(QObject):
    """跨线程通知界面刷新。"""

    changed = Signal()


class _Controller(QObject):
    """托盘图标与应用生命周期控制。"""

    def __init__(self, app, storage, settings, window):
        super().__init__()
        self._app = app
        self._storage = storage
        self._settings = settings
        self._window = window
        self._daily = QTimer(self)
        self._daily.setInterval(24 * 60 * 60 * 1000)
        self._daily.timeout.connect(self._daily_cleanup)
        self._daily.start()
        self._tray = None
        self._build_tray()

    def _build_tray(self):
        self._tray = QSystemTrayIcon(app_icon(), self)
        self._tray.setToolTip("历史剪贴板")
        menu = QMenu()
        act_open = menu.addAction("打开历史")
        act_open.triggered.connect(self.show_window)
        act_settings = menu.addAction("设置")
        act_settings.triggered.connect(self.open_settings)
        menu.addSeparator()
        act_quit = menu.addAction("退出")
        act_quit.triggered.connect(self.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self._window.isVisible():
                self._window.hide()
            else:
                self.show_window()

    def show_window(self):
        self._window.refresh()
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def open_settings(self):
        dialog = SettingsDialog(self._settings, self._storage, self._window)
        dialog.exec()
        if dialog.changed:
            self._sync_autostart()
            self._daily_cleanup()
            self._window.refresh()

    def _sync_autostart(self):
        if self._settings.get("autostart_enabled"):
            autostart_enable()
        else:
            autostart_disable()

    def _daily_cleanup(self):
        removed = cleanup_expired(
            self._storage, int(self._settings.get("retention_days", 3)))
        if removed:
            self._window.refresh()

    def quit(self):
        self._storage.close()
        self._app.quit()


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("HistoryCopy")
    app.setStyleSheet(stylesheet())

    if _already_running():
        return

    storage = Storage()
    settings = Settings()
    notifier = _Notifier()
    recorder = ClipboardRecorder(storage, on_recorded=notifier.changed.emit)
    monitor = ClipboardMonitor(on_change=recorder.handle_change)
    monitor.start()
    monitor.wait_ready(5)

    window = MainWindow(storage)
    window.setWindowIcon(app_icon())
    notifier.changed.connect(window.schedule_refresh)
    app.setWindowIcon(app_icon())

    controller = _Controller(app, storage, settings, window)
    controller._daily_cleanup()
    if settings.get("autostart_enabled"):
        autostart_enable()

    window.hide()
    controller._tray.showMessage("HistoryCopy", "已后台运行,点击托盘图标查看历史")

    sys.exit(app.exec())
