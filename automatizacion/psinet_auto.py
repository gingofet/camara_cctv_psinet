import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

PSINET_USER = os.getenv("PSINET_USER")
PSINET_PASS = os.getenv("PSINET_PASS")

OBSERVACION = "Mantenimiento preventivo, soporte, cableado y cámara CCTV"

AREA_BUSQUEDA = "BIN"
AREA_SELECCION = "-Taller BIN-Eje 12 / Eje 18"

MODO = "revision"  # revision | automatico


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )

        context = browser.new_context()

        page = context.new_page()

        page.goto("https://suite.apps.psinet.cl/login")

        page.get_by_role(
            "textbox",
            name="E-mail"
        ).fill(PSINET_USER)

        page.get_by_role(
            "textbox",
            name="Password"
        ).fill(PSINET_PASS)

        page.get_by_role(
            "button",
            name="Acceder"
        ).click()

        print("Login realizado correctamente")

        page.pause()

        context.close()
        browser.close()


if __name__ == "__main__":
    run()
