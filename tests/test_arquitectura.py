from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from cctvflow.config import obtener_ruta_sectores
from cctvflow.models import SolicitudMantenimiento
from cctvflow.portal.authentication import obtener_credenciales


ROOT = Path(__file__).resolve().parents[1]
EXTENSIONES_TEXTO = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".svg",
    ".txt",
    ".yml",
    ".yaml",
}
ARCHIVOS_ADICIONALES = {".env.example", ".gitignore"}
TERMINO_NO_PERMITIDO = "".join(("psi", "net"))
DIRECTORIOS_MANTENIDOS = ("cctvflow", "tests")
ARCHIVOS_RAIZ_MANTENIDOS = {
    ".env.example",
    ".gitignore",
    "CODE_REVIEW.md",
    "README.md",
    "ROADMAP.md",
    "cctvflow_gui.py",
    "pyproject.toml",
    "requirements.txt",
}


def iterar_archivos_mantenidos() -> list[Path]:
    """Devuelve solo archivos que forman parte mantenida de CCTVFlow.

    Los datos de ``runtime``, las descargas y otros proyectos vecinos no son
    código de esta aplicación y no deben volver no determinista esta prueba.
    """
    archivos: list[Path] = []

    for directorio in DIRECTORIOS_MANTENIDOS:
        raiz = ROOT / directorio
        if raiz.is_dir():
            archivos.extend(ruta for ruta in raiz.rglob("*") if ruta.is_file())

    archivos.extend(
        ROOT / nombre
        for nombre in ARCHIVOS_RAIZ_MANTENIDOS
        if (ROOT / nombre).is_file()
    )

    return archivos


class ArquitecturaTest(unittest.TestCase):
    def test_catalogos_residen_dentro_del_paquete(self) -> None:
        for division in ("DCH-SUBTE", "DRT"):
            ruta = obtener_ruta_sectores(division)
            self.assertTrue(ruta.is_file())
            self.assertIn("cctvflow/resources/catalogs", ruta.as_posix())

    def test_solicitud_rechaza_campos_requeridos_vacios(self) -> None:
        with self.assertRaisesRegex(ValueError, "area"):
            SolicitudMantenimiento(
                area="",
                area_busqueda="CAMARA",
                division="DRT",
                ubicacion_portal="DRT",
                fecha_mantenimiento="2026-07-28",
                hora_inicio="01:00",
                hora_fin="01:10",
                participantes=("Louis Rivera",),
                apr_participa=False,
                equipo_alza_hombre=False,
                fotos=(),
                observacion="Mantenimiento",
                dejar_campo_extra=False,
                camara_ip=True,
            )

    def test_solicitud_rechaza_fecha_futura(self) -> None:
        with self.assertRaisesRegex(ValueError, "futuro"):
            SolicitudMantenimiento(
                area="CAMARA",
                area_busqueda="CAMARA",
                division="DRT",
                ubicacion_portal="DRT",
                fecha_mantenimiento="2999-01-01",
                hora_inicio="01:00",
                hora_fin="01:10",
                participantes=("Louis Rivera",),
                apr_participa=False,
                equipo_alza_hombre=False,
                fotos=(),
                observacion="Mantenimiento",
                dejar_campo_extra=False,
                camara_ip=True,
            )

    def test_credenciales_usan_nombres_genericos_de_cctvflow(self) -> None:
        entorno = {
            "CCTVFLOW_PORTAL_URL": "https://portal.invalid/login",
            "CCTVFLOW_PORTAL_USER": "usuario",
            "CCTVFLOW_PORTAL_PASSWORD": "secreto",
        }

        with patch.dict(os.environ, entorno, clear=True):
            self.assertEqual(
                obtener_credenciales(),
                (
                    "https://portal.invalid/login",
                    "usuario",
                    "secreto",
                ),
            )

    def test_no_reaparece_la_identidad_externa_anterior(self) -> None:
        infracciones: list[str] = []

        for ruta in iterar_archivos_mantenidos():
            relativa = ruta.relative_to(ROOT)

            if any(
                parte in {"__pycache__"}
                for parte in relativa.parts
            ):
                continue

            if (
                ruta.suffix.casefold() not in EXTENSIONES_TEXTO
                and ruta.name not in ARCHIVOS_ADICIONALES
            ):
                continue

            if TERMINO_NO_PERMITIDO in relativa.as_posix().casefold():
                infracciones.append(str(relativa))
                continue

            contenido = ruta.read_text(
                encoding="utf-8",
                errors="ignore",
            ).casefold()

            if TERMINO_NO_PERMITIDO in contenido:
                infracciones.append(str(relativa))

        self.assertEqual(infracciones, [])


if __name__ == "__main__":
    unittest.main()
