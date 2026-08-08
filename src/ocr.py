"""图像文字识别模块。

封装 RapidOCR(rapidocr + onnxruntime):完全离线、CPU 推理,识别中英文。
设计:
- 懒加载:第一次识别时才创建引擎(首次加载 1~2 秒),不拖慢程序启动;
- 出错兜底:识别异常写入 data/error.log,不崩溃;
- 结果由调用方存入数据库 (storage.set_ocr_text)。
"""

import threading

from utils import log_error

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    """返回并缓存全局 RapidOCR 引擎(线程安全)。"""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from rapidocr import RapidOCR
                _engine = RapidOCR()
    return _engine


def is_available() -> bool:
    """RapidOCR 是否可用(环境变量安装正常情况下恒为 True)。"""
    try:
        import rapidocr  # noqa: F401
        import onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def extract_text(image_path: str) -> str:
    """识别图片文件中的文字,按行拼接返回;失败返回空字符串。"""
    try:
        out = _get_engine()(image_path)
        txts = getattr(out, "txts", None)
        if not txts:
            return ""
        lines = []
        for t in txts:
            t = str(t).strip()
            if t:
                lines.append(t)
        return "\n".join(lines)
    except Exception as e:
        log_error("OCR 识别异常 (%s): %s" % (image_path, e))
        return ""