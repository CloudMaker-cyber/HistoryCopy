"""通用工具:路径解析、时间格式化、MD5 指纹。"""

import datetime
import hashlib
import os
import sys
import time

APP_NAME = "HistoryCopy"


def is_frozen() -> bool:
    """是否处于 PyInstaller 打包后的运行环境。"""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    """程序主目录:打包后为 exe 所在目录,开发时为项目根目录。"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    """数据目录(数据库与图片文件的上级)。"""
    d = os.path.join(app_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def images_dir() -> str:
    """图片文件目录。"""
    d = os.path.join(data_dir(), "images")
    os.makedirs(d, exist_ok=True)
    return d


def db_path() -> str:
    """SQLite 数据库文件路径。"""
    return os.path.join(data_dir(), "history.db")


def now_str() -> str:
    """当前时间,ISO 格式字符串,可直接按字符串排序。"""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def md5_hex(data: bytes) -> str:
    """计算字节内容的 MD5 指纹,用于去重。"""
    return hashlib.md5(data).hexdigest()


def format_time(ts: str | None) -> str:
    """把存储时间显示成友好格式:今天/昨天/具体日期 + 时刻。"""
    if not ts:
        return ""
    try:
        d = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts
    today = datetime.date.today()
    hhmm = d.strftime("%H:%M")
    if d.date() == today:
        return "今天 " + hhmm
    if d.date() == today - datetime.timedelta(days=1):
        return "昨天 " + hhmm
    return d.strftime("%Y-%m-%d %H:%M")


def log_error(message: str) -> None:
    """把异常写入 data/error.log,保证程序不因偶发错误崩溃。"""
    try:
        with open(os.path.join(data_dir(), "error.log"), "a",
                  encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))
    except OSError:
        pass
