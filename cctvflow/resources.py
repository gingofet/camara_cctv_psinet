"""Acceso centralizado a los recursos estáticos usados por la aplicación."""

from __future__ import annotations

from pathlib import Path

from cctvflow.config import ART_DIR, PROJECT_ROOT


NOMBRES_FOTOS_ART = ("ART", "ART_atras")
EXTENSIONES_IMAGEN_ART = {".jpg", ".jpeg", ".png"}


def buscar_imagen_por_nombre(directorio: Path, nombre: str) -> Path:
    """Busca una imagen por nombre base sin imponer una extensión concreta."""

    if not directorio.is_dir():
        raise FileNotFoundError(
            f"No existe la carpeta de fotografías ART: {directorio}"
        )

    for archivo in directorio.iterdir():
        if (
            archivo.is_file()
            and archivo.suffix.casefold() in EXTENSIONES_IMAGEN_ART
            and archivo.stem.casefold() == nombre.casefold()
        ):
            return archivo.resolve()

    raise FileNotFoundError(
        f"No se encontró la fotografía {nombre!r} en {directorio}."
    )


def obtener_fotos_art() -> list[str]:
    """Devuelve anverso y reverso del ART en el orden requerido.

    Durante la migración se acepta también la ubicación antigua. Esto evita
    perder archivos locales ignorados por Git; la ruta nueva tiene prioridad.
    """

    directorios = (
        ART_DIR,
        PROJECT_ROOT / "automatizacion" / "data" / "art",
    )

    for directorio in directorios:
        try:
            return [
                str(buscar_imagen_por_nombre(directorio, nombre))
                for nombre in NOMBRES_FOTOS_ART
            ]
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        "No se encontraron ART.jpg y ART_atras.jpg. Guárdalas en "
        f"{ART_DIR}."
    )
