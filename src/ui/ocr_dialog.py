"""OCR 识别结果对话框:展示识别出的文字,支持一键复制到剪贴板。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from clipboard_monitor import set_clipboard_text


class OcrResultDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("识别文字")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumSize(420, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        tip = QLabel("已识别出 %d 行文字" % (len(text.splitlines()) if text.strip() else 0))
        tip.setObjectName("selInfo")
        layout.addWidget(tip)

        self._editor = QTextEdit()
        self._editor.setObjectName("ocrText")
        self._editor.setPlainText(text)
        self._editor.setReadOnly(True)
        layout.addWidget(self._editor, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btn_copy = QPushButton("复制文字")
        btn_copy.setObjectName("btnMini")
        btn_copy.clicked.connect(self._copy)
        self._feedback = QLabel("")
        self._feedback.setObjectName("selInfo")
        btns.addWidget(self._feedback, 1)
        btns.addWidget(btn_copy)
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("btnMiniDanger")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def _copy(self):
        text = self._editor.toPlainText()
        if text and set_clipboard_text(text):
            self._feedback.setText("已复制,可直接 Ctrl+V 粘贴 ✓")
        else:
            self._feedback.setText("复制失败,请重试")