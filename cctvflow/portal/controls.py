"""Interacciones reutilizables con controles personalizados del portal."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page


TIMEOUT_NORMAL_MS = 10_000


def patron_texto_exacto(texto: str) -> re.Pattern[str]:
    """Acepta espacios externos e ignora diferencias de mayúsculas."""

    return re.compile(rf"^\s*{re.escape(texto)}\s*$", re.IGNORECASE)


def _escapar_valor_atributo_css(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace('"', '\\"')


def buscar_input_asociado(
    page: Page,
    control: Locator,
) -> Locator | None:
    """Localiza el checkbox o radio real asociado a una etiqueta visible.

    Los controles Bootstrap del portal suelen ocultar el ``input``. Se prueba
    primero la relación semántica ``for``/``id`` y después estructuras HTML
    observadas en formularios reales.
    """

    try:
        identificador = control.get_attribute("for")
    except Exception:
        identificador = None

    if identificador:
        identificador_escapado = _escapar_valor_atributo_css(identificador)
        candidato = page.locator(f'[id="{identificador_escapado}"]').first

        if candidato.count() > 0:
            return candidato

    selectores_respaldo = (
        (
            "xpath=preceding-sibling::input["
            "@type='checkbox' or @type='radio'"
            "][1]"
        ),
        (
            "xpath=ancestor::*["
            "contains(concat(' ', normalize-space(@class), ' '), "
            "' custom-control ')"
            "][1]//input[@type='checkbox' or @type='radio'][1]"
        ),
        "xpath=parent::*//input[@type='checkbox' or @type='radio'][1]",
    )

    for selector in selectores_respaldo:
        candidato = control.locator(selector).first

        if candidato.count() > 0:
            return candidato

    return None


def activar_control_etiquetado(
    page: Page,
    control: Locator,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> bool:
    """Activa y confirma un checkbox/radio con clic e intento directo."""

    control.wait_for(state="visible", timeout=timeout)
    control.scroll_into_view_if_needed()
    input_asociado = buscar_input_asociado(page, control)

    if input_asociado is not None:
        try:
            if input_asociado.is_checked():
                return True
        except Exception:
            pass

    try:
        control.click()
    except Exception:
        control.click(force=True)

    page.wait_for_timeout(250)

    if input_asociado is None:
        return True

    try:
        if input_asociado.is_checked():
            return True
    except Exception:
        pass

    try:
        input_asociado.check(force=True)
        page.wait_for_timeout(200)
        return input_asociado.is_checked()
    except Exception:
        return False
