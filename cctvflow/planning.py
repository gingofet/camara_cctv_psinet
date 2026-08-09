"""Carga de catálogos y planificación de mantenciones."""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timedelta

from cctvflow.config import (
    DIVISIONES,
    obtener_configuracion_division,
    obtener_ruta_sectores,
)
from cctvflow.models import MantenimientoPlanificado


FORMATO_HORA = "%H:%M"
DURACION_MINUTOS = 10


def divisiones_disponibles() -> list[str]:
    return list(DIVISIONES)


def cargar_catalogo(division: str) -> dict[str, list[str]]:
    ruta = obtener_ruta_sectores(division)

    if not ruta.exists():
        raise FileNotFoundError(f"No existe el catálogo: {ruta}")

    with ruta.open(encoding="utf-8") as archivo:
        catalogo = json.load(archivo)

    if not isinstance(catalogo, dict):
        raise ValueError(f"El catálogo no es un objeto JSON: {ruta}")

    resultado: dict[str, list[str]] = {}

    for sector, camaras in catalogo.items():
        if not isinstance(sector, str) or not isinstance(camaras, list):
            raise ValueError(f"Formato inválido en el catálogo: {ruta}")

        resultado[sector] = [str(camara) for camara in camaras]

    return resultado


def ubicacion_portal(division: str) -> str:
    """Devuelve la ubicación que debe seleccionarse en el portal."""

    return obtener_configuracion_division(division)["ubicacion_portal"]


def normalizar_busqueda(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        caracter
        for caracter in descompuesto
        if not unicodedata.combining(caracter)
    )


def filtrar_camaras(
    catalogo: dict[str, list[str]],
    sector: str | None = None,
    consulta: str = "",
) -> list[tuple[str, str]]:
    consulta_normalizada = normalizar_busqueda(consulta.strip())
    resultados: list[tuple[str, str]] = []

    for nombre_sector, camaras in catalogo.items():
        if sector and nombre_sector != sector:
            continue

        for camara in camaras:
            texto = normalizar_busqueda(f"{nombre_sector} {camara}")

            if consulta_normalizada and consulta_normalizada not in texto:
                continue

            resultados.append((nombre_sector, camara))

    return resultados


def generar_plan(
    seleccion: list[tuple[str, str]],
    hora_inicial: str,
    duracion_minutos: int = DURACION_MINUTOS,
) -> list[MantenimientoPlanificado]:
    if not seleccion:
        return []

    if duracion_minutos <= 0:
        raise ValueError("La duración debe ser mayor que cero.")

    hora_actual = datetime.strptime(hora_inicial, FORMATO_HORA)
    plan: list[MantenimientoPlanificado] = []

    for sector, camara in seleccion:
        hora_fin = hora_actual + timedelta(minutes=duracion_minutos)
        plan.append(
            MantenimientoPlanificado(
                sector=sector,
                camara=camara,
                hora_inicio=hora_actual.strftime(FORMATO_HORA),
                hora_fin=hora_fin.strftime(FORMATO_HORA),
            )
        )
        hora_actual = hora_fin

    return plan


def validar_catalogos() -> dict[str, tuple[int, int]]:
    """Devuelve cantidad de sectores y cámaras por división."""

    resumen: dict[str, tuple[int, int]] = {}

    for division in divisiones_disponibles():
        catalogo = cargar_catalogo(division)
        cantidad = sum(len(camaras) for camaras in catalogo.values())
        resumen[division] = (len(catalogo), cantidad)

    return resumen
