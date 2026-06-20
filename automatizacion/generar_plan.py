import json
from menu_psinet import cargar_json, elegir_sector, elegir_manual, calcular_horarios, SECTORES_PATH, CONFIG_PATH, BASE_DIR

PLAN_PATH = BASE_DIR / "plan_ejecucion.json"


def main():
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
        config["duracion_minutos"]
    )

    plan = {
        "sector": sector,
        "modo_guardado": config["modo_guardado"],
        "observacion": config["observacion"],
        "carpeta_fotos": config["carpeta_fotos"],
        "tareas": horarios
    }
    carpeta_fotos = BASE_DIR / config["carpeta_fotos"] / sector
    carpeta_fotos.mkdir(parents=True, exist_ok=True)

    plan["ruta_fotos"] = str(carpeta_fotos)

    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\nPlan generado en: {PLAN_PATH}")
    print(f"Total tareas: {len(horarios)}")


if __name__ == "__main__":
    main()

    print(f"Carpeta fotos: {carpeta_fotos}")
