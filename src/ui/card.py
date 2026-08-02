"""历史卡片组件:展示一条文字/图片记录,提供复制/置顶/删除/预览操作。"""

import html

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils import format_time

_MAX_PREVIEW_CHARS = 200
_MAX_IMAGE_W = 200
_MAX_IMAGE_H = 160


def _highlight_text(content: str, keyword: str) -> str:
    """把关键词出现的位置用浅黄色背景标出,返回富文本 HTML。"""
    low = content.lower()
    kw = keyword.lower()
    parts = []
    start = 0
    while True:
        pos = low.find(kw, start)
        if pos < 0:
            parts.append(html.escape(content[start:]))
            break
        parts.append(html.escape(content[start:pos]))
        parts.append("<span style='background:#FFE08A;'>%s</span>"
                     % html.escape(content[pos:pos + len(kw)]))
        start = pos + len(kw)
    return "".join(parts)


class HistoryCard(QFrame):
    clicked = Signal(int)
    copy_requested = Signal(int)
    pin_requested = Signal(int)
    delete_requested = Signal(int)
    preview_requested = Signal(int)

    def __init__(self, item: dict, keyword: str = "", parent=None):
        super().__init__(parent)
        self.item = item
        self._keyword = (keyword or "").strip()
        self._preview = None
        self._full_text = ""
        self._display_plain = ""
        self._build()
        self._install_click_filter()
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("cardPinned" if item.get("is_pinned") else "card")

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 8)
        v.setSpacing(6)

        if self.item.get("is_pinned"):
            badge = QLabel("📌 置顶")
            badge.setObjectName("pinBadge")
            v.addWidget(badge)

        if self.item["content_type"] == "text":
            self._full_text = self.item["content"] or ""
            display = self._full_text
            if len(display) > _MAX_PREVIEW_CHARS:
                display = display[:_MAX_PREVIEW_CHARS] + "…"
            self._display_plain = display
            preview = QLabel()
            preview.setObjectName("cardText")
            preview.setWordWrap(True)
            if self._keyword and self._keyword.lower() in self._full_text.lower():
                preview.setTextFormat(Qt.RichText)
                preview.setText(_highlight_text(display, self._keyword))
            else:
                preview.setTextFormat(Qt.PlainText)
                preview.setText(display)
            preview.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            preview.ensurePolished()
            preview.setFixedHeight(preview.fontMetrics().lineSpacing() * 2 + 4)
            self._preview = preview
            v.addWidget(preview)
        else:
            thumb = QLabel()
            thumb.setObjectName("cardImage")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setMinimumHeight(40)
            pixmap = QPixmap(self.item["image_abs"])
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    QSize(_MAX_IMAGE_W, _MAX_IMAGE_H),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumb.setPixmap(pixmap)
            else:
                thumb.setText("图片无法显示")
            v.addWidget(thumb)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        time_label = QLabel(format_time(self.item["updated_at"]))
        time_label.setObjectName("cardTime")
        bottom.addWidget(time_label)
        bottom.addStretch(1)

        btn_copy = QPushButton("复制")
        btn_copy.setObjectName("btnMini")
        btn_copy.clicked.connect(lambda: self.copy_requested.emit(self.item["id"]))

        btn_pin = QPushButton("取消置顶" if self.item.get("is_pinned") else "置顶")
        btn_pin.setObjectName("btnMini")
        btn_pin.clicked.connect(lambda: self.pin_requested.emit(self.item["id"]))

        btn_delete = QPushButton("删除")
        btn_delete.setObjectName("btnMiniDanger")
        btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.item["id"]))

        bottom.addWidget(btn_copy)
        if self.item["content_type"] == "image":
            btn_preview = QPushButton("预览")
            btn_preview.setObjectName("btnMini")
            btn_preview.clicked.connect(
                lambda: self.preview_requested.emit(self.item["id"]))
            bottom.addWidget(btn_preview)
        bottom.addWidget(btn_pin)
        bottom.addWidget(btn_delete)
        v.addLayout(bottom)

    def _install_click_filter(self):
        for child in self.findChildren(QWidget):
            if not isinstance(child, QPushButton):
                child.installEventFilter(self)
        self.installEventFilter(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item["id"])
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_tooltip()

    def _update_tooltip(self):
        """文字预览被截断时,悬停显示完整内容。"""
        if self._preview is None:
            return
        clipped = self._full_text != self._display_plain or (
            self._preview.fontMetrics().boundingRect(
                self._preview.rect(), Qt.TextWordWrap, self._display_plain).height()
            > self._preview.height())
        self._preview.setToolTip(self._full_text if clipped else "")

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and not isinstance(obj, QPushButton)):
            self.clicked.emit(self.item["id"])
            event.accept()
            return True
        return super().eventFilter(obj, event)
