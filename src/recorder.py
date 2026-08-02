"""剪贴板记录器:把剪贴板变化写入存储,并做快照去重。

避免"仅图片变化但剪贴板残留旧文字"导致的误记录。
新增/更新时间后的回调(可选)用于通知界面刷新。
"""

import io

from clipboard_monitor import get_clipboard_image, get_clipboard_text
from storage import Storage
from utils import log_error, md5_hex


class ClipboardRecorder:
    def __init__(self, storage: Storage, on_recorded=None):
        self._storage = storage
        self._on_recorded = on_recorded
        self._last_text_fp = None
        self._last_image_fp = None

    def _notify(self):
        if self._on_recorded:
            self._on_recorded()

    def handle_change(self):
        try:
            text = get_clipboard_text()
            image = get_clipboard_image()
            if text is not None:
                fp = md5_hex(text.encode("utf-8"))
                if fp != self._last_text_fp:
                    self._last_text_fp = fp
                    self._storage.add_text(text)
                    self._notify()
            if image is not None:
                buf = io.BytesIO()
                image.convert("RGBA").save(buf, format="PNG")
                fp = md5_hex(buf.getvalue())
                if fp != self._last_image_fp:
                    self._last_image_fp = fp
                    self._storage.add_image(image)
                    self._notify()
        except Exception as exc:  # noqa: BLE001
            log_error("recorder.handle_change: %r" % (exc,))
