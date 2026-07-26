"""Punto de entrada de la interfaz gráfica de CCTVFlow."""

import sys

from PySide6.QtWidgets import QApplication

from gui.ventana import VentanaCCTVFlow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CCTVFlow")

    ventana = VentanaCCTVFlow()
    ventana.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
