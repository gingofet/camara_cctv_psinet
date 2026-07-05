"""
Proyecto: Cámara CCTV PSINet
Archivo: utils/archivos.py

Descripción:
Funciones reutilizables para leer y escribir archivos JSON.
"""

import json


def cargar_json(path):
    """Carga un archivo JSON desde disco."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(path, data):
    """Guarda datos Python en formato JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
