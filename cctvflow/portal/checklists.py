"""Relleno de las secciones de evaluación técnica."""

from __future__ import annotations

import re

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from cctvflow.portal.checklist_rules import (
    estados_conexiones,
    variantes_item_conexiones,
)
from cctvflow.portal.controls import (
    TIMEOUT_NORMAL_MS,
    activar_control_etiquetado,
    buscar_input_asociado,
    patron_texto_exacto,
)


def completar_estado_general(page: Page) -> None:
    """Completa ESTADO GENERAL con los valores validados en terreno."""

    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()

    for indice in range(6):
        page.get_by_text("B", exact=True).nth(indice).click()

    # Este último control aún no expone una etiqueta estable en el formulario.
    page.locator(
        "div:nth-child(7) > div > .custom-control-label"
    ).first.click()
    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()


def _seleccionar_estado_item(
    page: Page,
    panel: Locator,
    item: str,
    estado: str,
) -> None:
    variantes = variantes_item_conexiones(item)
    alternativas = "|".join(re.escape(variante) for variante in variantes)
    patron_item = re.compile(
        rf"^\s*(?:{alternativas})\s*$",
        re.IGNORECASE,
    )
    titulo = panel.get_by_text(patron_item).first

    try:
        titulo.wait_for(state="visible", timeout=TIMEOUT_NORMAL_MS)
    except PlaywrightTimeoutError as error:
        variantes_texto = ", ".join(repr(variante) for variante in variantes)
        raise RuntimeError(
            "No se encontró el ítem de conexiones "
            f"{item!r}. Variantes buscadas: {variantes_texto}."
        ) from error

    # La fila se resuelve por contenido y no por un ID dinámico del portal.
    fila = titulo.locator(
        "xpath=ancestor::*["
        ".//*[normalize-space()='B'] and "
        ".//*["
        "translate(normalize-space(), ' ', '')='N/A' or "
        "translate(normalize-space(), ' ', '')='NA'"
        "]"
        "][1]"
    ).first

    if fila.count() == 0:
        raise RuntimeError(
            f"No se pudo identificar la fila del ítem: {item}"
        )

    patron_estado = (
        re.compile(r"^\s*N\s*/?\s*A\s*$", re.IGNORECASE)
        if estado == "N/A"
        else patron_texto_exacto(estado)
    )
    controles = fila.locator(
        "label, button, [role='button']"
    ).filter(has_text=patron_estado)

    if controles.count() == 0:
        texto_estado = fila.get_by_text(patron_estado).first

        if texto_estado.count() > 0:
            controles = texto_estado.locator(
                "xpath=ancestor-or-self::*["
                "self::label or self::button or @role='button'"
                "][1]"
            )

    if controles.count() == 0:
        raise RuntimeError(
            f"No se encontró la opción {estado!r} para {item!r}."
        )

    control = controles.first
    input_asociado = buscar_input_asociado(page, control)
    seleccionado = False

    # B y N/A comparten la misma ruta rápida y disparan input/change.
    if input_asociado is not None:
        try:
            input_asociado.check(force=True)
            expect(input_asociado).to_be_checked(
                timeout=TIMEOUT_NORMAL_MS,
            )
            seleccionado = True
        except Exception:
            seleccionado = False

    if not seleccionado:
        seleccionado = activar_control_etiquetado(page, control)

    if not seleccionado:
        raise RuntimeError(
            f"No fue posible confirmar {estado!r} para {item!r}."
        )

    print(f"Conexiones · {item}: {estado}")


def completar_conexiones(page: Page, camara_ip: bool = False) -> None:
    """Completa CONEXIONES por nombre y aplica N/A cuando corresponde."""

    enlace = page.get_by_role("link", name="CONEXIONES", exact=True)
    id_panel = enlace.get_attribute("aria-controls")

    if not id_panel:
        id_panel = (enlace.get_attribute("href") or "").removeprefix("#")

    if not id_panel:
        raise RuntimeError(
            "No se pudo identificar el panel de la sección CONEXIONES."
        )

    enlace.click()
    panel = page.locator(f"#{id_panel}")
    panel.wait_for(state="visible")

    for item, estado in estados_conexiones(camara_ip):
        _seleccionar_estado_item(page, panel, item, estado)

    enlace.click()
