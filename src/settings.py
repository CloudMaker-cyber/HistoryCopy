"""应用设置:以 JSON 文件保存,默认存放在 data/settings.json。"""

import json
import os

from utils import data_dir

DEFAULTS = {
    "retention_days": 3,
    "autostart_enabled": False,
}


class Settings:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "settings.json")
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)
        except (OSError, ValueError):
            pass

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()
