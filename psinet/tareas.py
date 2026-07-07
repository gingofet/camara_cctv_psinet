from pathlib import Path

from playwright.sync_api import Page


OBSERVACION_DEFAULT = "Mantenimiento CCTV"


def _click_opcion(page: Page, textos: list[str]):
    for texto in textos:
        opcion = page.get_by_text(texto, exact=True)

        if opcion.count() > 0:
            opcion.first.click()
            return

    raise RuntimeError(f"No se encontró ninguna opción: {textos}")


def ir_a_tareas(page: Page):
    page.get_by_role("link", name="Tareas / Actividades").click()
    page.wait_for_load_state("networkidle")

    page.get_by_role("link", name="Tareas", exact=True).click()
    page.wait_for_load_state("networkidle")


def abrir_nueva_tarea(page: Page):
    page.get_by_text("Nueva", exact=True).click()
    page.wait_for_load_state("networkidle")

def seleccionar_camara(page: Page, area_busqueda: str, area_psinet: str):
    campo_busqueda = page.get_by_role("textbox").nth(5)

    campo_busqueda.fill(area_busqueda)
    page.wait_for_timeout(800)

    opcion = page.get_by_role("treeitem", name=area_psinet)

    if opcion.count() == 0 and len(area_busqueda) > 1:
        campo_busqueda.press("Backspace")
        page.wait_for_timeout(800)
        opcion = page.get_by_role("treeitem", name=area_psinet)

    if opcion.count() > 0:
        opcion.first.click()
        return

    print("")
    print("No pude seleccionar la cámara automáticamente.")
    print("Selecciona la cámara manualmente en PSINet.")
    print("Cuando la selecciones, presiona Enter aquí para continuar.")
    input()

def crear_tarea_base(page: Page, area_busqueda: str, area_psinet: str):
    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role("treeitem", name="Mantencion Programada").click()

    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role("treeitem", name="DCH-SUBTE").click()

    page.locator("#forms_add_tarea").get_by_label("", exact=True).click()

    seleccionar_camara(
        page=page,
        area_busqueda=area_busqueda,
        area_psinet=area_psinet,
    )

    page.locator('input[name="text_observacion_tarea"]').fill(OBSERVACION_DEFAULT)

    print("Voy a presionar Ingresar para crear la tarea base...")
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def seleccionar_opcion_select2(page: Page, etiqueta: str, opcion: str):
    selector = (
        f"xpath=//*[normalize-space()='{etiqueta}']"
        "/following::*[@role='combobox' or contains(@class, 'select2-selection')][1]"
    )

    page.locator(selector).click()
    page.get_by_role("treeitem", name=opcion).click()


def crear_actividad(
    page: Page,
    hora_inicio: str = "17:00",
    hora_fin: str = "17:10",
    responsable: str = "Louis Rivera",
):
    page.locator(".btn.btn-outline-info").first.click()
    page.wait_for_timeout(1000)

    seleccionar_opcion_select2(page, "Tipo de Actividad:", "Mantenimiento Preventivo")
    seleccionar_opcion_select2(page, "Causa:", "CCTV")

    page.locator("#time_inicio_actividad").fill(hora_inicio)
    page.locator('input[name="time_cierre_actividad"]').fill(hora_fin)
    page.locator('input[name="text_observacion_actividad"]').fill(OBSERVACION_DEFAULT)

    print("")
    print("Selecciona manualmente los participantes/trabajadores.")
    print("Cuando estén seleccionados, presiona Enter aquí para continuar.")
    input()

    page.get_by_role("textbox", name="No", exact=True).click()
    page.get_by_role("treeitem", name="Si").click()

    print("Voy a presionar Ingresar para crear la actividad...")
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_load_state("networkidle")

def seleccionar_no_por_pregunta(page: Page, pregunta: str):
    opcion_no = page.locator(
        f"xpath=//*[contains(normalize-space(), '{pregunta}')]"
        "/following::*[normalize-space()='No'][1]"
    )
    opcion_no.click()

def completar_estado_general(page: Page):
    page.get_by_role("link", name="ESTADO GENERAL").click()

    for indice in range(6):
        page.get_by_text("B", exact=True).nth(indice).click()

    page.locator("div:nth-child(7) > div > .custom-control-label").first.click()

    page.get_by_role("link", name="ESTADO GENERAL").click()


def completar_conexiones(page: Page):
    page.get_by_role("link", name="CONEXIONES").click()

    page.locator(
        "#collapse1543 > .card-body > .container > div > div:nth-child(5) > .custom-control-label"
    ).first.click()
    page.locator(
        "#collapse1543 > .card-body > .container > div:nth-child(2) > div > .custom-control-label"
    ).first.click()
    page.locator(
        "#collapse1543 > .card-body > .container > div:nth-child(3) > div:nth-child(5) > .custom-control-label"
    ).click()
    page.locator(
        "#collapse1543 > .card-body > .container > div:nth-child(4) > div > .custom-control-label"
    ).first.click()
    page.locator(
        "#collapse1543 > .card-body > .container > div:nth-child(5) > div > .custom-control-label"
    ).first.click()
    page.locator(
        "#collapse1543 > .card-body > .container > div:nth-child(6) > div > .custom-control-label"
    ).first.click()

    page.get_by_role("link", name="CONEXIONES").click()


def completar_cierre(page: Page, fotos: list[str]):
    try:
        seleccionar_no_por_pregunta(page, "APR participa en la actividad")
        seleccionar_no_por_pregunta(page, "Apoyo de equipo alza hombre")
    except Exception as error:
        print("")
        print("No pude seleccionar automaticamente APR/Alza hombre.")
        print("Selecciona manualmente los 'No' y luego presiona Enter aqui.")
        print(f"Detalle: {error}")
        input()

    page.get_by_role("textbox", name="Observaciones generales:").fill(OBSERVACION_DEFAULT)

    if fotos:
        subir_fotos(page, fotos)

    print("")
    print("Formulario listo para adjuntar fotos y guardar.")
    print("Sube las fotos manualmente y presiona Guardar en PSINet.")


def subir_fotos(page: Page, fotos: list[str]):
    if not fotos:
        return

    for indice, foto in enumerate(fotos, start=1):
        ruta_foto = Path(foto)

        if indice == 1:
            page.get_by_role("button", name="Choose File").set_input_files(str(ruta_foto))
        else:
            page.locator(f"#inputFoto{indice}").set_input_files(str(ruta_foto))

        if indice < len(fotos):
            page.locator(f"#plus{indice}").click()


def crear_mantenimiento(page: Page, evidencia: dict, modo_navegacion: str = "completa"):
    area = evidencia["area"]
    area_busqueda = evidencia.get("area_busqueda", area)
    fotos = evidencia.get("fotos", [])
    hora_inicio = evidencia.get("hora_inicio", "17:00")
    hora_fin = evidencia.get("hora_fin", "17:10")

    if modo_navegacion == "completa":
        ir_a_tareas(page)
        abrir_nueva_tarea(page)
    elif modo_navegacion == "solo_nueva":
        abrir_nueva_tarea(page)
    elif modo_navegacion == "ninguna":
        print("Usando formulario de Nueva tarea ya abierto...")
    else:
        raise ValueError(f"Modo de navegación no válido: {modo_navegacion}")

    crear_tarea_base(
        page=page,
        area_busqueda=area_busqueda,
        area_psinet=area,
    )

    crear_actividad(
        page=page,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
    )

    completar_estado_general(page)
    completar_conexiones(page)
    completar_cierre(page, fotos)

    print("Mantención completada. Sube las fotos manualmente y guarda.")