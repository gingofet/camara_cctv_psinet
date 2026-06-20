import json
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECTORES_PATH = BASE_DIR / "data" / "sectores.json"
CONFIG_PATH = BASE_DIR / "config.json"


def cargar_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_horarios(areas, hora_inicio, duracion_minutos):
    inicio = datetime.strptime(hora_inicio, "%H:%M")
    resultado = []

    for area in areas:
        fin = inicio + timedelta(minutes=duracion_minutos)
        resultado.append({
            "area": area,
            "inicio": inicio.strftime("%H:%M"),
            "fin": fin.strftime("%H:%M")
        })
        inicio = fin

    return resultado


def elegir_sector(sectores):
    nombres = list(sectores.keys())

    print("\nSectores disponibles:\n")
    for i, sector in enumerate(nombres, start=1):
        print(f"{i}. {sector} ({len(sectores[sector])} cámaras)")

    opcion = int(input("\nElige sector: "))
    return nombres[opcion - 1]


def elegir_manual(sectores):
    todas = []
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

    seleccion = input("\nElige números separados por coma, ejemplo 1,3,5: ").strip()

    indices = [int(x.strip()) - 1 for x in seleccion.split(",") if x.strip()]
    return [resultados[i][1] for i in indices]


def main():
    sectores = cargar_json(SECTORES_PATH)
    config = cargar_json(CONFIG_PATH)

    print("\n=== PSINet CCTV - Generador de tareas ===")
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
