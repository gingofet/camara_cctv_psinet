"""
Proyecto: Cámara CCTV PSINet
Archivo: generar_plan.py

Descripción:
Genera un archivo plan_ejecucion.json a partir de una selección de cámaras.

Permite:
- Generar un plan por sector completo.
- Generar un plan con cámaras seleccionadas manualmente.
- Calcular horarios automáticos.
- Crear la carpeta donde se dejarán las fotos/evidencias.
"""

import json
from menu_psinet import (
    cargar_json,
    elegir_sector,
    elegir_manual,
    calcular_horarios,
    SECTORES_PATH,
    CONFIG_PATH,
    BASE_DIR,
)


PLAN_PATH = BASE_DIR / "plan_ejecucion.json"


def main():
    """
    Genera el plan de ejecución que luego será usado por Playwright
    para crear tareas en PSINet.
    """
    sectores = cargar_json(SECTORES_PATH)
    config = cargar_json(CONFIG_PATH)

    print("\n=== Generar plan de ejecución PSINet ===")
    print("1. Ejecutar por sector")
    print("2. Elegir cámaras manualmente")

    opcion = input("\nOpción: ").strip()

    if opcion == "1":
        sector = elegir_sector(sectores)
        areas = sectores[sector]

    elif opcion == "2":
        sector = "MANUAL"
        areas = elegir_manual(sectores)

    else:
        print("Opción inválida.")
        return

    horarios = calcular_horarios(
        areas,
        config["hora_inicio"],
        config["duracion_minutos"],
    )

    carpeta_fotos = BASE_DIR / config["carpeta_fotos"] / sector
    carpeta_fotos.mkdir(parents=True, exist_ok=True)

    plan = {
        "sector": sector,
        "modo_guardado": config["modo_guardado"],
        "observacion": config["observacion"],
        "carpeta_fotos": config["carpeta_fotos"],
        "ruta_fotos": str(carpeta_fotos),
        "tareas": horarios,
    }

    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\nPlan generado en: {PLAN_PATH}")
    print(f"Carpeta fotos: {carpeta_fotos}")
    print(f"Total tareas: {len(horarios)}")


if __name__ == "__main__":
    main()
