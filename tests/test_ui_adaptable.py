from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication, QLineEdit

    from cctvflow.ui.login import LoginDialog
    from cctvflow.ui.theme import THEME_DARK, THEME_LIGHT, ThemeController
    from cctvflow.ui.window import VentanaCCTVFlow
except (ImportError, ModuleNotFoundError):  # pragma: no cover
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 no está instalado.")
class InterfazAdaptableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setOrganizationName("CCTVFlowTests")
        cls.app.setApplicationName("CCTVFlowTests")

    def test_tema_oscuro_y_claro_cambian_la_paleta(self) -> None:
        controller = ThemeController(self.app)

        controller.set_mode(THEME_DARK)
        dark = self.app.palette().color(QPalette.ColorRole.Window)
        self.assertLess(dark.lightness(), 128)

        controller.set_mode(THEME_LIGHT)
        light = self.app.palette().color(QPalette.ColorRole.Window)
        self.assertGreater(light.lightness(), 128)

    def test_formulario_no_colapsa_en_1366_por_728(self) -> None:
        controller = ThemeController(self.app)
        controller.set_mode(THEME_DARK)
        window = VentanaCCTVFlow(theme_controller=controller)
        window.resize(1366, 728)
        window.show()
        self.app.processEvents()

        self.assertGreaterEqual(window.grupo_configuracion.height(), 200)
        self.assertGreaterEqual(window.combo_division.height(), 28)
        self.assertTrue(all(size >= 125 for size in window.divisor_vertical.sizes()))
        window.close()

    def test_login_oculta_password_y_ofrece_modo_local(self) -> None:
        dialog = LoginDialog(None)
        self.assertEqual(dialog.password.echoMode(), QLineEdit.EchoMode.Password)
        self.assertFalse(dialog.login_button.isEnabled())
        self.assertTrue(dialog.offline_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
