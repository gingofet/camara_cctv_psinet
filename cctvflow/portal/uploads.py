"""Carga y verificación de fotografías antes de guardar una mantención."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import re

from playwright.sync_api import Page, expect

from cctvflow.config import MAXIMO_FOTOS
from cctvflow.portal.photo_fields import selector_input_foto


TIMEOUT_FOTO_MS = 30_000
ESPERA_PROCESAMIENTO_FOTO_MS = 1_000
ESPERA_FINAL_FOTOS_MS = 2_000

_ARCHIVO_VALIDO_JS = """(input, nombreEsperado) => Boolean(
    input.files
    && input.files.length === 1
    && input.files[0].name === nombreEsperado
    && input.files[0].size > 0
)"""


def _verificar_input(page: Page, indice: int, ruta: Path) -> bool:
    campo = page.locator(selector_input_foto(indice))
    return bool(campo.evaluate(_ARCHIVO_VALIDO_JS, ruta.name))


def subir_fotos(
    page: Page,
    fotos: Sequence[str],
    dejar_campo_extra: bool = False,
) -> None:
    """Carga cada archivo en un input único y vuelve a validarlos al final."""

    if not fotos:
        return

    if len(fotos) > MAXIMO_FOTOS:
        raise ValueError(
            f"Se recibieron {len(fotos)} fotografías, pero el portal "
            f"permite un máximo de {MAXIMO_FOTOS}."
        )

    archivos_confirmados: list[tuple[int, Path]] = []

    for indice, foto in enumerate(fotos, start=1):
        ruta = Path(foto)

        if not ruta.is_file():
            raise FileNotFoundError(f"No se encontró la fotografía: {ruta}")

        print(
            f"Adjuntando fotografía {indice}/{len(fotos)}: {ruta.name}"
        )

        # Los inputs anteriores permanecen en el DOM; el ID evita locators
        # ambiguos cuando ya existen varios campos deshabilitados.
        campo = page.locator(selector_input_foto(indice))
        campo.wait_for(state="attached", timeout=TIMEOUT_FOTO_MS)
        campo.set_input_files(str(ruta))
        expect(campo).to_have_value(
            re.compile(rf"{re.escape(ruta.name)}$"),
            timeout=TIMEOUT_FOTO_MS,
        )

        if not _verificar_input(page, indice, ruta):
            raise RuntimeError(
                "El portal no conservó correctamente la fotografía "
                f"{indice}: {ruta.name}"
            )

        archivos_confirmados.append((indice, ruta))
        print(f"Fotografía confirmada en el portal: {ruta.name}")
        page.wait_for_timeout(ESPERA_PROCESAMIENTO_FOTO_MS)

        if indice < len(fotos):
            boton_agregar = page.locator(f"#plus{indice}")
            boton_agregar.wait_for(
                state="visible",
                timeout=TIMEOUT_FOTO_MS,
            )
            boton_agregar.click()
            page.wait_for_timeout(300)

    # La verificación completa protege especialmente la última evidencia,
    # que el portal puede soltar mientras procesa los cambios anteriores.
    for indice, ruta in archivos_confirmados:
        if not _verificar_input(page, indice, ruta):
            raise RuntimeError(
                "Una fotografía dejó de estar disponible antes de guardar: "
                f"{ruta.name}"
            )

    page.wait_for_timeout(ESPERA_FINAL_FOTOS_MS)
    print(
        f"Carga verificada: {len(archivos_confirmados)} fotografía(s) "
        "listas para guardar."
    )

    if dejar_campo_extra and len(fotos) < MAXIMO_FOTOS:
        boton_agregar = page.locator(f"#plus{len(fotos)}")

        if boton_agregar.count() > 0:
            boton_agregar.click()
            page.wait_for_timeout(300)
            print(
                "Campo adicional preparado para la fotografía manual "
                "del mantenimiento."
            )
        else:
            print(
                "No se encontró el botón para crear un campo fotográfico "
                "adicional."
            )
