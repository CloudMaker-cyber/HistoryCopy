"""主窗口:无边框淡蓝色界面,含搜索框、卡片列表(置顶优先/时间倒序)、操作。"""

import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clipboard_monitor import set_clipboard_image, set_clipboard_text
from storage import Storage
from ui.card import HistoryCard
from ui.preview import ImagePreviewDialog

_LIST_LIMIT = 2000


class _DragHandle(QLabel):
    """可拖动窗口的标题区域。"""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._offset = (event.globalPosition().toPoint()
                            - self.window().frameGeometry().topLeft())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "_offset"):
            self.window().move(event.globalPosition().toPoint() - self._offset)
            event.accept()


class MainWindow(QWidget):
    def __init__(self, storage: Storage):
        super().__init__()
        self._storage = storage
        self._footer_text = "共 0 条记录"
        self._last_keyword = ""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(200)
        self._refresh_timer.timeout.connect(self.refresh)
        self._build_ui()
        self.refresh()

    # --- 界面搭建 ---

    def _build_ui(self):
        self.setWindowTitle("历史剪贴板")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self.setMinimumHeight(460)
        self.resize(420, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

        shell = QFrame(objectName="Shell")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.gray)
        shell.setGraphicsEffect(shadow)
        root.addWidget(shell)

        shell_l = QVBoxLayout(shell)
        shell_l.setContentsMargins(14, 12, 14, 10)
        shell_l.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = _DragHandle("历史剪贴板")
        title.setObjectName("appTitle")
        title.setFixedHeight(30)
        header.addWidget(title)

        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("搜索历史记录...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self.schedule_refresh)
        header.addWidget(self._search, 1)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(28, 28)
        btn_close.clicked.connect(self.hide)
        header.addWidget(btn_close)
        shell_l.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("cardScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(2, 6, 2, 6)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._container)
        shell_l.addWidget(self._scroll, 1)

        self._footer = QLabel(self._footer_text)
        self._footer.setObjectName("footer")
        shell_l.addWidget(self._footer)

    # --- 数据刷新 ---

    def schedule_refresh(self):
        """防抖刷新:复制/搜索触发的刷新合并到 200ms 后执行一次。"""
        self._refresh_timer.start()

    def refresh(self):
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()

        keyword = self._search.text().strip().lower()
        keep_scroll = keyword == self._last_keyword
        self._last_keyword = keyword
        scrollbar = self._scroll.verticalScrollBar()
        scroll_pos = scrollbar.value() if keep_scroll else 0

        items = self._storage.list_sorted(_LIST_LIMIT)

        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        shown = 0
        for item in items:
            if keyword and item["content_type"] == "text":
                if keyword not in (item["content"] or "").lower():
                    continue
            card = HistoryCard(item, keyword=keyword)
            card.clicked.connect(self._on_card_clicked)
            card.copy_requested.connect(self._on_copy)
            card.pin_requested.connect(self._on_pin)
            card.delete_requested.connect(self._on_delete)
            card.preview_requested.connect(self._on_preview)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
            shown += 1

        if shown == 0:
            hint = QLabel("暂无复制记录" if not self._storage.count() else "未找到相关记录")
            hint.setObjectName("emptyHint")
            hint.setAlignment(Qt.AlignCenter)
            hint.setFixedHeight(160)
            self._list_layout.insertWidget(self._list_layout.count() - 1, hint)

        self._footer_text = "共 %d 条记录 · 显示 %d 条" % (self._storage.count(), shown)
        self._footer.setText(self._footer_text)

        if keep_scroll and scroll_pos:
            QTimer.singleShot(0, lambda: scrollbar.setValue(
                min(scroll_pos, scrollbar.maximum())))
        elif not keep_scroll:
            scrollbar.setValue(0)

    # --- 操作处理 ---

    def _on_card_clicked(self, item_id: int):
        if self._copy(item_id):
            self._flash_copied()
            self.hide()
        else:
            self._footer.setText("复制失败,请重试")

    def _on_copy(self, item_id: int):
        if self._copy(item_id):
            self._flash_copied()
        else:
            self._footer.setText("复制失败,请重试")

    def _copy(self, item_id: int) -> bool:
        item = self._storage.get(item_id)
        if not item:
            return False
        if item["content_type"] == "text":
            return set_clipboard_text(item["content"] or "")
        try:
            from PIL import Image
            image = Image.open(item["image_abs"])
            return set_clipboard_image(image)
        except Exception:
            return False

    def _flash_copied(self):
        self._footer.setText("已复制到剪贴板,可直接 Ctrl+V 粘贴 ✓")
        QTimer.singleShot(1500, lambda: self._footer.setText(self._footer_text))

    def _on_pin(self, item_id: int):
        item = self._storage.get(item_id)
        if not item:
            return
        self._storage.set_pinned(item_id, not item["is_pinned"])
        self.refresh()

    def _on_delete(self, item_id: int):
        item = self._storage.get(item_id)
        if not item:
            return
        tip = ("这是一条置顶记录,确定要删除吗?" if item["is_pinned"]
               else "确定要删除这条记录吗?")
        answer = QMessageBox.question(
            self, "删除确认", tip,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._storage.delete(item_id)
            self.refresh()

    def _on_preview(self, item_id: int):
        item = self._storage.get(item_id)
        if item and item["image_abs"] and os.path.exists(item["image_abs"]):
            ImagePreviewDialog(item["image_abs"], self).exec()

    # --- 快捷键 ---

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
