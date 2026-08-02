"""界面主题:色板与全局样式(QSS)。色值以 docs/design-spec.md 为准。"""

COLORS = {
    "bg": "#F0F6FB",
    "primary": "#5B9BD5",
    "primary_hover": "#4A87C3",
    "card_bg": "#FFFFFF",
    "card_hover": "#EAF3FB",
    "text_main": "#2B3A4A",
    "text_sub": "#8CA3B8",
    "divider": "#E3EDF6",
    "pin": "#3E8EC7",
    "danger": "#D9534F",
}

APP_FONT = "Microsoft YaHei"


def stylesheet() -> str:
    c = COLORS
    return f"""
QWidget {{
    font-family: "{APP_FONT}";
    color: {c["text_main"]};
    font-size: 12px;
}}
QFrame#Shell {{
    background: {c["bg"]};
    border-radius: 12px;
    border: 1px solid {c["divider"]};
}}
QLabel#appTitle {{
    font-size: 15px;
    font-weight: 600;
}}
QLineEdit#searchBox {{
    background: {c["card_bg"]};
    border: 1px solid {c["divider"]};
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    selection-background-color: {c["primary"]};
}}
QLineEdit#searchBox:focus {{
    border: 1px solid {c["primary"]};
}}
QPushButton#btnClose {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {c["text_sub"]};
    font-size: 14px;
}}
QPushButton#btnClose:hover {{
    background: {c["danger"]};
    color: #FFFFFF;
}}
QScrollArea#cardScroll {{
    border: none;
    background: transparent;
}}
QScrollArea#cardScroll > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {c["divider"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c["primary"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QFrame#card {{
    background: {c["card_bg"]};
    border: 1px solid {c["divider"]};
    border-radius: 8px;
}}
QFrame#card:hover {{
    background: {c["card_hover"]};
}}
QFrame#cardPinned {{
    background: {c["card_bg"]};
    border: 1px solid {c["primary"]};
    border-left: 3px solid {c["pin"]};
    border-radius: 8px;
}}
QFrame#cardPinned:hover {{
    background: {c["card_hover"]};
}}
QLabel#pinBadge {{
    color: {c["pin"]};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#cardText {{
    color: {c["text_main"]};
    font-size: 12px;
}}
QLabel#cardTime {{
    color: {c["text_sub"]};
    font-size: 11px;
}}
QLabel#cardImage {{
    border: 1px solid {c["divider"]};
    border-radius: 6px;
    background: {c["bg"]};
}}
QPushButton#btnMini {{
    background: transparent;
    border: 1px solid {c["divider"]};
    border-radius: 6px;
    padding: 3px 10px;
    color: {c["text_main"]};
    font-size: 11px;
}}
QPushButton#btnMini:hover {{
    border-color: {c["primary"]};
    color: {c["primary"]};
}}
QPushButton#btnMiniDanger {{
    background: transparent;
    border: 1px solid {c["divider"]};
    border-radius: 6px;
    padding: 3px 10px;
    color: {c["danger"]};
    font-size: 11px;
}}
QPushButton#btnMiniDanger:hover {{
    background: {c["danger"]};
    color: #FFFFFF;
}}
QLabel#emptyHint {{
    color: {c["text_sub"]};
    font-size: 13px;
}}
QLabel#footer {{
    color: {c["text_sub"]};
    font-size: 11px;
    padding: 2px 4px;
}}
"""
