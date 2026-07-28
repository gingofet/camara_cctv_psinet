"""Utilidades puras para la carga de fotografías en PSINet."""

from __future__ import annotations


def selector_input_foto(indice: int) -> str:
    """Devuelve el selector único del campo fotográfico indicado."""

    if indice < 1:
        raise ValueError("El índice de fotografía debe comenzar en 1.")

    return f"#inputFoto{indice}"
