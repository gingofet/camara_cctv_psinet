from pathlib import Path


# ==========================================================
# DIVISIÓN ACTIVA
# ==========================================================

# Cambia únicamente este valor para trabajar con otra división.
DIVISION_ACTIVA = "DRT"

DIVISIONES = {
    "DCH-SUBTE": {
        "ubicacion_psinet": "DCH-SUBTE",
        "archivo_sectores": "sectores.json",
    },
    "DRT": {
        # Debe coincidir exactamente con la opción mostrada en PSINet.
        "ubicacion_psinet": "DRT",
        "archivo_sectores": "sectores_drt.json",
    },
}


DATA_DIR = Path(__file__).resolve().parent


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
    return DATA_DIR / configuracion["archivo_sectores"]


CONFIGURACION_DIVISION = obtener_configuracion_division(DIVISION_ACTIVA)
SECTORES_PATH = obtener_ruta_sectores(DIVISION_ACTIVA)


# ==========================================================
# CONFIGURACIÓN DE PSINET
# ==========================================================

OBSERVACION_DEFAULT = "Mantenimiento CCTV"

TIPO_TAREA_DEFAULT = "Mantencion Programada"

UBICACION_DEFAULT = CONFIGURACION_DIVISION["ubicacion_psinet"]

TIPO_ACTIVIDAD_DEFAULT = "Mantenimiento Preventivo"

CAUSA_DEFAULT = "CCTV"

RESPONSABLE_DEFAULT = "Louis Rivera"

PARTICIPANTES_DEFAULT = [
    "Louis Rivera",
]

APR_PARTICIPA = False

ALZA_HOMBRE = False

MAXIMO_FOTOS = 15
