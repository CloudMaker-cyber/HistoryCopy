"""主窗口:无边框淡蓝色界面,含搜索框、卡片列表(置顶优先/时间倒序)、操作。"""

import os

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clipboard_monitor import set_clipboard_image, set_clipboard_text
from storage import Storage
from ui.card import HistoryCard
from ui.ocr_dialog import OcrResultDialog
from ui.preview import ImagePreviewDialog

_LIST_LIMIT = 2000


class _OcrWorker(QThread):
    """后台执行图片文字识别,完成后带回结果,避免卡界面。"""

    finished_ocr = Signal(int, str)

    def __init__(self, item_id: int, image_path: str, parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self._image_path = image_path

    def run(self):
        from ocr import extract_text
        text = extract_text(self._image_path)
        self.finished_ocr.emit(self._item_id, text)


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
        self._selection_mode = False
        self._selected_ids = set()
        self._ocr_in_progress = set()
        self._ocr_worker = None
        self._ocr_item_id = None
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

        self._btn_select = QPushButton("选择")
        self._btn_select.setObjectName("btnHeader")
        self._btn_select.setFixedHeight(28)
        self._btn_select.clicked.connect(self._toggle_selection_mode)
        header.addWidget(self._btn_select)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(28, 28)
        btn_close.clicked.connect(self.hide)
        header.addWidget(btn_close)
        shell_l.addLayout(header)

        self._selection_bar = QHBoxLayout()
        self._selection_bar.setSpacing(8)
        self._sel_info = QLabel("")
        self._sel_info.setObjectName("selInfo")
        self._sel_info.setVisible(False)
        self._btn_delete_selected = QPushButton("删除所选")
        self._btn_delete_selected.setObjectName("btnMiniDanger")
        self._btn_delete_selected.setFixedHeight(26)
        self._btn_delete_selected.setVisible(False)
        self._btn_delete_selected.clicked.connect(self._on_delete_selected)
        self._btn_select_all = QPushButton("全选")
        self._btn_select_all.setObjectName("btnMini")
        self._btn_select_all.setFixedHeight(26)
        self._btn_select_all.setVisible(False)
        self._btn_select_all.clicked.connect(self._on_select_all)
        self._selection_bar.addWidget(self._sel_info, 1)
        self._selection_bar.addWidget(self._btn_select_all)
        self._selection_bar.addWidget(self._btn_delete_selected)
        shell_l.addLayout(self._selection_bar)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("cardScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(2, 6, 2, 6)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch(1)
        # 容器横向尺寸策略设为 Ignored,使其宽度恒定等于可视区宽度,
        # 任何卡片内容都不会再把列表撑出可视宽度(见 devlog 2026-08-20)。
        self._container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        # 不允许任何一张卡片的最小宽度把容器撑得比可视区更宽:
        # 极端长内容只会在卡片内截断(悬停可看全文),而不是让所有卡片一起变宽。
        self._list_layout.setSizeConstraint(QLayout.SetNoConstraint)
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
            card.ocr_requested.connect(self._on_ocr_requested)
            card.selection_toggled.connect(self._on_selection_toggled)
            card.set_selection_mode(self._selection_mode)
            if self._selection_mode:
                card.set_checked(item["id"] in self._selected_ids)
            if item["id"] in self._ocr_in_progress:
                card.set_ocr_busy(True)
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

    # --- 图像文字识别 ---

    def _on_ocr_requested(self, item_id: int):
        """点击"识别文字":命中缓存直接展示,否则后台识别。"""
        if item_id in self._ocr_in_progress:
            return
        item = self._storage.get(item_id)
        if not item or item["content_type"] != "image":
            return
        if not item["image_abs"] or not os.path.exists(item["image_abs"]):
            self._footer.setText("图片文件缺失,无法识别")
            return
        cached = self._storage.get_ocr_text(item_id)
        if cached:
            OcrResultDialog(cached, self).exec()
            return

        card = self._find_card(item_id)
        if card is not None:
            card.set_ocr_busy(True)
        self._ocr_in_progress.add(item_id)
        worker = _OcrWorker(item_id, item["image_abs"])
        worker.finished_ocr.connect(self._on_ocr_finished)
        worker.finished.connect(worker.deleteLater)
        self._ocr_worker = worker
        self._ocr_item_id = item_id
        worker.start()

    def _on_ocr_finished(self, item_id: int, text: str):
        self._ocr_in_progress.discard(item_id)
        card = self._find_card(item_id)
        if card is not None:
            card.set_ocr_busy(False)
        if self._ocr_worker is not None:
            self._ocr_worker = None
        if not text:
            self._footer.setText("未能识别出文字,请尝试更清晰的图片")
            return
        self._storage.set_ocr_text(item_id, text)
        OcrResultDialog(text, self).exec()

    def _find_card(self, item_id: int):
        """在当前列表布局中找到指定记录对应的卡片组件。"""
        count = self._list_layout.count()
        for i in range(count):
            widget = self._list_layout.itemAt(i).widget()
            if isinstance(widget, HistoryCard) and widget.item["id"] == item_id:
                return widget
        return None

    # --- 多选 / 批量删除 ---

    def _toggle_selection_mode(self):
        if not self._selection_mode and self._storage.count() == 0:
            return
        self._selection_mode = not self._selection_mode
        if not self._selection_mode:
            self._selected_ids.clear()
        self._update_selection_ui()
        self.refresh()

    def _update_selection_ui(self):
        active = self._selection_mode
        self._btn_select.setText("取消" if active else "选择")
        self._sel_info.setVisible(active)
        self._btn_delete_selected.setVisible(active)
        self._btn_select_all.setVisible(active)
        if active:
            self._update_selection_info()

    def _update_selection_info(self):
        n = len(self._selected_ids)
        self._sel_info.setText("已选 %d 条" % n)

    def _on_selection_toggled(self, item_id: int, checked: bool):
        if checked:
            self._selected_ids.add(item_id)
        else:
            self._selected_ids.discard(item_id)
        self._update_selection_info()

    def _on_select_all(self):
        for i in range(self._list_layout.count()):
            widget = self._list_layout.itemAt(i).widget()
            if isinstance(widget, HistoryCard):
                self._selected_ids.add(widget.item["id"])
                widget.set_checked(True)
        self._update_selection_info()

    def _on_delete_selected(self):
        if not self._selected_ids:
            return
        has_pinned = any(
            self._storage.get(i) and self._storage.get(i)["is_pinned"]
            for i in self._selected_ids)
        total = len(self._selected_ids)
        tip = ("确定要删除选中的 %d 条记录吗?" % total +
               (("(包含置顶记录)" if has_pinned else "")))
        answer = QMessageBox.question(
            self, "删除确认", tip,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._storage.delete_many(list(self._selected_ids))
            self._selected_ids.clear()
            self._selection_mode = False
            self._update_selection_ui()
            self.refresh()

    # --- 快捷键 ---

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
