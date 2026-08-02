"""应用图标:程序内绘制,避免依赖外部图标文件。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from ui.theme import COLORS


def app_icon(size: int = 32) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(COLORS["primary"]))
    p.drawRoundedRect(size * 0.18, size * 0.06, size * 0.64, size * 0.88,
                      size * 0.09, size * 0.09)
    p.setBrush(QColor(COLORS["pin"]))
    p.drawRoundedRect(size * 0.34, 0.0, size * 0.32, size * 0.16,
                      size * 0.06, size * 0.06)
    p.setBrush(QColor("#FFFFFF"))
    w = size * 0.38
    x = size * 0.31
    for y in (size * 0.38, size * 0.52, size * 0.66):
        p.drawRoundedRect(x, y, w, size * 0.06, size * 0.03, size * 0.03)
    p.end()
    return QIcon(pm)
