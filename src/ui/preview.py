"""大图预览对话框。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

_MAX_W = 720
_MAX_H = 520


class ImagePreviewDialog(QDialog):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.setText("图片无法显示")
        else:
            pixmap = pixmap.scaled(_MAX_W, _MAX_H,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            self.resize(min(pixmap.width() + 40, _MAX_W + 40),
                        min(pixmap.height() + 40, _MAX_H + 40))
        layout.addWidget(label)
