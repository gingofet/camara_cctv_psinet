"""
Proyecto: Cámara CCTV PSINet
Archivo: generar_plan_desde_fotos.py

Descripción:
Genera plan_ejecucion.json automáticamente usando las fotos detectadas
por lector_fotos.py.

Flujo:
1. Lee evidencias.json.
2. Toma las áreas que tienen fotos.
3. Calcula horarios automáticos.
4. Genera plan_ejecucion.json listo para PSINet.
"""

import json
from pathlib import Path

from menu_psinet import (
    cargar_json,
    calcular_horarios,
    CONFIG_PATH,
    BASE_DIR,
)


EVIDENCIAS_PATH = BASE_DIR / "evidencias.json"
PLAN_PATH = BASE_DIR / "plan_ejecucion.json"


def main():
    config = cargar_json(CONFIG_PATH)

    if not EVIDENCIAS_PATH.exists():
        print("No existe evidencias.json. Primero ejecuta lector_fotos.py")
        return

    evidencias_data = cargar_json(EVIDENCIAS_PATH)
    evidencias = evidencias_data.get("evidencias", {})

    if not evidencias:
        print("No hay evidencias detectadas. Revisa la carpeta fotos/")
        return

    areas = list(evidencias.keys())

    horarios = calcular_horarios(
        areas,
        config["hora_inicio"],
        config["duracion_minutos"],
    )

    plan = {
        "sector": "DESDE_FOTOS",
        "modo_guardado": config["modo_guardado"],
        "observacion": config["observacion"],
        "carpeta_fotos": config["carpeta_fotos"],
        "ruta_fotos": str(BASE_DIR / config["carpeta_fotos"]),
        "tareas": [],
    }

    for item in horarios:
        area = item["area"]
        item["sector"] = evidencias[area]["sector"]
        item["fotos"] = evidencias[area]["fotos"]
        plan["tareas"].append(item)

    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print("\n=== Plan generado desde fotos ===\n")

    for tarea in plan["tareas"]:
        print(
            f"{tarea['inicio']} - {tarea['fin']} | "
            f"[{tarea['sector']}] {tarea['area']} | "
            f"{len(tarea['fotos'])} foto(s)"
        )

    print(f"\nPlan generado en: {PLAN_PATH}")
    print(f"Total tareas: {len(plan['tareas'])}")


if __name__ == "__main__":
    main()
