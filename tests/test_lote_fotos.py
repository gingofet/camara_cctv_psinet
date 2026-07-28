from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gui.lote_fotos import analizar_carpeta, validar_lote


class LoteFotosTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalogo = {
            "CHANCADO OXIDOS": [
                "RTAPIP001-Vista oruga 1",
                "Cámara Sala 3",
            ],
            "ELECTROWING": [
                "RTSTEW-P010-MAQ 2-Ingreso Nave",
            ],
        }

    def test_detecta_y_agrupa_una_carpeta_recursiva(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            subcarpeta = carpeta / "Turno_A"
            subcarpeta.mkdir()

            nombres = [
                "RTAPIP001-Vista_oruga_1_0001.jpg",
                "RTAPIP001-Vista_oruga_1_0002.jpg",
                "RTSTEW-P010-MAQ_2-Ingreso_Nave_0001.png",
            ]

            for nombre in nombres:
                (subcarpeta / nombre).touch()

            (carpeta / "sin_coincidencia_0001.jpg").touch()

            lote = analizar_carpeta(carpeta, self.catalogo)

            self.assertEqual(lote.cantidad_fotos, 3)
            self.assertEqual(
                len(lote.fotos_por_camara["RTAPIP001-Vista oruga 1"]),
                2,
            )
            self.assertEqual(
                lote.sector_por_camara[
                    "RTSTEW-P010-MAQ 2-Ingreso Nave"
                ],
                "ELECTROWING",
            )
            self.assertEqual(len(lote.no_detectadas), 1)

    def test_no_confunde_numero_de_camara_con_correlativo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / "Camara_Sala_3_0001.jpg").touch()

            lote = analizar_carpeta(carpeta, self.catalogo)

            self.assertIn("Cámara Sala 3", lote.fotos_por_camara)

    def test_valida_limite_de_trece_evidencias(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)

            for correlativo in range(1, 15):
                nombre = (
                    "RTAPIP001-Vista_oruga_1_"
                    f"{correlativo:04d}.jpg"
                )
                (carpeta / nombre).touch()

            lote = analizar_carpeta(carpeta, self.catalogo)
            errores = validar_lote(
                lote,
                ["RTAPIP001-Vista oruga 1"],
            )

            self.assertEqual(len(errores), 1)
            self.assertIn("el máximo es 13", errores[0])


if __name__ == "__main__":
    unittest.main()
