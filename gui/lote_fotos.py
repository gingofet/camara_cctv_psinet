"""Detección y validación de lotes fotográficos desde la GUI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from automatizacion.data.config import MAXIMO_FOTOS
from utils.normalizar import normalizar_texto


EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
FOTOS_ART_POR_MANTENIMIENTO = 2
MAXIMO_EVIDENCIAS_POR_CAMARA = (
    MAXIMO_FOTOS - FOTOS_ART_POR_MANTENIMIENTO
)
PATRON_CORRELATIVO = re.compile(r"(?:[_\s-])\d{4,}$")


@dataclass(frozen=True, slots=True)
class FotoNoDetectada:
    ruta: Path
    motivo: str


@dataclass(frozen=True, slots=True)
class LoteFotografico:
    """Resultado inmutable de analizar una carpeta de fotografías."""

    carpeta: Path
    fotos_por_camara: dict[str, tuple[Path, ...]]
    sector_por_camara: dict[str, str]
    no_detectadas: tuple[FotoNoDetectada, ...]

    @property
    def sectores(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.sector_por_camara.values()))

    @property
    def cantidad_fotos(self) -> int:
        return sum(len(fotos) for fotos in self.fotos_por_camara.values())


def _nombre_camara_desde_foto(ruta: Path) -> str:
    """Quita únicamente el correlativo final generado por la app Android."""

    sin_correlativo = PATRON_CORRELATIVO.sub("", ruta.stem)
    return normalizar_texto(sin_correlativo)


def analizar_carpeta(
    carpeta: str | Path,
    catalogo: dict[str, list[str]],
) -> LoteFotografico:
    """Relaciona cada imagen con una cámara mediante su nombre normalizado."""

    ruta_carpeta = Path(carpeta).expanduser().resolve()

    if not ruta_carpeta.is_dir():
        raise NotADirectoryError(
            f"No existe la carpeta de fotografías: {ruta_carpeta}"
        )

    indice: dict[str, list[tuple[str, str]]] = {}

    for sector, camaras in catalogo.items():
        for camara in camaras:
            clave = normalizar_texto(camara)
            indice.setdefault(clave, []).append((sector, camara))

    fotos_por_camara: dict[str, list[Path]] = {}
    sector_por_camara: dict[str, str] = {}
    no_detectadas: list[FotoNoDetectada] = []

    archivos = sorted(
        (
            ruta
            for ruta in ruta_carpeta.rglob("*")
            if ruta.is_file()
            and ruta.suffix.casefold() in EXTENSIONES_IMAGEN
        ),
        key=lambda ruta: str(ruta).casefold(),
    )

    for foto in archivos:
        clave = _nombre_camara_desde_foto(foto)
        coincidencias = indice.get(clave, [])

        if not coincidencias:
            no_detectadas.append(
                FotoNoDetectada(
                    foto,
                    "El nombre no coincide con ninguna cámara del catálogo.",
                )
            )
            continue

        if len(coincidencias) > 1:
            sectores = ", ".join(
                sector for sector, _ in coincidencias
            )
            no_detectadas.append(
                FotoNoDetectada(
                    foto,
                    f"El nombre coincide con más de un área: {sectores}.",
                )
            )
            continue

        sector, camara = coincidencias[0]
        fotos_por_camara.setdefault(camara, []).append(foto)
        sector_por_camara[camara] = sector

    return LoteFotografico(
        carpeta=ruta_carpeta,
        fotos_por_camara={
            camara: tuple(fotos)
            for camara, fotos in fotos_por_camara.items()
        },
        sector_por_camara=sector_por_camara,
        no_detectadas=tuple(no_detectadas),
    )


def validar_lote(
    lote: LoteFotografico,
    camaras: list[str] | tuple[str, ...],
) -> list[str]:
    """Devuelve problemas que impiden ejecutar automáticamente un lote."""

    errores: list[str] = []

    for camara in camaras:
        fotos = lote.fotos_por_camara.get(camara, ())

        if not fotos:
            errores.append(f"{camara}: no tiene fotografías.")
            continue

        if len(fotos) > MAXIMO_EVIDENCIAS_POR_CAMARA:
            errores.append(
                f"{camara}: tiene {len(fotos)} evidencias; el máximo es "
                f"{MAXIMO_EVIDENCIAS_POR_CAMARA} porque dos espacios se "
                "reservan para el ART."
            )

        for foto in fotos:
            if not foto.is_file():
                errores.append(
                    f"{camara}: ya no existe {foto.name}."
                )

    return errores
