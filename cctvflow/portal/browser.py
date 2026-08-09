"""Creación y cierre seguro de la sesión de Chromium."""

from contextlib import contextmanager

from playwright.sync_api import sync_playwright


@contextmanager
def iniciar_navegador(headless=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            yield page
        finally:
            context.close()
            browser.close()
