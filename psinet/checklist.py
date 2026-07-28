"""Reglas de negocio para los checklist de mantenimiento."""

from __future__ import annotations


ITEMS_CONEXIONES = (
    "ENCODER",
    "POE",
    "ESTADO CONECTOR COAXIAL",
    "ESTADO CABLEADO",
    "SW/IOS/FIRMWARE",
    "CONEXIÓN SERVIDOR",
)
ITEMS_NO_APLICAN_CAMARA_IP = {
    "ENCODER",
    "ESTADO CONECTOR COAXIAL",
}
VARIANTES_ITEMS_CONEXIONES = {
    "CONEXIÓN SERVIDOR": (
        "CONEXIÓN SERVIDOR",
        "CONEXION SERVIDOR",
    ),
}


def variantes_item_conexiones(item: str) -> tuple[str, ...]:
    """Devuelve las escrituras aceptadas para un ítem de conexiones.

    PSINet no usa siempre la misma acentuación en todos sus checklist. La
    descripción canónica conserva la ortografía correcta, pero la búsqueda en
    pantalla admite también las variantes observadas.
    """

    return VARIANTES_ITEMS_CONEXIONES.get(item, (item,))


def estados_conexiones(camara_ip: bool) -> tuple[tuple[str, str], ...]:
    """Devuelve el estado correcto de cada conexión según la tecnología."""

    return tuple(
        (
            item,
            (
                "N/A"
                if camara_ip and item in ITEMS_NO_APLICAN_CAMARA_IP
                else "B"
            ),
        )
        for item in ITEMS_CONEXIONES
    )
