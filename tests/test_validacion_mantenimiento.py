from __future__ import annotations

import contextlib
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from cctvflow.checkpoint import (
    ESTADO_COMPLETADO,
    ESTADO_EN_PROCESO,
    ESTADO_INCOMPLETO,
    actualizar_estado,
    cargar_checkpoint,
    crear_checkpoint,
    plan_pendiente,
    resumen_checkpoint,
)
from cctvflow.models import MantenimientoPlanificado
from cctvflow.portal.checklist_rules import (
    estados_conexiones,
    variantes_item_conexiones,
)
from cctvflow.portal.reports import (
    PdfMantenimientoIncompletoError,
    validar_pdf_mantenimiento,
)
from cctvflow.portal.photo_fields import selector_input_foto
from cctvflow.portal.manual import esperar_confirmacion_manual

try:
    from cctvflow.ui.runner import (
        EjecucionDetenidaError,
        EjecutorMantenimientos,
    )
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    EjecucionDetenidaError = None
    EjecutorMantenimientos = None


class ConfirmacionManualTest(unittest.TestCase):
    def test_gui_usa_callback_en_lugar_de_input(self) -> None:
        mensajes: list[str] = []

        with patch("builtins.input") as entrada:
            esperar_confirmacion_manual(
                "Selecciona la cámara en el portal.",
                mensajes.append,
            )

        entrada.assert_not_called()
        self.assertEqual(
            mensajes,
            ["Selecciona la cámara en el portal."],
        )

    def test_terminal_conserva_input_como_respaldo(self) -> None:
        with patch("builtins.input", return_value="") as entrada:
            esperar_confirmacion_manual(
                "Selecciona la cámara en el portal."
            )

        entrada.assert_called_once()


class ConexionesTest(unittest.TestCase):
    def test_camara_ip_usa_na_en_encoder_y_coaxial(self) -> None:
        estados = dict(estados_conexiones(camara_ip=True))

        self.assertEqual(estados["ENCODER"], "N/A")
        self.assertEqual(estados["ESTADO CONECTOR COAXIAL"], "N/A")
        self.assertEqual(estados["POE"], "B")
        self.assertEqual(estados["ESTADO CABLEADO"], "B")
        self.assertEqual(estados["SW/IOS/FIRMWARE"], "B")
        self.assertEqual(estados["CONEXIÓN SERVIDOR"], "B")

    def test_conexion_servidor_admite_texto_con_y_sin_tilde(self) -> None:
        variantes = variantes_item_conexiones("CONEXIÓN SERVIDOR")

        self.assertIn("CONEXIÓN SERVIDOR", variantes)
        self.assertIn("CONEXION SERVIDOR", variantes)

    def test_camara_no_ip_conserva_estado_bueno(self) -> None:
        estados = dict(estados_conexiones(camara_ip=False))

        self.assertTrue(all(estado == "B" for estado in estados.values()))


class SelectorFotografiasTest(unittest.TestCase):
    def test_cada_fotografia_usa_un_input_unico_desde_la_primera(self) -> None:
        self.assertEqual(selector_input_foto(1), "#inputFoto1")
        self.assertEqual(selector_input_foto(2), "#inputFoto2")
        self.assertEqual(selector_input_foto(3), "#inputFoto3")

    def test_rechaza_indices_anteriores_al_primero(self) -> None:
        with self.assertRaisesRegex(ValueError, "comenzar en 1"):
            selector_input_foto(0)


