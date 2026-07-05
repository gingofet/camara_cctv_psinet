import os

from dotenv import load_dotenv
from playwright.sync_api import Page


load_dotenv()


def obtener_credenciales():
    url = os.getenv("PSINET_URL")
    usuario = os.getenv("PSINET_USER")
    password = os.getenv("PSINET_PASS")

    if not url:
        raise ValueError("Falta PSINET_URL en el archivo .env")

    if not usuario:
        raise ValueError("Falta PSINET_USER en el archivo .env")

    if not password:
        raise ValueError("Falta PSINET_PASS en el archivo .env")

    return url, usuario, password


def login_psinet(page: Page):
    url, usuario, password = obtener_credenciales()

    page.goto(url)

    page.get_by_role("textbox", name="E-mail").fill(usuario)
    page.get_by_role("textbox", name="Password").fill(password)
    page.get_by_role("button", name="Acceder").click()

    page.wait_for_load_state("networkidle")

    print("Login realizado correctamente")