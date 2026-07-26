"""Ejecución de Playwright fuera del hilo de la interfaz."""

from __future__ import annotations

import contextlib
import io
import threading
import traceback

from PySide6.QtCore import QObject, Signal, Slot

from gui.planificador import MantenimientoPlanificado, ubicacion_psinet
from psinet.descargas import descargar_pdf_abierto
from psinet.login import login_psinet
from psinet.navegador import iniciar_navegador
from psinet.tareas import crear_mantenimiento


class _SalidaSenal(io.TextIOBase):
    """Convierte las escrituras de print() en mensajes para la GUI."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._pendiente = ""

    def write(self, texto: str) -> int:
        self._pendiente += texto

        while "\n" in self._pendiente:
            linea, self._pendiente = self._pendiente.split("\n", 1)
            if linea.strip():
                self._callback(linea)

        return len(texto)

    def flush(self) -> None:
        if self._pendiente.strip():
            self._callback(self._pendiente)
        self._pendiente = ""


class EjecutorPSINet(QObject):
    """Procesa un plan completo usando una sola sesión de navegador."""

    mensaje = Signal(str)
    progreso = Signal(int, int, str)
    espera_foto = Signal(str)
    finalizado = Signal()
    detenido = Signal()
    error = Signal(str)

    def __init__(
        self,
        division: str,
        plan: list[MantenimientoPlanificado],
        participantes: list[str],
        apr_participa: bool,
        equipo_alza_hombre: bool,
        fotos_art: list[str],
        observacion: str,
    ):
        super().__init__()
        self.division = division
        self.plan = plan
        self.participantes = participantes
        self.apr_participa = apr_participa
        self.equipo_alza_hombre = equipo_alza_hombre
        self.fotos_art = fotos_art
        self.observacion = observacion
        self._confirmacion_foto = threading.Event()
        self._detener = threading.Event()

    def confirmar_foto(self) -> None:
        self._confirmacion_foto.set()

    def solicitar_detencion(self) -> None:
        self._detener.set()
        self._confirmacion_foto.set()

    def _emitir_salida(self, texto: str) -> None:
        self.mensaje.emit(texto)

    @Slot()
    def ejecutar(self) -> None:
        salida = _SalidaSenal(self._emitir_salida)

        try:
            ubicacion = ubicacion_psinet(self.division)
            total = len(self.plan)

            with contextlib.redirect_stdout(salida):
                with iniciar_navegador(headless=False) as page:
                    login_psinet(page)
                    modo_navegacion = "completa"

                    for indice, item in enumerate(self.plan, start=1):
                        if self._detener.is_set():
                            self.detenido.emit()
                            return

                        self.progreso.emit(indice, total, item.camara)
                        evidencia = {
                            "area": item.camara,
                            "area_busqueda": item.camara,
                            "division": self.division,
                            "ubicacion_psinet": ubicacion,
                            "hora_inicio": item.hora_inicio,
                            "hora_fin": item.hora_fin,
                            "participantes": self.participantes.copy(),
                            "apr_participa": self.apr_participa,
                            "equipo_alza_hombre": self.equipo_alza_hombre,
                            "fotos": self.fotos_art.copy(),
                            "observacion": self.observacion,
                        }

                        crear_mantenimiento(
                            page=page,
                            evidencia=evidencia,
                            modo_navegacion=modo_navegacion,
                        )

                        self._confirmacion_foto.clear()
                        self.espera_foto.emit(item.camara)
                        self._confirmacion_foto.wait()

                        if self._detener.is_set():
                            self.detenido.emit()
                            return

                        self.mensaje.emit(
                            "Guardando mantención y descargando PDF..."
                        )

                        with page.expect_popup(timeout=30_000) as popup_info:
                            page.get_by_role(
                                "button",
                                name="Guardar",
                                exact=True,
                            ).click()

                        pagina_pdf = popup_info.value
                        pagina_pdf.wait_for_load_state("domcontentloaded")
                        descargar_pdf_abierto(page)
                        modo_navegacion = "solo_nueva"

            salida.flush()
            self.finalizado.emit()
        except Exception:
            salida.flush()
            self.error.emit(traceback.format_exc())
