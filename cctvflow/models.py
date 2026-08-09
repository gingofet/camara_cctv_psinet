"""Modelos inmutables compartidos por la interfaz y la automatización."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MantenimientoPlanificado:
    """Una cámara con el intervalo asignado dentro de un lote."""

    sector: str
    camara: str
    hora_inicio: str
    hora_fin: str


@dataclass(frozen=True, slots=True)
class SolicitudMantenimiento:
    """Datos validados necesarios para completar una mantención."""

    area: str
    area_busqueda: str
    division: str
    ubicacion_portal: str
    hora_inicio: str
    hora_fin: str
    participantes: tuple[str, ...]
    apr_participa: bool
    equipo_alza_hombre: bool
    fotos: tuple[str, ...]
    observacion: str
    dejar_campo_extra: bool
    camara_ip: bool

    def __post_init__(self) -> None:
        campos_requeridos = {
            "area": self.area,
            "area_busqueda": self.area_busqueda,
            "ubicacion_portal": self.ubicacion_portal,
            "hora_inicio": self.hora_inicio,
            "hora_fin": self.hora_fin,
        }

        vacios = [
            nombre
            for nombre, valor in campos_requeridos.items()
            if not valor.strip()
        ]

        if vacios:
            raise ValueError(
                "Faltan datos requeridos del mantenimiento: "
                + ", ".join(vacios)
            )
