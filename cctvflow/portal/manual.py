"""Confirmaciones manuales compartidas por la GUI y usos interactivos."""

from __future__ import annotations

from collections.abc import Callable


ConfirmacionManual = Callable[[str], None]


def esperar_confirmacion_manual(
    mensaje: str,
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Pausa el flujo usando la GUI o la consola según el llamador."""

    if confirmar_manual is not None:
        confirmar_manual(mensaje)
        return

    input(f"{mensaje}\nPresiona Enter para continuar...")
