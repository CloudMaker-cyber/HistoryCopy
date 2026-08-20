"""剪贴板监听模块(Windows)。

通过系统级事件 AddClipboardFormatListener 监听剪贴板变化,
事件驱动、低占用,不轮询、不干扰用户操作。
"""

import ctypes
import threading
from ctypes import wintypes

# 剪贴板消息与格式常量
WM_CLIPBOARDUPDATE = 0x031D
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
HWND_MESSAGE = -3
CF_UNICODETEXT = 13
CF_DIB = 8
CF_DIBV5 = 17

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# PNG 是"注册格式"(格式名 "PNG"),现代浏览器/Edge"复制图片"常只提供它。
user32.RegisterClipboardFormatW.restype = ctypes.c_uint
user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
CF_PNG = user32.RegisterClipboardFormatW("PNG")

# --- 类型与函数签名声明(避免 64 位指针截断) ---

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, ctypes.c_uint,
                             wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", ctypes.c_uint),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]

kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]

kernel32.GlobalFree.restype = wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]

user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HANDLE, wintypes.HINSTANCE, ctypes.c_void_p,
]

user32.GetMessageW.restype = ctypes.c_int
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND,
                               wintypes.UINT, wintypes.UINT]

user32.DispatchMessageW.restype = ctypes.c_ssize_t
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]

user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint,
                                  wintypes.WPARAM, wintypes.LPARAM]

user32.AddClipboardFormatListener.restype = wintypes.BOOL
user32.AddClipboardFormatListener.argtypes = [wintypes.HWND]

user32.RemoveClipboardFormatListener.restype = wintypes.BOOL
user32.RemoveClipboardFormatListener.argtypes = [wintypes.HWND]

user32.PostQuitMessage.restype = None
user32.PostQuitMessage.argtypes = [ctypes.c_int]

user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint,
                                wintypes.WPARAM, wintypes.LPARAM]

user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]

user32.CloseClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []

user32.EmptyClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []

user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]

user32.GetClipboardData.restype = wintypes.HGLOBAL
user32.GetClipboardData.argtypes = [wintypes.UINT]

user32.SetClipboardData.restype = wintypes.HGLOBAL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HGLOBAL]


# --- 剪贴板内容读取 ---

def get_clipboard_text() -> str | None:
    """读取剪贴板文字,无文字时返回 None。"""
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _read_clipboard_bytes(fmt: int) -> bytes | None:
    """读取剪贴板指定格式的原始字节,无数据或失败时返回 None。"""
    if not user32.IsClipboardFormatAvailable(fmt):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(fmt)
        if not handle:
            return None
        size = kernel32.GlobalSize(handle)
        if not size:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.string_at(ptr, size)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def get_clipboard_image():
    """读取剪贴板图片,返回 PIL Image;无图片时返回 None。

    依次尝试位图(DIB / DIBV5)与 PNG,覆盖截图、浏览器/网页复制图片(仅 PNG)、
    画图等常见来源;同一次剪贴板里存在多个格式时按顺序取第一个能解码的。
    """
    from PIL import Image
    import io

    raws = []
    for fmt in (CF_DIB, CF_DIBV5, CF_PNG):
        raw = _read_clipboard_bytes(fmt)
        if raw:
            raws.append(raw)
    for raw in raws:
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
            return img
        except Exception:
            continue
    return None


# --- 剪贴板写入(测试与"复制回剪贴板"功能使用) ---

_GMEM_MOVEABLE = 0x0002
_GMEM_ZEROINIT = 0x0040


def set_clipboard_text(text: str) -> bool:
    """把文字写入系统剪贴板,返回是否成功。"""
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        handle = kernel32.GlobalAlloc(_GMEM_MOVEABLE | _GMEM_ZEROINIT, len(data))
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        try:
            ctypes.memmove(ptr, data, len(data))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def set_clipboard_image(image) -> bool:
    """把 PIL Image 写入系统剪贴板(位图格式),返回是否成功。"""
    from PIL import Image
    import io
    if isinstance(image, str):
        image = Image.open(image)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="BMP")
    bmp = buf.getvalue()
    dib = bmp[14:]  # 去掉 BMP 文件头,保留位图信息头与像素数据
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(_GMEM_MOVEABLE | _GMEM_ZEROINIT, len(dib))
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        try:
            ctypes.memmove(ptr, dib, len(dib))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_DIB, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


# --- 监听器 ---

class ClipboardMonitor:
    """后台监听剪贴板变化,变化时回调 on_change。

    回调由一个常驻 worker 串行执行:短时间内多次剪贴板变化会合并成一次唤醒
    (事件驱动、不轮询),既避免"每次变化都新开线程"的堆积,也避免多个线程
    并发读取进程级互斥的剪贴板而偶发漏读。
    """

    def __init__(self, on_change=None):
        self.on_change = on_change
        self._wndproc = WNDPROC(self._wnd_proc)
        self._hwnd = None
        self._thread = None
        self._worker = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._ready = threading.Event()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_CLIPBOARDUPDATE:
            self._wake.set()
        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _worker_loop(self):
        while not self._stop.is_set():
            self._wake.wait()
            if self._stop.is_set():
                return
            self._wake.clear()
            cb = self.on_change
            if not cb:
                continue
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                from utils import log_error
                log_error("clipboard_monitor 回调异常: %r" % (exc,))

    def start(self):
        """在后台线程启动监听消息循环与回调 worker。"""
        self._worker = threading.Thread(target=self._worker_loop, daemon=True,
                                        name="clipboard-worker")
        self._worker.start()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="clipboard-monitor")
        self._thread.start()

    @property
    def is_ready(self):
        """监听窗口是否已注册完成。"""
        return self._ready.is_set()

    def wait_ready(self, timeout=5.0) -> bool:
        return self._ready.wait(timeout)

    def _run(self):
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinst
        wc.lpszClassName = "HistoryCopyClipboardListener"
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.get_last_error() != 1410:
            return  # 1410 = ERROR_CLASS_ALREADY_EXISTS
        self._hwnd = user32.CreateWindowExW(
            0, "HistoryCopyClipboardListener", "HistoryCopyClipboard",
            0, 0, 0, 0, 0, HWND_MESSAGE, None, hinst, None)
        if not self._hwnd:
            return
        user32.AddClipboardFormatListener(self._hwnd)
        self._ready.set()
        msg = MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result <= 0:
                break
            user32.DispatchMessageW(ctypes.byref(msg))
        if self._hwnd:
            user32.RemoveClipboardFormatListener(self._hwnd)

    def stop(self):
        """停止监听。"""
        self._stop.set()
        self._wake.set()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
