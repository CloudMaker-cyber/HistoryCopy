"""历史卡片组件:展示一条文字/图片记录,提供复制/置顶/删除/预览操作。"""

import html

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
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


_ZWSP = "\u200b"
_LONG_TOKEN_LIMIT = 30
# QLabel 会在此断行的空白:普通空格、制表符、回车换行等。
_BREAKABLE_SPACE = frozenset(" \t\n\r\f\v")
# Qt 视为"不换行空格"(网页/Office 复制文本常见),QLabel 不会在此折行,
# 必须按普通字符计长并补零宽空格,否则整段会变成一个无法断行的超长单词。
_NOBREAK_SPACE = frozenset("\u00a0\u2007\u202f")


def _break_long_tokens(content: str) -> str:
    """在连续无空格的超长段中插入零宽换行符,使 QLabel 能按字符断行。

    原因:QLabel 自动换行按"单词"断行,遇到超长无空格串(网址/代码/base64)
    不会断行,导致卡片最小宽度被撑破容器。零宽字符不影响显示与复制。
    注意:不换行空格也应计长,并在其后补零宽空格使其成为可断行点。
    """
    parts = []
    buf = []
    buf_len = 0
    for ch in content:
        if ch in _BREAKABLE_SPACE:
            if buf:
                parts.append("".join(buf))
                buf, buf_len = [], 0
            parts.append(ch)
        else:
            buf.append(ch)
            buf_len += 1
            if buf_len >= _LONG_TOKEN_LIMIT:
                parts.append("".join(buf))
                parts.append(_ZWSP)
                buf, buf_len = [], 0
            if ch in _NOBREAK_SPACE:
                # 不换行空格 Qt 不会断开,补零宽空格让文字能在此折行。
                parts.append("".join(buf) + _ZWSP)
                buf, buf_len = [], 0
    if buf:
        parts.append("".join(buf))
    return "".join(parts)


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
    ocr_requested = Signal(int)
    selection_toggled = Signal(int, bool)

    def __init__(self, item: dict, keyword: str = "", parent=None):
        super().__init__(parent)
        self.item = item
        self._keyword = (keyword or "").strip()
        self._preview = None
        self._full_text = ""
        self._display_plain = ""
        self._selection_mode = False
        self._checked = False
        self._build()
        self._install_click_filter()
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("cardPinned" if item.get("is_pinned") else "card")

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 10, 8, 8)
        v.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(8)
        self._checkbox = QCheckBox()
        self._checkbox.setObjectName("cardCheck")
        self._checkbox.setFixedSize(18, 18)
        self._checkbox.setEnabled(False)
        self._checkbox.setVisible(False)
        self._checkbox.stateChanged.connect(self._on_checkbox)
        head.addWidget(self._checkbox)

        if self.item.get("is_pinned"):
            badge = QLabel("📌 置顶")
            badge.setObjectName("pinBadge")
            head.addWidget(badge)
        head.addStretch(1)
        # 时间放在头部行(右侧),底部按钮行不再塞时间,避免按钮行总宽
        # 超出 420px 窗口下的可视宽度、把"删除"按钮顶出卡片(见 devlog 2026-08-20)。
        head_time = QLabel(format_time(self.item["updated_at"]))
        head_time.setObjectName("cardTime")
        head.addWidget(head_time)
        v.addLayout(head)

        if self.item["content_type"] == "text":
            self._full_text = self.item["content"] or ""
            display = self._full_text
            if len(display) > _MAX_PREVIEW_CHARS:
                display = display[:_MAX_PREVIEW_CHARS] + "…"
            self._display_plain = display
            # 对超长无空格段插入零宽换行符,防止撑破卡片宽度。
            display = _break_long_tokens(display)
            preview = QLabel()
            preview.setObjectName("cardText")
            preview.setMinimumWidth(0)
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
            thumb.setMaximumWidth(_MAX_IMAGE_W)
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
        bottom.setSpacing(6)
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

        self._btn_copy = btn_copy
        self._btn_pin = btn_pin
        self._btn_delete = btn_delete
        self._btn_preview = None
        self._btn_ocr = None

        bottom.addWidget(btn_copy)
        if self.item["content_type"] == "image":
            btn_preview = QPushButton("预览")
            btn_preview.setObjectName("btnMini")
            btn_preview.clicked.connect(
                lambda: self.preview_requested.emit(self.item["id"]))
            btn_ocr = QPushButton("识别")
            btn_ocr.setObjectName("btnOcr")
            btn_ocr.clicked.connect(
                lambda: self.ocr_requested.emit(self.item["id"]))
            self._btn_preview = btn_preview
            self._btn_ocr = btn_ocr
            bottom.addWidget(btn_preview)
            bottom.addWidget(btn_ocr)
        bottom.addWidget(btn_pin)
        bottom.addWidget(btn_delete)
        v.addLayout(bottom)

    # --- 多选模式 ---

    def set_selection_mode(self, active: bool) -> None:
        """进入/退出多选模式:显示勾选框,隐藏操作按钮。"""
        self._selection_mode = active
        self._checkbox.setVisible(active)
        self._checkbox.setEnabled(active)
        self._btn_copy.setVisible(not active)
        self._btn_pin.setVisible(not active)
        self._btn_delete.setVisible(not active)
        if self._btn_preview is not None:
            self._btn_preview.setVisible(not active)
            self._btn_ocr.setVisible(not active)

    def set_checked(self, checked: bool) -> None:
        """设置勾选状态(不触发 stateChanged 信号循环)。"""
        self._checked = bool(checked)
        self._checkbox.blockSignals(True)
        self._checkbox.setChecked(self._checked)
        self._checkbox.blockSignals(False)

    def set_ocr_busy(self, busy: bool) -> None:
        """识别中禁用"识别文字"按钮,防止重复点击。"""
        if self._btn_ocr is not None:
            self._btn_ocr.setEnabled(not busy)
            self._btn_ocr.setText("识别中…" if busy else "识别")

    def _on_checkbox(self, state: int) -> None:
        self._checked = state == Qt.Checked
        self.selection_toggled.emit(self.item["id"], self._checked)

    def _install_click_filter(self):
        for child in self.findChildren(QWidget):
            if not isinstance(child, QPushButton):
                child.installEventFilter(self)
        self.installEventFilter(self)

    def _toggle_selection(self) -> None:
        if self._selection_mode:
            self.set_checked(not self._checked)
            self.selection_toggled.emit(self.item["id"], self._checked)
        else:
            self.clicked.emit(self.item["id"])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_selection()
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
            self._toggle_selection()
            event.accept()
            return True
        return super().eventFilter(obj, event)
