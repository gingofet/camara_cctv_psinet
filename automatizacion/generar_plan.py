"""
Proyecto: Cámara CCTV PSINet
Archivo: generar_plan_desde_fotos.py

Descripción:
Genera plan_ejecucion.json automáticamente usando las fotos detectadas
por lector_fotos.py.
"""

from menu_psinet import CONFIG_PATH, BASE_DIR
from utils.archivos import cargar_json, guardar_json
from utils.horarios import calcular_horarios


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

    guardar_json(PLAN_PATH, plan)

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