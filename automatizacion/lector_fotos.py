"""
Proyecto: Cámara CCTV PSINet
Archivo: lector_fotos.py

Descripción:
Lee la carpeta de evidencias fotográficas y detecta automáticamente a qué
cámara/área pertenece cada foto, comparando el nombre del archivo con el
catálogo de sectores definido en data/sectores.json.

Este módulo genera evidencias.json, que luego será utilizado por la
automatización de PSINet para saber qué fotos subir en cada tarea.
"""

import json
import unicodedata
from pathlib import Path


# ==========================================================
# RUTAS BASE DEL PROYECTO
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

SECTORES_PATH = BASE_DIR / "data" / "sectores.json"
FOTOS_DIR = BASE_DIR / "fotos"
EVIDENCIAS_PATH = BASE_DIR / "evidencias.json"

# Extensiones de imagen válidas para evidencias.
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


# ==========================================================
# NORMALIZACIÓN DE TEXTO
# ==========================================================

def normalizar(texto):
    """
    Convierte un texto a una versión más fácil de comparar.

    Ejemplo:
        "20180-Taller BIN-Eje 12 / Eje 18"
        -> "20180 taller bin eje 12 eje 18"

    Esto permite comparar nombres aunque tengan:
    - Mayúsculas/minúsculas distintas.
    - Acentos.
    - Guiones.
    - Slash.
    - Puntos o comas.
    """
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    for char in ["/", "-", "_", ".", ",", "(", ")", "[", "]"]:
        texto = texto.replace(char, " ")

    return " ".join(texto.split())


# ==========================================================
# CARGA DE DATOS
# ==========================================================

def cargar_json(path):
    """
    Carga un archivo JSON desde disco.

    Parámetros:
        path: Ruta del archivo JSON.

    Retorna:
        Contenido del JSON como estructura Python.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_areas(sectores):
    """
    Transforma el catálogo de sectores en una lista plana de áreas.

    Entrada esperada:
        {
            "BIN": ["13 BIN 2", "14 Bin Exterior 5"],
            "TAP": ["TAP 19 Exterior SEU 06"]
        }

    Salida:
        [
            {
                "sector": "BIN",
                "area": "13 BIN 2",
                "normalizado": "13 bin 2"
            },
            ...
        ]

    La versión normalizada permite comparar contra nombres de archivo.
    """
    areas = []

    for sector, lista_areas in sectores.items():
        for area in lista_areas:
            areas.append({
                "sector": sector,
                "area": area,
                "normalizado": normalizar(area),
            })

    return areas


# ==========================================================
# DETECCIÓN DE ÁREA SEGÚN NOMBRE DE FOTO
# ==========================================================

def detectar_area_en_foto(foto, areas):
    """
    Intenta detectar a qué área pertenece una foto.

    Usa el nombre del archivo, sin extensión, y lo compara contra todas las
    áreas registradas en sectores.json.

    Ejemplo:
        Archivo:
            "13 BIN 2_001.jpg"

        Área detectada:
            "13 BIN 2"

    Si existen varias coincidencias, se escoge la más larga/específica.
    Esto evita que un nombre corto como "13 Bin" gane sobre "13 BIN 2".
    """
    nombre_foto = normalizar(foto.stem)
    coincidencias = []

    for item in areas:
        area_normalizada = item["normalizado"]

        if area_normalizada in nombre_foto:
            coincidencias.append(item)

    if not coincidencias:
        return None

    coincidencias.sort(
        key=lambda x: len(x["normalizado"]),
        reverse=True,
    )

    return coincidencias[0]


# ==========================================================
# FLUJO PRINCIPAL
# ==========================================================

def main():
    """
    Lee la carpeta de fotos, identifica áreas y genera evidencias.json.
    """
    FOTOS_DIR.mkdir(exist_ok=True)

    sectores = cargar_json(SECTORES_PATH)
    areas = obtener_areas(sectores)

    fotos = [
        archivo
        for archivo in FOTOS_DIR.rglob("*")
        if archivo.suffix.lower() in EXTENSIONES
    ]

    evidencias = {}
    no_detectadas = []

    for foto in fotos:
        area_detectada = detectar_area_en_foto(foto, areas)

        if area_detectada is None:
            no_detectadas.append(str(foto))
            continue

        area = area_detectada["area"]
        sector = area_detectada["sector"]

        if area not in evidencias:
            evidencias[area] = {
                "sector": sector,
                "fotos": [],
            }

        evidencias[area]["fotos"].append(str(foto))

    with open(EVIDENCIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "evidencias": evidencias,
                "no_detectadas": no_detectadas,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n=== Evidencias detectadas desde carpeta ===\n")

    for area, data in evidencias.items():
        print(f"[{data['sector']}] {area}: {len(data['fotos'])} foto(s)")

        for foto in data["fotos"]:
            print(f"  - {foto}")

    if no_detectadas:
        print("\nFotos no detectadas:\n")

        for foto in no_detectadas:
            print(f"  - {foto}")

    print(f"\nArchivo generado: {EVIDENCIAS_PATH}")


if __name__ == "__main__":
    main()
