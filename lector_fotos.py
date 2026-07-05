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

from utils.archivos import cargar_json, guardar_json
from utils.normalizar import normalizar
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

    Si existen varias coincidencias, se escoge la más larga/específica.

    Además, evita aceptar coincidencias demasiado genéricas cuando el nombre
    de la foto tiene más información que el área detectada.

    Ejemplo a evitar:
        Foto: "13 BIN exterior 5.jpg"
        Área genérica: "13 Bin"

    En ese caso, se considera dudosa y no se asigna automáticamente.
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

    mejor = coincidencias[0]
    area_detectada = mejor["normalizado"]

    palabras_foto = set(nombre_foto.split())
    palabras_area = set(area_detectada.split())

    palabras_extra = palabras_foto - palabras_area

    if len(palabras_area) <= 2 and palabras_extra:
        return None

    return mejor

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

    
        guardar_json(EVIDENCIAS_PATH, {
    "evidencias": evidencias,
    "no_detectadas": no_detectadas,
})

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
