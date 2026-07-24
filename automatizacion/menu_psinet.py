"""
Proyecto: Cámara CCTV PSINet
Archivo: menu_psinet.py

Descripción:
Módulo encargado de mostrar un menú por terminal para generar una vista previa
de tareas de mantenimiento CCTV.

Permite:
- Seleccionar un sector completo.
- Seleccionar cámaras/áreas manualmente.
- Calcular horarios automáticos por cada cámara.
- Mostrar un resumen antes de generar o automatizar tareas en PSINet.

Este archivo NO crea tareas en PSINet.
Solo prepara y muestra la planificación.
"""

from pathlib import Path

from automatizacion.data.config import DIVISION_ACTIVA, SECTORES_PATH
from utils.archivos import cargar_json
from utils.horarios import calcular_horarios


# ==========================================================
# RUTAS BASE DEL PROYECTO
# ==========================================================
# BASE_DIR apunta a la carpeta actual:
# camara_cctv_psinet/automatizacion/
#
# Desde aquí se construyen las rutas de:
# - sectores.json: catálogo de cámaras por sector.
# - config.json: configuración general del sistema.

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


# ==========================================================
# SELECCIÓN POR SECTOR
# ==========================================================

def elegir_sector(sectores):
    """
    Muestra los sectores disponibles y permite elegir uno.

    Parámetros:
        sectores: Diccionario con sectores como claves y listas de cámaras como valores.

    Retorna:
        Nombre del sector seleccionado.
    """
    nombres = list(sectores.keys())

    print("\nSectores disponibles:\n")

    for i, sector in enumerate(nombres, start=1):
        cantidad_camaras = len(sectores[sector])
        print(f"{i}. {sector} ({cantidad_camaras} cámaras)")

    opcion = int(input("\nElige sector: "))

    return nombres[opcion - 1]


# ==========================================================
# SELECCIÓN MANUAL DE CÁMARAS
# ==========================================================

def elegir_manual(sectores):
    """
    Permite buscar cámaras/áreas por texto y seleccionar una o varias manualmente.

    Ejemplo:
        Buscar: bin

        Resultado:
            1. [BIN] 13 Bin
            2. [BIN] 13 BIN 2
            3. [BIN] Porton Eje 16 Bin

        Selección:
            1,3

    Retorna:
        Lista de áreas seleccionadas.
    """
    todas = []

    # Convierte el catálogo por sector en una lista plana:
    # [(sector, area), (sector, area), ...]
    for sector, areas in sectores.items():
        for area in areas:
            todas.append((sector, area))

    busqueda = input("\nBuscar área/cámara: ").strip().lower()

    resultados = [
        (sector, area)
        for sector, area in todas
        if busqueda in area.lower()
    ]

    if not resultados:
        print("No encontré resultados.")
        return []

    print("\nResultados:\n")

    for i, (sector, area) in enumerate(resultados, start=1):
        print(f"{i}. [{sector}] {area}")

    seleccion = input(
        "\nElige números separados por coma, ejemplo 1,3,5: "
    ).strip()

    indices = [
        int(x.strip()) - 1
        for x in seleccion.split(",")
        if x.strip()
    ]

    return [resultados[i][1] for i in indices]


# ==========================================================
# FLUJO PRINCIPAL
# ==========================================================

def main():
    """
    Punto de entrada del menú.

    Carga sectores y configuración, permite escoger el modo de selección,
    calcula horarios y muestra un resumen de las tareas a generar.
    """
    sectores = cargar_json(SECTORES_PATH)
    config = cargar_json(CONFIG_PATH)

    print("\n=== PSINet CCTV - Generador de tareas ===")
    print(f"División activa: {DIVISION_ACTIVA}")
    print("1. Ejecutar por sector")
    print("2. Elegir cámaras manualmente")

    opcion = input("\nOpción: ").strip()

    if opcion == "1":
        sector = elegir_sector(sectores)
        areas = sectores[sector]

    elif opcion == "2":
        areas = elegir_manual(sectores)
        sector = "MANUAL"

    else:
        print("Opción inválida.")
        return

    horarios = calcular_horarios(
        areas,
        config["hora_inicio"],
        config["duracion_minutos"]
    )

    print("\nResumen de ejecución:\n")
    print(f"Sector: {sector}")
    print(f"Hora inicio: {config['hora_inicio']}")
    print(f"Duración por cámara: {config['duracion_minutos']} min")
    print(f"Modo guardado: {config['modo_guardado']}")
    print("\nTareas a generar:\n")

    for item in horarios:
        print(f"{item['inicio']} - {item['fin']} | {item['area']}")

    print("\nTotal:", len(horarios), "tareas")


if __name__ == "__main__":
    main()
