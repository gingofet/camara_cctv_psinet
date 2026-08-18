"""Inicio de sesión en el portal usando credenciales locales."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from cctvflow.config import LOCAL_ENV_PATH

if TYPE_CHECKING:
    from playwright.sync_api import Page


def obtener_credenciales() -> tuple[str, str, str]:
    """Valida y devuelve las tres variables requeridas del archivo ``.env``."""

    url = os.getenv("CCTVFLOW_PORTAL_URL")
    usuario = os.getenv("CCTVFLOW_PORTAL_USER")
    password = os.getenv("CCTVFLOW_PORTAL_PASSWORD")

    if not all((url, usuario, password)):
        # La importación diferida mantiene testeable la validación pura incluso
        # en entornos mínimos que aún no instalaron las dependencias de la app.
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=LOCAL_ENV_PATH)
        url = os.getenv("CCTVFLOW_PORTAL_URL")
        usuario = os.getenv("CCTVFLOW_PORTAL_USER")
        password = os.getenv("CCTVFLOW_PORTAL_PASSWORD")

    if not url:
        raise ValueError("Falta CCTVFLOW_PORTAL_URL en el archivo .env")

    if not usuario:
        raise ValueError("Falta CCTVFLOW_PORTAL_USER en el archivo .env")

    if not password:
        raise ValueError("Falta CCTVFLOW_PORTAL_PASSWORD en el archivo .env")

    return url, usuario, password


def iniciar_sesion(page: Page) -> None:
    """Abre el portal y autentica al usuario configurado."""
    url, usuario, password = obtener_credenciales()

    page.goto(url)

    page.get_by_role("textbox", name="E-mail").fill(usuario)
    page.get_by_role("textbox", name="Password").fill(password)
    page.get_by_role("button", name="Acceder").click()

    page.wait_for_load_state("networkidle")

    print("Inicio de sesión realizado correctamente")
