from playwright.sync_api import Page


def _click_opcion(page: Page, textos: list[str]):
    for texto in textos:
        opcion = page.get_by_text(texto, exact=True)

        if opcion.count() > 0:
            opcion.first.click()
            return

    raise RuntimeError(f"No se encontró ninguna opción: {textos}")


def ir_a_tareas(page: Page):
    print("Abriendo módulo Tareas / Actividades...")

    _click_opcion(page, [
        "Tareas / Actividades",
        "Tareas",
        "Actividades",
    ])

    page.wait_for_load_state("networkidle")

    print("Abriendo listado de tareas...")

    _click_opcion(page, [
        "Tareas",
    ])

    page.wait_for_load_state("networkidle")


def abrir_nueva_tarea(page: Page):
    print("Abriendo formulario Nueva tarea...")

    _click_opcion(page, [
        "Nueva",
        "Nuevo",
        "+ Nueva",
        "+ Nuevo",
    ])

    page.wait_for_load_state("networkidle")

    print("Formulario de nueva tarea abierto")


def crear_tareas_desde_plan(page: Page, plan, evidencias):
    ir_a_tareas(page)
    abrir_nueva_tarea(page)

    print("Pausa para revisar formulario...")
    page.pause()