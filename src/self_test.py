"""自动化自检脚本(开发用,不属于最终产品)。

验证:监听启动、文字记录、图片记录、去重不新增、图片文件落盘。
用法:python src/self_test.py
"""

import io
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clipboard_monitor import (
    ClipboardMonitor,
    set_clipboard_image,
    set_clipboard_text,
)
from storage import Storage
from utils import md5_hex

FAILED = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILED.append(name)


class _Recorder:
    def __init__(self, storage):
        self._storage = storage
        self._last_text_fp = None
        self._last_image_fp = None

    def handle_change(self):
        from clipboard_monitor import get_clipboard_image, get_clipboard_text
        text = get_clipboard_text()
        image = get_clipboard_image()
        if text is not None:
            fp = md5_hex(text.encode("utf-8"))
            if fp != self._last_text_fp:
                self._last_text_fp = fp
                self._storage.add_text(text)
        if image is not None:
            buf = io.BytesIO()
            image.convert("RGBA").save(buf, format="PNG")
            fp = md5_hex(buf.getvalue())
            if fp != self._last_image_fp:
                self._last_image_fp = fp
                self._storage.add_image(image)


def main():
    tmp = tempfile.mkdtemp(prefix="hc_test_")
    db = os.path.join(tmp, "history.db")
    storage = Storage(db)

    recorder = _Recorder(storage)
    monitor = ClipboardMonitor(on_change=recorder.handle_change)
    monitor.start()
    if not monitor.wait_ready(5):
        print("FAIL  剪贴板监听启动失败")
        sys.exit(1)
    check("监听启动", True)
    time.sleep(0.3)

    set_clipboard_text("hello history")
    time.sleep(0.6)
    check("复制文字后被记录", storage.count() == 1)

    t1 = storage.list_recent(1)[0]["updated_at"]
    time.sleep(1.1)
    set_clipboard_text("hello history")
    time.sleep(0.6)
    check("重复复制不新增", storage.count() == 1)
    t2 = storage.list_recent(1)[0]["updated_at"]
    check("重复复制更新时间", t2 >= t1)

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (135, 155, 213))
    ImageDraw.Draw(img).text((8, 26), "HC", fill=(255, 255, 255))
    set_clipboard_image(img)
    time.sleep(0.8)
    check("复制图片后被记录", storage.count() == 2)
    img_items = [i for i in storage.list_recent(10)
                 if i["content_type"] == "image"]
    check("图片记录类型正确", len(img_items) == 1)
    check("图片文件已保存",
          bool(img_items and img_items[0]["image_abs"]
               and os.path.exists(img_items[0]["image_abs"])))

    monitor.stop()
    storage.close()

    print()
    if FAILED:
        print("自检未通过: %s" % ", ".join(FAILED))
        sys.exit(1)
    print("全部自检通过")


if __name__ == "__main__":
    main()
