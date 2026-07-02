"""
Proyecto: Cámara CCTV PSINet
Archivo: utils/normalizar.py

Descripción:
Normalización de textos para comparar nombres de áreas y fotos.
"""

import unicodedata


def normalizar(texto):
    """Convierte texto a formato comparable."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    for char in ["/", "-", "_", ".", ",", "(", ")", "[", "]"]:
        texto = texto.replace(char, " ")

    return " ".join(texto.split())
