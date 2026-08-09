"""Creación de la tarea base, actividad y participantes."""

from __future__ import annotations

from collections.abc import Sequence

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from cctvflow.config import (
    CAUSA_DEFAULT,
    OBSERVACION_DEFAULT,
    RESPONSABLE_DEFAULT,
    TIPO_ACTIVIDAD_DEFAULT,
    TIPO_TAREA_DEFAULT,
    UBICACION_PORTAL_DEFAULT,
)
from cctvflow.portal.controls import (
    TIMEOUT_NORMAL_MS,
    activar_control_etiquetado,
    patron_texto_exacto,
)
from cctvflow.portal.manual import (
    ConfirmacionManual,
    esperar_confirmacion_manual,
)


TIMEOUT_BUSQUEDA_MS = 800


def _normalizar_participantes(
    participantes: Sequence[str],
) -> list[str]:
    """Elimina nombres vacíos y duplicados conservando el orden."""

    resultado: list[str] = []
    vistos: set[str] = set()

    for nombre in participantes:
        nombre_limpio = str(nombre).strip()
        clave = nombre_limpio.casefold()

        if nombre_limpio and clave not in vistos:
            resultado.append(nombre_limpio)
            vistos.add(clave)

    return resultado


def ir_a_tareas(page: Page) -> None:
    """Abre Tareas / Actividades y entra a la sección Tareas."""

    page.get_by_role("link", name="Tareas / Actividades").click()
    page.wait_for_load_state("networkidle")
    page.get_by_role("link", name="Tareas", exact=True).click()
    page.wait_for_load_state("networkidle")


def abrir_nueva_tarea(page: Page) -> None:
    page.get_by_text("Nueva", exact=True).click()
    page.wait_for_load_state("networkidle")


