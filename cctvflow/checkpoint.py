"""Punto de control persistente para lotes automáticos de CCTVFlow."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cctvflow.config import RUNTIME_DIR
from cctvflow.models import MantenimientoPlanificado


CHECKPOINT_PATH = RUNTIME_DIR / "ejecucion_pendiente.json"
VERSION_CHECKPOINT = 1

ESTADO_PENDIENTE = "pendiente"
ESTADO_EN_PROCESO = "en_proceso"
ESTADO_COMPLETADO = "completado"
ESTADO_INCOMPLETO = "pdf_incompleto"
ESTADO_ERROR = "requiere_revision"


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _escribir_atomico(datos: dict[str, Any], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(f"{ruta.suffix}.tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporal, ruta)


def crear_checkpoint(
    *,
    division: str,
    plan: list[MantenimientoPlanificado],
    participantes: list[str],
    apr_participa: bool,
    equipo_alza_hombre: bool,
    observacion: str,
    fotos_por_camara: dict[str, list[str]],
    fotos_art_por_sector: dict[str, list[str]],
    eliminar_fotos_tras_exito: bool,
    eliminar_art_tras_exito: bool,
    ruta: str | Path = CHECKPOINT_PATH,
) -> Path:
    """Crea el estado inicial antes de abrir el portal."""

    destino = Path(ruta)
    marca_tiempo = _ahora()
    datos: dict[str, Any] = {
        "version": VERSION_CHECKPOINT,
        "creado": marca_tiempo,
        "actualizado": marca_tiempo,
        "division": division,
        "configuracion": {
            "participantes": participantes,
            "apr_participa": apr_participa,
            "equipo_alza_hombre": equipo_alza_hombre,
            "observacion": observacion,
            "eliminar_fotos_tras_exito": eliminar_fotos_tras_exito,
            "eliminar_art_tras_exito": eliminar_art_tras_exito,
        },
        "plan": [asdict(item) for item in plan],
        "fotos_por_camara": fotos_por_camara,
        "fotos_art_por_sector": fotos_art_por_sector,
        "resultados": {
            item.camara: {
                "estado": ESTADO_PENDIENTE,
                "actualizado": marca_tiempo,
                "pdf": None,
                "detalle": None,
            }
            for item in plan
        },
    }
    _escribir_atomico(datos, destino)
    return destino


def cargar_checkpoint(
    ruta: str | Path = CHECKPOINT_PATH,
) -> dict[str, Any] | None:
    origen = Path(ruta)

    if not origen.is_file():
        return None

    try:
        datos = json.loads(origen.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"No fue posible leer el punto de control: {origen}"
        ) from error

    if datos.get("version") != VERSION_CHECKPOINT:
        raise RuntimeError(
            "El punto de control pertenece a una versión incompatible."
        )

    campos = {
        "division",
        "configuracion",
        "plan",
        "fotos_por_camara",
        "fotos_art_por_sector",
        "resultados",
    }

    if not campos.issubset(datos):
        raise RuntimeError("El punto de control está incompleto.")

    return datos


def actualizar_estado(
    camara: str,
    estado: str,
    *,
    pdf: str | Path | None = None,
    detalle: str | None = None,
    ruta: str | Path = CHECKPOINT_PATH,
) -> None:
    datos = cargar_checkpoint(ruta)

    if datos is None:
        return

    if camara not in datos["resultados"]:
        raise KeyError(
            f"La cámara no pertenece al punto de control: {camara}"
        )

    marca_tiempo = _ahora()
    datos["resultados"][camara] = {
        "estado": estado,
        "actualizado": marca_tiempo,
        "pdf": str(pdf) if pdf else None,
        "detalle": detalle,
    }
    datos["actualizado"] = marca_tiempo
    _escribir_atomico(datos, Path(ruta))


def plan_pendiente(
    datos: dict[str, Any],
) -> list[MantenimientoPlanificado]:
    """Devuelve solo cámaras que nunca comenzaron a guardarse en el portal."""

    resultados = datos["resultados"]
    return [
        MantenimientoPlanificado(**item)
        for item in datos["plan"]
        if resultados[item["camara"]]["estado"] == ESTADO_PENDIENTE
    ]


def resumen_checkpoint(datos: dict[str, Any]) -> dict[str, int]:
    resumen = {
        ESTADO_PENDIENTE: 0,
        ESTADO_EN_PROCESO: 0,
        ESTADO_COMPLETADO: 0,
        ESTADO_INCOMPLETO: 0,
        ESTADO_ERROR: 0,
    }

    for resultado in datos["resultados"].values():
        estado = resultado.get("estado", ESTADO_ERROR)
        resumen[estado] = resumen.get(estado, 0) + 1

    return resumen
