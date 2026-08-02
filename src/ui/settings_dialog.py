"""设置对话框:保留期限、开机自启、清空历史、立即清理。"""

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from cleanup import cleanup_expired

_RETENTION_CHOICES = (1, 3, 5)


class SettingsDialog(QDialog):
    def __init__(self, settings, storage, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._storage = storage
        self.changed = False
        self.setWindowTitle("设置")
        self.setFixedWidth(380)
        self._build()
        self._load()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(12)

        group_ret = QGroupBox("保留期限(超过期限自动清理)")
        ret_l = QVBoxLayout(group_ret)
        self._radio_group = QButtonGroup(self)
        self._radios = {}
        for days in _RETENTION_CHOICES:
            rb = QRadioButton("%d 天" % days)
            self._radios[days] = rb
            self._radio_group.addButton(rb, days)
            ret_l.addWidget(rb)
        v.addWidget(group_ret)

        group_auto = QGroupBox("开机自启")
        auto_l = QVBoxLayout(group_auto)
        self._auto_check = QCheckBox("开机自动启动 HistoryCopy(写入注册表)")
        auto_l.addWidget(self._auto_check)
        v.addWidget(group_auto)

        row = QHBoxLayout()
        btn_clear = QPushButton("清空所有历史")
        btn_clear.setObjectName("btnMiniDanger")
        btn_clear.clicked.connect(self._on_clear)
        btn_clean = QPushButton("立即清理过期")
        btn_clean.setObjectName("btnMini")
        btn_clean.clicked.connect(self._on_clean_now)
        row.addWidget(btn_clear)
        row.addWidget(btn_clean)
        v.addLayout(row)

        self._tip = QLabel("")
        self._tip.setObjectName("footer")
        v.addWidget(self._tip)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btn_ok = QPushButton("确定")
        btn_ok.setObjectName("btnMini")
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("btnMini")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        v.addLayout(btns)

    def _load(self):
        days = int(self._settings.get("retention_days", 3))
        rb = self._radios.get(days) or self._radios[3]
        rb.setChecked(True)
        self._auto_check.setChecked(
            bool(self._settings.get("autostart_enabled", False)))

    def _selected_days(self) -> int:
        return self._radio_group.checkedId()

    def _on_clear(self):
        answer = QMessageBox.question(
            self, "清空确认", "确定要清空所有历史记录吗?此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._storage.clear_all()
            self._tip.setText("已清空所有历史记录")
            self.changed = True

    def _on_clean_now(self):
        removed = cleanup_expired(self._storage, self._selected_days())
        self._tip.setText("已清理 %d 条过期记录" % removed)
        self.changed = True

    def _on_ok(self):
        self._settings.set("retention_days", self._selected_days())
        self._settings.set("autostart_enabled", self._auto_check.isChecked())
        self.changed = True
        self.accept()
