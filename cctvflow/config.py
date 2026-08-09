"""Configuración funcional y rutas persistentes de CCTVFlow."""

from pathlib import Path


# Rutas calculadas desde el paquete para no depender del directorio actual.
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
RESOURCES_DIR = PACKAGE_DIR / "resources"
CATALOGS_DIR = RESOURCES_DIR / "catalogs"
ART_DIR = RESOURCES_DIR / "art"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
REPORTS_DIR = PROJECT_ROOT / "downloads" / "pdfs"

DIVISIONES = {
    "DCH-SUBTE": {
        "ubicacion_portal": "DCH-SUBTE",
        "archivo_sectores": "sectores.json",
    },
    "DRT": {
        # Debe coincidir exactamente con la opción mostrada en el portal.
        "ubicacion_portal": "DRT",
        "archivo_sectores": "sectores_drt.json",
    },
}


def obtener_configuracion_division(
    division: str,
) -> dict[str, str]:
    """Devuelve una copia de la configuración de una división."""

    try:
        configuracion = DIVISIONES[division]
    except KeyError as error:
        disponibles = ", ".join(DIVISIONES)
        raise ValueError(
            f"División no configurada: {division!r}. "
            f"Divisiones disponibles: {disponibles}"
        ) from error

    return configuracion.copy()


def obtener_ruta_sectores(division: str) -> Path:
    """Obtiene el catálogo de cámaras correspondiente a una división."""

    configuracion = obtener_configuracion_division(division)
    return CATALOGS_DIR / configuracion["archivo_sectores"]

OBSERVACION_DEFAULT = "Mantenimiento CCTV"

TIPO_TAREA_DEFAULT = "Mantencion Programada"

UBICACION_PORTAL_DEFAULT = DIVISIONES["DRT"]["ubicacion_portal"]

TIPO_ACTIVIDAD_DEFAULT = "Mantenimiento Preventivo"

CAUSA_DEFAULT = "CCTV"

RESPONSABLE_DEFAULT = "Louis Rivera"

PARTICIPANTES_DEFAULT = [
    "Louis Rivera",
]

APR_PARTICIPA = False

ALZA_HOMBRE = False

MAXIMO_FOTOS = 15
