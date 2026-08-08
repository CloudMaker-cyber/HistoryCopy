"""数据存储模块。

文字记录存 SQLite,图片以文件保存于 data/images/ 并在库中记录路径。
支持去重:相同内容再次复制时仅更新时间,不重复新增。
线程安全:所有写操作通过同一连接 + 锁执行。
"""

import io
import os
import sqlite3
import threading

from utils import db_path, images_dir, now_str, md5_hex

_COLUMNS = ("id", "content_type", "content", "image_path", "ocr_text",
            "created_at", "updated_at", "is_pinned", "pinned_at")


class Storage:
    def __init__(self, path: str | None = None):
        self.path = path or db_path()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS clip_items ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " content_type TEXT NOT NULL,"
                " content TEXT,"
                " image_path TEXT,"
                " ocr_text TEXT,"
                " fingerprint TEXT,"
                " created_at TEXT NOT NULL,"
                " updated_at TEXT NOT NULL,"
                " is_pinned INTEGER NOT NULL DEFAULT 0,"
                " pinned_at TEXT)"
            )
            cols = {r[1] for r in self._conn.execute(
                "PRAGMA table_info(clip_items)").fetchall()}
            if "ocr_text" not in cols:
                self._conn.execute("ALTER TABLE clip_items ADD COLUMN ocr_text TEXT")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_updated ON clip_items(updated_at)")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fingerprint "
                "ON clip_items(content_type, fingerprint)")
            self._conn.commit()

    def _row_to_dict(self, row):
        item = dict(zip(_COLUMNS, row))
        if item["image_path"]:
            item["image_abs"] = os.path.join(images_dir(), item["image_path"])
        else:
            item["image_abs"] = None
        return item

    # --- 写入 ---

    def add_text(self, content: str) -> int:
        """记录一条文字。相同内容再次复制则仅刷新时间,返回记录 id。"""
        content = (content or "").strip()
        if not content:
            return -1
        fp = md5_hex(content.encode("utf-8"))
        now = now_str()
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM clip_items WHERE content_type='text' "
                "AND fingerprint=? LIMIT 1", (fp,)).fetchone()
            if row:
                self._conn.execute(
                    "UPDATE clip_items SET updated_at=? WHERE id=?",
                    (now, row[0]))
                self._conn.commit()
                return row[0]
            cur = self._conn.execute(
                "INSERT INTO clip_items (content_type, content, fingerprint,"
                " created_at, updated_at) VALUES (?,?,?,?,?)",
                ("text", content, fp, now, now))
            self._conn.commit()
            return cur.lastrowid

    def add_image(self, image) -> int:
        """记录一张图片(PIL Image)。相同图片再次复制则仅刷新时间。"""
        buf = io.BytesIO()
        image.convert("RGBA").save(buf, format="PNG")
        data = buf.getvalue()
        fp = md5_hex(data)
        now = now_str()
        with self._lock:
            row = self._conn.execute(
                "SELECT id, image_path FROM clip_items WHERE content_type='image' "
                "AND fingerprint=? LIMIT 1", (fp,)).fetchone()
            if row:
                self._conn.execute(
                    "UPDATE clip_items SET updated_at=? WHERE id=?",
                    (now, row[0]))
                self._conn.commit()
                return row[0]
            fname = f"img_{now_str().replace(':', '').replace(' ', '_')}_{fp[:8]}.png"
            with open(os.path.join(images_dir(), fname), "wb") as f:
                f.write(data)
            cur = self._conn.execute(
                "INSERT INTO clip_items (content_type, image_path, fingerprint,"
                " created_at, updated_at) VALUES (?,?,?,?,?)",
                ("image", fname, fp, now, now))
            self._conn.commit()
            return cur.lastrowid

    # --- 查询 ---

    def list_recent(self, limit: int = 100) -> list:
        """按最后更新时间倒序返回最近记录。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT %s FROM clip_items ORDER BY updated_at DESC LIMIT ?"
                % ", ".join(_COLUMNS), (limit,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_sorted(self, limit: int = 500) -> list:
        """列表用排序:置顶优先(按置顶时间倒序),其余按最后更新时间倒序。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT %s FROM clip_items ORDER BY is_pinned DESC,"
                " COALESCE(pinned_at, updated_at) DESC LIMIT ?"
                % ", ".join(_COLUMNS), (limit,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, item_id: int):
        """按 id 取单条记录。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT %s FROM clip_items WHERE id=?" % ", ".join(_COLUMNS),
                (item_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM clip_items").fetchone()
        return row[0] if row else 0

    def list_expired(self, cutoff: str) -> list:
        """返回最后更新时间早于 cutoff 且未置顶的记录。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT %s FROM clip_items WHERE is_pinned=0 AND updated_at < ?"
                % ", ".join(_COLUMNS), (cutoff,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def clear_all(self) -> None:
        """清空所有记录并删除对应图片文件。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT image_path FROM clip_items").fetchall()
            self._conn.execute("DELETE FROM clip_items")
            self._conn.commit()
        for (path,) in rows:
            if path:
                full = os.path.join(images_dir(), path)
                if os.path.exists(full):
                    try:
                        os.remove(full)
                    except OSError:
                        pass

    # --- 管理(置顶/删除,后续界面阶段使用) ---

    def set_pinned(self, item_id: int, pinned: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE clip_items SET is_pinned=?, pinned_at=? WHERE id=?",
                (1 if pinned else 0, now_str() if pinned else None, item_id))
            self._conn.commit()

    def delete(self, item_id: int) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT image_path FROM clip_items WHERE id=?", (item_id,)).fetchone()
            self._conn.execute("DELETE FROM clip_items WHERE id=?", (item_id,))
            self._conn.commit()
        if row and row[0]:
            full = os.path.join(images_dir(), row[0])
            if os.path.exists(full):
                try:
                    os.remove(full)
                except OSError:
                    pass

    def delete_many(self, item_ids: list) -> None:
        """批量删除多条记录并清理对应图片文件。"""
        ids = [i for i in item_ids if isinstance(i, int)]
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        with self._lock:
            rows = self._conn.execute(
                "SELECT image_path FROM clip_items WHERE id IN (%s)" % placeholders,
                ids).fetchall()
            self._conn.execute(
                "DELETE FROM clip_items WHERE id IN (%s)" % placeholders, ids)
            self._conn.commit()
        for (path,) in rows:
            if path:
                full = os.path.join(images_dir(), path)
                if os.path.exists(full):
                    try:
                        os.remove(full)
                    except OSError:
                        pass

    def set_ocr_text(self, item_id: int, text: str) -> None:
        """保存图片识别出的文字(为空则视为清除)。"""
        with self._lock:
            self._conn.execute(
                "UPDATE clip_items SET ocr_text=? WHERE id=?",
                (text or "", item_id))
            self._conn.commit()

    def get_ocr_text(self, item_id: int) -> str:
        """读取某条记录已识别的文字。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT ocr_text FROM clip_items WHERE id=?", (item_id,)).fetchone()
        return (row[0] if row and row[0] else "") or ""

    def close(self) -> None:
        with self._lock:
            self._conn.close()