def seleccionar_camara(
    page: Page,
    area_busqueda: str,
    nombre_portal: str,
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Busca la cámara y solicita intervención si la lista no responde."""

    campo_busqueda = page.get_by_role("textbox").nth(5)
    campo_busqueda.fill(area_busqueda)
    page.wait_for_timeout(TIMEOUT_BUSQUEDA_MS)
    opcion = page.get_by_role("treeitem", name=nombre_portal, exact=True)

    # El árbol a veces no refresca con el nombre completo. Borrar el último
    # carácter fuerza el evento de búsqueda sin cambiar el elemento objetivo.
    if opcion.count() == 0 and len(area_busqueda) > 1:
        campo_busqueda.press("Backspace")
        page.wait_for_timeout(TIMEOUT_BUSQUEDA_MS)
        opcion = page.get_by_role(
            "treeitem",
            name=nombre_portal,
            exact=True,
        )

    if opcion.count() > 0:
        opcion.first.click()
        print(f"Cámara seleccionada: {nombre_portal}")
        return

    print("\nNo pude seleccionar la cámara automáticamente.")
    esperar_confirmacion_manual(
        "Selecciona la cámara manualmente en el portal.",
        confirmar_manual,
    )


def crear_tarea_base(
    page: Page,
    area_busqueda: str,
    nombre_portal: str,
    ubicacion_portal: str = UBICACION_PORTAL_DEFAULT,
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Completa el formulario inicial y crea la tarea."""

    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role(
        "treeitem",
        name=TIPO_TAREA_DEFAULT,
        exact=True,
    ).click()
    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role(
        "treeitem",
        name=ubicacion_portal,
        exact=True,
    ).click()
    page.locator("#forms_add_tarea").get_by_label("", exact=True).click()
    seleccionar_camara(
        page,
        area_busqueda,
        nombre_portal,
        confirmar_manual,
    )
    page.locator(
        'input[name="text_observacion_tarea"]'
    ).fill(OBSERVACION_DEFAULT)
    print("Voy a presionar Ingresar para crear la tarea base...")
    page.get_by_role("button", name="Ingresar", exact=True).click()
    page.wait_for_load_state("networkidle")


def _seleccionar_opcion_select2(
    page: Page,
    etiqueta: str,
    opcion: str,
) -> None:
    selector = (
        f"xpath=//*[normalize-space()='{etiqueta}']"
        "/following::*["
        "@role='combobox' or contains(@class, 'select2-selection')"
        "][1]"
    )
    page.locator(selector).click()
    page.get_by_role("treeitem", name=opcion, exact=True).click()


def seleccionar_participante(
    page: Page,
    nombre: str,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> bool:
    """Selecciona un participante por etiqueta y confirma el input real."""

    nombre = nombre.strip()

    if not nombre:
        raise ValueError("El nombre del participante no puede estar vacío.")

    print(f"Buscando participante: {nombre}")
    etiquetas = page.locator("label").filter(
        has_text=patron_texto_exacto(nombre)
    )

    if etiquetas.count() == 0:
        texto = page.get_by_text(nombre, exact=True).first

        if texto.count() > 0:
            etiquetas = texto.locator("xpath=ancestor-or-self::label[1]")

    if etiquetas.count() == 0:
        print(f"No se encontró al participante: {nombre}")
        return False

    if etiquetas.count() > 1:
        print(
            f"Advertencia: hay {etiquetas.count()} coincidencias para "
            f"{nombre!r}. Se utilizará la primera."
        )

    try:
        seleccionado = activar_control_etiquetado(
            page,
            etiquetas.first,
            timeout,
        )
    except PlaywrightTimeoutError:
        print(f"El participante no quedó visible: {nombre}")
        return False
    except Exception as error:
        print(f"No se pudo seleccionar a {nombre}. Detalle: {error}")
        return False

    if seleccionado:
        print(f"Participante seleccionado: {nombre}")
        return True

    print(f"No fue posible confirmar a: {nombre}")
    return False


def seleccionar_participantes(
    page: Page,
    participantes: Sequence[str],
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Selecciona la lista configurada o deja los pendientes al usuario."""

    participantes_limpios = _normalizar_participantes(participantes)

    if not participantes_limpios:
        esperar_confirmacion_manual(
            "Selecciona los participantes manualmente en el portal.",
            confirmar_manual,
        )
        return

    no_seleccionados = [
        participante
        for participante in participantes_limpios
        if not seleccionar_participante(page, participante)
    ]

    if no_seleccionados:
        print("\nNo se pudieron seleccionar automáticamente:")

        for participante in no_seleccionados:
            print(f"  - {participante}")

        esperar_confirmacion_manual(
            "Selecciona manualmente los participantes pendientes en el "
            "portal.",
            confirmar_manual,
        )
        return

    print("Todos los participantes fueron seleccionados correctamente.")


def crear_actividad(
    page: Page,
    hora_inicio: str,
    hora_fin: str,
    participantes: Sequence[str],
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Crea la actividad asociada y asigna sus participantes."""

    page.locator(".btn.btn-outline-info").first.click()
    page.wait_for_timeout(1_000)
    _seleccionar_opcion_select2(
        page,
        "Tipo de Actividad:",
        TIPO_ACTIVIDAD_DEFAULT,
    )
    _seleccionar_opcion_select2(page, "Causa:", CAUSA_DEFAULT)
    page.locator("#time_inicio_actividad").fill(hora_inicio)
    page.locator('input[name="time_cierre_actividad"]').fill(hora_fin)
    page.locator(
        'input[name="text_observacion_actividad"]'
    ).fill(OBSERVACION_DEFAULT)
    seleccionar_participantes(
        page,
        participantes or (RESPONSABLE_DEFAULT,),
        confirmar_manual,
    )

    # Este Select2 no expone una etiqueta estable; se conserva el selector
    # observado hasta contar con un nombre accesible inequívoco.
    page.get_by_role("textbox", name="No", exact=True).click()
    page.get_by_role("treeitem", name="Si", exact=True).click()
    print("Voy a presionar Ingresar para crear la actividad...")
    page.get_by_role("button", name="Ingresar", exact=True).click()
    page.wait_for_load_state("networkidle")
