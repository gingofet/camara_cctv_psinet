from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from pypdf import PdfReader

from cctvflow.config import REPORTS_DIR

if TYPE_CHECKING:
    from playwright.sync_api import Page


PAGINAS_BASE_INFORME = 1


class PdfMantenimientoIncompletoError(RuntimeError):
    """El informe generado omitió una o más fotografías."""

    def __init__(
        self,
        ruta_pdf: Path,
        paginas_reales: int,
        paginas_minimas: int,
        cantidad_fotos_esperadas: int,
    ):
        self.ruta_pdf = ruta_pdf
        self.paginas_reales = paginas_reales
        self.paginas_minimas = paginas_minimas
        self.cantidad_fotos_esperadas = cantidad_fotos_esperadas
        super().__init__(
            f"El PDF {ruta_pdf.name} tiene {paginas_reales} página(s), "
            f"pero se esperaban al menos {paginas_minimas}: una página "
            f"de informe y {cantidad_fotos_esperadas} fotografía(s)."
        )


def obtener_nombre_pdf_desde_url(url: str) -> str:
    ruta = urlparse(url).path
    nombre = Path(unquote(ruta)).name

    if not nombre.lower().endswith(".pdf"):
        nombre = f"{nombre}.pdf"

    return nombre


def buscar_pagina_pdf(page: Page):
    for pagina in reversed(page.context.pages):
        url = pagina.url.lower()

        if "pdf_chkmantencion" in url or url.endswith(".pdf"):
            return pagina

    return None


def descargar_pdf_abierto(page: Page):
    pagina_pdf = buscar_pagina_pdf(page)

    if not pagina_pdf:
        print("No encontré una pestaña PDF abierta.")
        return None

    url_pdf = pagina_pdf.url
    nombre_pdf = obtener_nombre_pdf_desde_url(url_pdf)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    destino = REPORTS_DIR / nombre_pdf

    respuesta = page.context.request.get(url_pdf)

    if not respuesta.ok:
        print(f"No pude descargar el PDF. Estado HTTP: {respuesta.status}")
        return None

    destino.write_bytes(respuesta.body())

    if pagina_pdf != page:
        pagina_pdf.close()

    print(f"PDF descargado: {destino}")
    return destino


def validar_pdf_mantenimiento(
    ruta_pdf: str | Path,
    cantidad_fotos_esperadas: int,
) -> int:
    """Confirma que el PDF contenga el informe y todas las fotografías.

    El portal genera una primera página de checklist y una página adicional por
    fotografía. Se acepta que el informe tenga páginas extra, pero nunca menos
    de las necesarias para la cantidad de imágenes enviada.
    """

    ruta = Path(ruta_pdf)

    if cantidad_fotos_esperadas < 0:
        raise ValueError(
            "La cantidad de fotografías esperadas no puede ser negativa."
        )

    if not ruta.is_file() or ruta.stat().st_size == 0:
        raise RuntimeError(
            f"El PDF descargado no existe o está vacío: {ruta}"
        )

    try:
        lector = PdfReader(str(ruta))
        paginas_reales = len(lector.pages)
    except Exception as error:
        raise RuntimeError(
            f"No fue posible validar el PDF descargado: {ruta.name}"
        ) from error

    paginas_minimas = PAGINAS_BASE_INFORME + cantidad_fotos_esperadas

    if paginas_reales < paginas_minimas:
        raise PdfMantenimientoIncompletoError(
            ruta_pdf=ruta,
            paginas_reales=paginas_reales,
            paginas_minimas=paginas_minimas,
            cantidad_fotos_esperadas=cantidad_fotos_esperadas,
        )

    print(
        f"PDF validado: {paginas_reales} página(s), "
        f"{cantidad_fotos_esperadas} fotografía(s) confirmadas."
    )
    return paginas_reales
