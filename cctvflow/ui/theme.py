"""Tema visual adaptable para CCTVFlow."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Qt, Signal, Slot
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

THEME_SYSTEM = "system"
THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_OPTIONS = (
    ("Sistema", THEME_SYSTEM),
    ("Oscuro", THEME_DARK),
    ("Claro", THEME_LIGHT),
)
VALID_THEMES = {value for _label, value in THEME_OPTIONS}


APP_STYLESHEET = """
QWidget {
    font-size: 10pt;
}

QGroupBox {
    border: 1px solid palette(mid);
    border-radius: 8px;
    font-weight: 600;
    margin-top: 13px;
    padding: 10px 8px 8px 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}

QLineEdit,
QComboBox,
QDateEdit,
QTimeEdit,
QSpinBox {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 5px;
    min-height: 28px;
    padding: 0 7px;
    selection-background-color: palette(highlight);
    selection-color: palette(highlighted-text);
}

QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QTimeEdit:focus,
QSpinBox:focus,
QListWidget:focus,
QTableWidget:focus,
QTextEdit:focus {
    border: 1px solid palette(highlight);
}

QPushButton {
    background: palette(button);
    border: 1px solid palette(mid);
    border-radius: 5px;
    min-height: 29px;
    padding: 2px 12px;
}

QPushButton:hover {
    border-color: palette(highlight);
}

QPushButton:pressed {
    background: palette(alternate-base);
}

QPushButton:disabled {
    color: palette(mid);
}

QCheckBox {
    min-height: 28px;
    spacing: 7px;
}

QListWidget,
QTableWidget,
QTextEdit,
QTabWidget::pane {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 6px;
}

QHeaderView::section {
    background: palette(button);
    border: 0;
    border-right: 1px solid palette(mid);
    border-bottom: 1px solid palette(mid);
    padding: 6px;
}

QTabBar::tab {
    background: palette(button);
    border: 1px solid palette(mid);
    border-bottom: 0;
    padding: 7px 14px;
}

QTabBar::tab:selected {
    color: palette(highlight);
    font-weight: 600;
}

QProgressBar {
    border: 1px solid palette(mid);
    border-radius: 5px;
    min-height: 18px;
    text-align: center;
}

QProgressBar::chunk {
    background: palette(highlight);
    border-radius: 4px;
}

QSplitter::handle {
    background: palette(window);
}
"""


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e5edf7"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0b1220"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1a2537"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e5edf7"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1d2939"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e5edf7"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#22b8f0"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0ea5e9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Light, QColor("#334155"))
    palette.setColor(QPalette.ColorRole.Midlight, QColor("#273449"))
    palette.setColor(QPalette.ColorRole.Mid, QColor("#41516a"))
    palette.setColor(QPalette.ColorRole.Dark, QColor("#080d16"))
    palette.setColor(QPalette.ColorRole.Shadow, QColor("#05080e"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8492a6"))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor("#6f7c90"),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor("#6f7c90"),
    )
    return palette


def _light_palette() -> QPalette:
    style = QStyleFactory.create("Fusion")
    palette = style.standardPalette() if style else QPalette()
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0798ce"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#007da8"))
    return palette


class ThemeController(QObject):
    """Aplica y persiste la preferencia visual de la aplicación."""

    theme_changed = Signal(str)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._settings = QSettings()
        saved = str(self._settings.value("appearance/theme", THEME_SYSTEM))
        self._mode = saved if saved in VALID_THEMES else THEME_SYSTEM
        self._app.setStyle("Fusion")
        self._app.styleHints().colorSchemeChanged.connect(
            self._system_theme_changed
        )
        self._apply()

    @property
    def mode(self) -> str:
        return self._mode

    def _resolved_mode(self) -> str:
        if self._mode != THEME_SYSTEM:
            return self._mode
        scheme = self._app.styleHints().colorScheme()
        return (
            THEME_DARK
            if scheme == Qt.ColorScheme.Dark
            else THEME_LIGHT
        )

    def _apply(self) -> None:
        resolved = self._resolved_mode()
        palette = (
            _dark_palette()
            if resolved == THEME_DARK
            else _light_palette()
        )
        self._app.setPalette(palette)
        self._app.setStyleSheet(APP_STYLESHEET)
        self._app.setProperty("cctvflowResolvedTheme", resolved)
        self.theme_changed.emit(self._mode)

    @Slot(str)
    def set_mode(self, mode: str) -> None:
        if mode not in VALID_THEMES or mode == self._mode:
            return
        self._mode = mode
        self._settings.setValue("appearance/theme", mode)
        self._apply()

    def _system_theme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if self._mode == THEME_SYSTEM:
            self._apply()
