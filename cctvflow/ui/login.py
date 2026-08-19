"""Inicio de sesión interactivo del agente de escritorio."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Slot
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from cctvflow.server_client import (
    AgentIdentity,
    CCTVFlowServerClient,
    ServerClientError,
)

RUTA_LOGO = Path(__file__).resolve().parent / "assets" / "cctvflow_logo.svg"


class LoginDialog(QDialog):
    """Valida al usuario Web sin almacenar su contraseña."""

    def __init__(
        self,
        server_client: CCTVFlowServerClient | None,
        *,
        configuration_error: str | None = None,
    ) -> None:
        super().__init__()
        self.server_client = server_client
        self.identity: AgentIdentity | None = None
        self.offline = False
        self._settings = QSettings()

        self.setWindowTitle("Iniciar sesión · CCTVFlow")
        self.setModal(True)
        self.setMinimumWidth(470)
        self._build_ui(configuration_error)

    def _build_ui(self, configuration_error: str | None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)

        logo = QSvgWidget(str(RUTA_LOGO))
        logo.setFixedSize(310, 70)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Acceso al agente de mantenimiento")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        explanation = QLabel(
            "Usa la misma cuenta de CCTVFlow Web. La contraseña se envía "
            "únicamente por HTTPS y no se guarda en este equipo."
        )
        explanation.setWordWrap(True)
        explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(explanation)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Usuario de CCTVFlow Web")
        self.username.setText(
            str(self._settings.value("login/username", ""))
        )
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Contraseña")
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        layout.addLayout(form)

        self.show_password = QCheckBox("Mostrar contraseña")
        layout.addWidget(self.show_password)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(36)
        if configuration_error:
            self.status.setText(configuration_error)
        elif self.server_client is None:
            self.status.setText(
                "Este equipo no tiene configurado el acceso a CCTVFlow Web."
            )
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.offline_button = QPushButton("Trabajar sin conexión")
        self.exit_button = QPushButton("Salir")
        self.login_button = QPushButton("Iniciar sesión")
        self.login_button.setDefault(True)
        self.login_button.setEnabled(self.server_client is not None)
        buttons.addWidget(self.offline_button)
        buttons.addStretch()
        buttons.addWidget(self.exit_button)
        buttons.addWidget(self.login_button)
        layout.addLayout(buttons)

        self.show_password.toggled.connect(self._toggle_password)
        self.login_button.clicked.connect(self._login)
        self.offline_button.clicked.connect(self._continue_offline)
        self.exit_button.clicked.connect(self.reject)
        self.password.returnPressed.connect(self._login)

        if self.username.text():
            self.password.setFocus()
        else:
            self.username.setFocus()

    @Slot(bool)
    def _toggle_password(self, visible: bool) -> None:
        mode = (
            QLineEdit.EchoMode.Normal
            if visible
            else QLineEdit.EchoMode.Password
        )
        self.password.setEchoMode(mode)

    def _set_busy(self, busy: bool) -> None:
        self.username.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.login_button.setEnabled(not busy and self.server_client is not None)
        self.offline_button.setEnabled(not busy)
        self.exit_button.setEnabled(not busy)

    @Slot()
    def _login(self) -> None:
        if self.server_client is None:
            return

        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.status.setText("Ingresa tu usuario y contraseña.")
            return

        self._set_busy(True)
        self.status.setText("Verificando cuenta…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            identity = self.server_client.login(username, password)
        except ServerClientError as error:
            if error.status_code == 401:
                message = "Usuario o contraseña incorrectos para este equipo."
            elif error.status_code == 429:
                message = "Demasiados intentos. Espera unos minutos."
            else:
                message = str(error)
            self.password.clear()
            self.password.setFocus()
            self.status.setText(message)
            return
        finally:
            QApplication.restoreOverrideCursor()
            self._set_busy(False)

        self.identity = identity
        self._settings.setValue("login/username", identity.username)
        self.accept()

    @Slot()
    def _continue_offline(self) -> None:
        answer = QMessageBox.question(
            self,
            "Trabajar sin conexión",
            "La automatización local seguirá disponible, pero esta sesión no "
            "enviará estados ni auditoría a CCTVFlow Web. ¿Deseas continuar?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.offline = True
            self.accept()
