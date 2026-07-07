from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import Page


BASE_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = BASE_DIR / "downloads" / "pdfs"


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

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    destino = PDF_DIR / nombre_pdf

    respuesta = page.context.request.get(url_pdf)

    if not respuesta.ok:
        print(f"No pude descargar el PDF. Estado HTTP: {respuesta.status}")
        return None

    destino.write_bytes(respuesta.body())

    if pagina_pdf != page:
        pagina_pdf.close()

    print(f"PDF descargado: {destino}")
    return destino