class ValidacionPdfTest(unittest.TestCase):
    @staticmethod
    def _crear_pdf(ruta: Path, paginas: int) -> None:
        escritor = PdfWriter()

        for _ in range(paginas):
            escritor.add_blank_page(width=595, height=842)

        with ruta.open("wb") as archivo:
            escritor.write(archivo)

    def test_acepta_informe_con_todas_las_fotografias(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "mantenimiento.pdf"
            self._crear_pdf(ruta, paginas=4)

            paginas = validar_pdf_mantenimiento(
                ruta,
                cantidad_fotos_esperadas=3,
            )

            self.assertEqual(paginas, 4)

    def test_rechaza_pdf_al_que_le_falta_la_ultima_foto(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "mantenimiento_incompleto.pdf"
            self._crear_pdf(ruta, paginas=3)

            with self.assertRaisesRegex(
                PdfMantenimientoIncompletoError,
                "se esperaban al menos 4",
            ) as contexto:
                validar_pdf_mantenimiento(
                    ruta,
                    cantidad_fotos_esperadas=3,
                )

            self.assertEqual(contexto.exception.paginas_reales, 3)
            self.assertEqual(contexto.exception.paginas_minimas, 4)
            self.assertEqual(contexto.exception.ruta_pdf, ruta)


class CheckpointEjecucionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = [
            MantenimientoPlanificado(
                sector="AREA 1",
                camara="CAMARA 1",
                hora_inicio="01:00",
                hora_fin="01:10",
            ),
            MantenimientoPlanificado(
                sector="AREA 1",
                camara="CAMARA 2",
                hora_inicio="01:10",
                hora_fin="01:20",
            ),
            MantenimientoPlanificado(
                sector="AREA 2",
                camara="CAMARA 3",
                hora_inicio="01:20",
                hora_fin="01:30",
            ),
        ]

    def _crear(self, ruta: Path) -> None:
        crear_checkpoint(
            division="DRT",
            fecha_mantenimiento="2026-07-28",
            plan=self.plan,
            participantes=["Louis Rivera"],
            apr_participa=False,
            equipo_alza_hombre=False,
            observacion="Prueba",
            fotos_por_camara={
                item.camara: [f"/fotos/{item.camara}.jpg"]
                for item in self.plan
            },
            fotos_art_por_sector={
                "AREA 1": ["/art/a.jpg", "/art/b.jpg"],
                "AREA 2": ["/art/c.jpg", "/art/d.jpg"],
            },
            eliminar_fotos_tras_exito=True,
            eliminar_art_tras_exito=True,
            ruta=ruta,
        )

    def test_reanuda_solo_camaras_que_nunca_comenzaron(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "checkpoint.json"
            self._crear(ruta)
            actualizar_estado(
                "CAMARA 1",
                ESTADO_COMPLETADO,
                ruta=ruta,
            )
            actualizar_estado(
                "CAMARA 2",
                ESTADO_INCOMPLETO,
                detalle="PDF de tres páginas",
                ruta=ruta,
            )

            datos = cargar_checkpoint(ruta)
            self.assertIsNotNone(datos)
            pendientes = plan_pendiente(datos)

            self.assertEqual(
                [item.camara for item in pendientes],
                ["CAMARA 3"],
            )

    def test_un_estado_en_proceso_no_se_repite_automaticamente(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "checkpoint.json"
            self._crear(ruta)
            actualizar_estado(
                "CAMARA 1",
                ESTADO_EN_PROCESO,
                ruta=ruta,
            )

            datos = cargar_checkpoint(ruta)
            self.assertIsNotNone(datos)
            pendientes = plan_pendiente(datos)
            resumen = resumen_checkpoint(datos)

            self.assertEqual(
                [item.camara for item in pendientes],
                ["CAMARA 2", "CAMARA 3"],
            )
            self.assertEqual(resumen[ESTADO_EN_PROCESO], 1)


@unittest.skipIf(
    EjecutorMantenimientos is None,
    "PySide6 no está instalado en el entorno de pruebas.",
)
class ContinuidadLoteTest(unittest.TestCase):
    def test_detener_desbloquea_una_confirmacion_manual(self) -> None:
        ejecutor = EjecutorMantenimientos(
            division="DRT",
            plan=[],
            participantes=["Louis Rivera"],
            apr_participa=False,
            equipo_alza_hombre=False,
            fotos_art=[],
            observacion="Prueba",
        )
        errores: list[BaseException] = []

        def esperar() -> None:
            try:
                ejecutor._esperar_confirmacion_manual(
                    "Selecciona la cámara."
                )
            except BaseException as error:
                errores.append(error)

        hilo = threading.Thread(target=esperar)
        hilo.start()
        self.assertTrue(
            ejecutor._esperando_confirmacion.wait(timeout=1)
        )
        ejecutor.solicitar_detencion()
        hilo.join(timeout=1)

        self.assertFalse(hilo.is_alive())
        self.assertEqual(len(errores), 1)
        self.assertIsInstance(errores[0], EjecucionDetenidaError)

    def test_pdf_incompleto_no_aborta_la_camara_siguiente(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            checkpoint = carpeta / "checkpoint.json"
            plan = [
                MantenimientoPlanificado(
                    "AREA",
                    "CAMARA FALLIDA",
                    "01:00",
                    "01:10",
                ),
                MantenimientoPlanificado(
                    "AREA",
                    "CAMARA SIGUIENTE",
                    "01:10",
                    "01:20",
                ),
            ]
            fotos_por_camara = {
                "CAMARA FALLIDA": [str(carpeta / "fallida.jpg")],
                "CAMARA SIGUIENTE": [str(carpeta / "siguiente.jpg")],
            }
            fotos_art_por_sector = {
                "AREA": [
                    str(carpeta / "art_anverso.jpg"),
                    str(carpeta / "art_reverso.jpg"),
                ]
            }
            crear_checkpoint(
                division="DRT",
                fecha_mantenimiento="2026-07-28",
                plan=plan,
                participantes=["Louis Rivera"],
                apr_participa=False,
                equipo_alza_hombre=False,
                observacion="Prueba",
                fotos_por_camara=fotos_por_camara,
                fotos_art_por_sector=fotos_art_por_sector,
                eliminar_fotos_tras_exito=False,
                eliminar_art_tras_exito=False,
                ruta=checkpoint,
            )
            pdf_incompleto = carpeta / "incompleto.pdf"
            pdf_correcto = carpeta / "correcto.pdf"
            ejecutor = EjecutorMantenimientos(
                division="DRT",
                fecha_mantenimiento="2026-07-28",
                plan=plan,
                participantes=["Louis Rivera"],
                apr_participa=False,
                equipo_alza_hombre=False,
                fotos_art=[],
                observacion="Prueba",
                fotos_por_camara=fotos_por_camara,
                fotos_art_por_sector=fotos_art_por_sector,
                checkpoint_path=str(checkpoint),
            )
            guardados: list[str] = []

            def guardar(_page, cantidad_fotos_esperadas):
                self.assertEqual(cantidad_fotos_esperadas, 3)
                guardados.append(plan[len(guardados)].camara)

                if len(guardados) == 1:
                    raise PdfMantenimientoIncompletoError(
                        pdf_incompleto,
                        paginas_reales=3,
                        paginas_minimas=4,
                        cantidad_fotos_esperadas=3,
                    )

                return pdf_correcto

            with (
                patch(
                    "cctvflow.ui.runner.iniciar_navegador",
                    return_value=contextlib.nullcontext(object()),
                ),
                patch("cctvflow.ui.runner.iniciar_sesion"),
                patch("cctvflow.ui.runner.crear_mantenimiento"),
                patch.object(
                    ejecutor,
                    "_guardar_y_descargar",
                    side_effect=guardar,
                ),
            ):
                ejecutor.ejecutar()

            datos = cargar_checkpoint(checkpoint)
            self.assertIsNotNone(datos)
            self.assertEqual(
                guardados,
                ["CAMARA FALLIDA", "CAMARA SIGUIENTE"],
            )
            self.assertEqual(
                datos["resultados"]["CAMARA FALLIDA"]["estado"],
                ESTADO_INCOMPLETO,
            )
            self.assertEqual(
                datos["resultados"]["CAMARA SIGUIENTE"]["estado"],
                ESTADO_COMPLETADO,
            )


if __name__ == "__main__":
    unittest.main()
