"""Punto de entrada de la interfaz gráfica de CCTVFlow."""

import sys

from PySide6.QtWidgets import QApplication

from cctvflow.server_client import ServerClientError, configured_server_client
from cctvflow.ui.login import LoginDialog
from cctvflow.ui.theme import ThemeController
from cctvflow.ui.window import VentanaCCTVFlow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CCTVFlow")
    app.setOrganizationName("CCTVFlow")

    theme_controller = ThemeController(app)

    configuration_error = None
    try:
        server_client = configured_server_client()
    except ServerClientError as error:
        server_client = None
        configuration_error = str(error)

    login = LoginDialog(
        server_client,
        configuration_error=configuration_error,
    )
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return 0

    ventana = VentanaCCTVFlow(
        theme_controller=theme_controller,
        server_client=None if login.offline else server_client,
        server_autoconfigure=not login.offline,
        user_identity=login.identity,
    )
    ventana.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
