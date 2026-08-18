"""Ejecución de Playwright fuera del hilo de la interfaz."""

from __future__ import annotations

import contextlib
import io
import threading
import traceback
from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from cctvflow.checkpoint import (
    ESTADO_COMPLETADO,
    ESTADO_EN_PROCESO,
    ESTADO_ERROR,
    ESTADO_INCOMPLETO,
    actualizar_estado,
    cargar_checkpoint,
    resumen_checkpoint,
)
from cctvflow.models import (
    MantenimientoPlanificado,
    SolicitudMantenimiento,
    normalizar_fecha_mantenimiento,
)
from cctvflow.planning import ubicacion_portal
from cctvflow.portal.authentication import iniciar_sesion
from cctvflow.portal.browser import iniciar_navegador
from cctvflow.portal.reports import (
    PdfMantenimientoIncompletoError,
    descargar_pdf_abierto,
    validar_pdf_mantenimiento,
)
from cctvflow.portal.workflow import crear_mantenimiento
from cctvflow.server_client import (
    CCTVFlowServerClient,
    ServerClientError,
    build_maintenance_event,
    configured_server_client,
    maintenance_event_id,
)


class EjecucionDetenidaError(RuntimeError):
    """Interrumpe limpiamente una espera manual solicitada desde la GUI."""


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


class EjecutorMantenimientos(QObject):
    """Procesa un plan completo usando una sola sesión de navegador."""

    mensaje = Signal(str)
    progreso = Signal(int, int, str)
    espera_manual = Signal(str, str)
    finalizado = Signal()
    detenido = Signal()
    error = Signal(str)
    resultado_limpieza = Signal(bool)
    resumen = Signal(object)

    def __init__(
        self,
        division: str,
        plan: list[MantenimientoPlanificado],
        participantes: list[str],
        apr_participa: bool,
        equipo_alza_hombre: bool,
        fotos_art: list[str],
        observacion: str,
        fecha_mantenimiento: str | None = None,
        fotos_por_camara: dict[str, list[str]] | None = None,
        fotos_art_por_sector: dict[str, list[str]] | None = None,
        eliminar_fotos_tras_exito: bool = False,
        eliminar_art_tras_exito: bool = False,
        checkpoint_path: str | None = None,
        server_client: CCTVFlowServerClient | None = None,
    ):
        super().__init__()
        self.division = division
        self.plan = plan
        self.participantes = participantes
        self.apr_participa = apr_participa
        self.equipo_alza_hombre = equipo_alza_hombre
        self.fotos_art = fotos_art
        self.observacion = observacion
        self.fecha_mantenimiento = normalizar_fecha_mantenimiento(
            fecha_mantenimiento or date.today().isoformat()
        )
        self.fotos_por_camara = fotos_por_camara or {}
        self.fotos_art_por_sector = fotos_art_por_sector or {}
        self.eliminar_fotos_tras_exito = eliminar_fotos_tras_exito
        self.eliminar_art_tras_exito = eliminar_art_tras_exito
        self.checkpoint_path = checkpoint_path
        self.server_client = server_client
        self.modo_automatico = bool(self.fotos_por_camara)
        self._confirmacion_foto = threading.Event()
        self._esperando_confirmacion = threading.Event()
        self._detener = threading.Event()
        self._event_ids = {
            item.camara: maintenance_event_id(
                item.camara,
                checkpoint_path,
            )
            for item in plan
        }

    def confirmar_paso_manual(self) -> None:
        self._confirmacion_foto.set()

    def confirmar_foto(self) -> None:
        """Alias conservado para compatibilidad con versiones anteriores."""

        self.confirmar_paso_manual()

    def solicitar_detencion(self) -> None:
        self._detener.set()
        self._confirmacion_foto.set()

    def _esperar_confirmacion_manual(
        self,
        mensaje: str,
        texto_boton: str = "Selección lista · Continuar",
    ) -> None:
        self._confirmacion_foto.clear()
        self._esperando_confirmacion.set()

        try:
            self.espera_manual.emit(mensaje, texto_boton)
            self._confirmacion_foto.wait()

            if self._detener.is_set():
                raise EjecucionDetenidaError(
                    "Ejecución detenida durante una confirmación manual."
                )
        finally:
            self._esperando_confirmacion.clear()

    def _emitir_salida(self, texto: str) -> None:
        self.mensaje.emit(texto)

    def _fotos_item(self, item: MantenimientoPlanificado) -> list[str]:
        if not self.modo_automatico:
            return self.fotos_art.copy()

        return [
            *self.fotos_art_por_sector[item.sector],
            *self.fotos_por_camara[item.camara],
        ]

    def _eliminar_archivos(
        self,
        rutas: list[str],
        tipo: str,
    ) -> bool:
        """Elimina solo archivos explícitos de un lote ya confirmado."""

        eliminacion_completa = True

        for ruta_texto in dict.fromkeys(rutas):
            ruta = Path(ruta_texto)

            if not ruta.is_file():
                continue

            try:
                ruta.unlink()
            except OSError as error:
                self.mensaje.emit(f"No se pudo eliminar {tipo} {ruta.name}: {error}")
                eliminacion_completa = False
                continue

            self.mensaje.emit(f"Eliminada {tipo}: {ruta.name}")

        return eliminacion_completa

    def _guardar_y_descargar(
        self,
        page,
        cantidad_fotos_esperadas: int,
    ) -> Path:
        self.mensaje.emit("Guardando mantención y descargando PDF...")

        with page.expect_popup(timeout=30_000) as popup_info:
            page.get_by_role(
                "button",
                name="Guardar",
                exact=True,
            ).click()

        pagina_pdf = popup_info.value
        pagina_pdf.wait_for_load_state("domcontentloaded")
        destino_pdf = descargar_pdf_abierto(page)

        if destino_pdf is None:
            raise RuntimeError(
                "El portal guardó la mantención, pero CCTVFlow no pudo "
                "confirmar la descarga del PDF. Las fotografías se "
                "conservarán para revisión."
            )

        validar_pdf_mantenimiento(
            ruta_pdf=destino_pdf,
            cantidad_fotos_esperadas=cantidad_fotos_esperadas,
        )
        return destino_pdf

    def _actualizar_checkpoint(
        self,
        camara: str,
        estado: str,
        *,
        pdf: str | Path | None = None,
        detalle: str | None = None,
    ) -> None:
        if self.checkpoint_path is None:
            return

        actualizar_estado(
            camara,
            estado,
            pdf=pdf,
            detalle=detalle,
            ruta=self.checkpoint_path,
        )

    def _emitir_resumen_checkpoint(self) -> None:
        if self.checkpoint_path is None:
            return

        datos = cargar_checkpoint(self.checkpoint_path)

        if datos is not None:
            self.resumen.emit(resumen_checkpoint(datos))

    def _conectar_servidor(self) -> None:
        if self.server_client is None:
            self.server_client = configured_server_client()

        if self.server_client is None:
            self.mensaje.emit("Servidor central no configurado: ejecución solo local.")
            return

        response = self.server_client.heartbeat()
        if response.get("status") != "ok":
            raise ServerClientError("El servidor no confirmó el agente.")
        self.mensaje.emit("Agente conectado a CCTVFlow Web.")

    def _reportar_mantenimiento(
        self,
        item: MantenimientoPlanificado,
        status: str,
        photo_count: int,
        *,
        pdf: str | Path | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        if self.server_client is None:
            return

        event = build_maintenance_event(
            event_id=self._event_ids[item.camara],
            maintenance_date=self.fecha_mantenimiento,
            camera_name=item.camara,
            division=self.division,
            status=status,
            photo_count=photo_count,
            pdf=pdf,
            detail=detail,
        )
        try:
            self.server_client.report_maintenance(event)
        except ServerClientError as error:
            self.mensaje.emit(
                "No se pudo sincronizar el estado con el servidor; "
                f"la ejecución local continúa. Detalle: {error}"
            )

    @Slot()
    def ejecutar(self) -> None:
        salida = _SalidaSenal(self._emitir_salida)

        try:
            ubicacion = ubicacion_portal(self.division)
            total = len(self.plan)

            try:
                self._conectar_servidor()
            except ServerClientError as error:
                self.mensaje.emit(
                    "CCTVFlow Web no está disponible; la ejecución local "
                    f"continúa. Detalle: {error}"
                )
                self.server_client = None

            with contextlib.redirect_stdout(salida):
                with iniciar_navegador(headless=False) as page:
                    iniciar_sesion(page)
                    modo_navegacion = "completa"
                    limpieza_evidencias_completa = True

                    for indice, item in enumerate(self.plan, start=1):
                        if self._detener.is_set():
                            self.detenido.emit()
                            return

                        self.progreso.emit(indice, total, item.camara)
                        self._actualizar_checkpoint(
                            item.camara,
                            ESTADO_EN_PROCESO,
                        )
                        solicitud = SolicitudMantenimiento(
                            area=item.camara,
                            area_busqueda=item.camara,
                            division=self.division,
                            ubicacion_portal=ubicacion,
                            fecha_mantenimiento=self.fecha_mantenimiento,
                            hora_inicio=item.hora_inicio,
                            hora_fin=item.hora_fin,
                            participantes=tuple(self.participantes),
                            apr_participa=self.apr_participa,
                            equipo_alza_hombre=self.equipo_alza_hombre,
                            fotos=tuple(self._fotos_item(item)),
                            observacion=self.observacion,
                            dejar_campo_extra=not self.modo_automatico,
                            camara_ip=(self.division.strip().upper() == "DRT"),
                        )
                        cantidad_fotos_esperadas = len(solicitud.fotos)
                        if not self.modo_automatico:
                            # En el modo asistido se cargan las dos ART
                            # automáticamente y una evidencia manual.
                            cantidad_fotos_esperadas += 1

                        self._reportar_mantenimiento(
                            item,
                            "running",
                            cantidad_fotos_esperadas,
                        )

                        try:
                            crear_mantenimiento(
                                page=page,
                                solicitud=solicitud,
                                modo_navegacion=modo_navegacion,
                                confirmar_manual=(self._esperar_confirmacion_manual),
                            )

                            if not self.modo_automatico:
                                self._esperar_confirmacion_manual(
                                    "Sube manualmente la fotografía del "
                                    "mantenimiento en Chromium para "
                                    f"{item.camara}.",
                                    "Foto cargada · Guardar y continuar",
                                )

                            destino_pdf = self._guardar_y_descargar(
                                page,
                                cantidad_fotos_esperadas=(cantidad_fotos_esperadas),
                            )
                        except EjecucionDetenidaError:
                            self.detenido.emit()
                            return
                        except PdfMantenimientoIncompletoError as error:
                            limpieza_evidencias_completa = False
                            self._actualizar_checkpoint(
                                item.camara,
                                ESTADO_INCOMPLETO,
                                pdf=error.ruta_pdf,
                                detalle=str(error),
                            )
                            self.mensaje.emit(
                                "\n⚠ PDF INCOMPLETO · "
                                f"{item.camara}\n"
                                f"{error}\n"
                                "El portal alcanzó a guardar esta mantención. "
                                "CCTVFlow conservará sus fotografías, la "
                                "dejará marcada para revisión y continuará "
                                "con la cámara siguiente."
                            )
                            self._reportar_mantenimiento(
                                item,
                                "incomplete",
                                cantidad_fotos_esperadas,
                                pdf=error.ruta_pdf,
                                detail={
                                    "reason": "pdf_incomplete",
                                    "actual_pages": error.paginas_reales,
                                    "minimum_pages": error.paginas_minimas,
                                },
                            )
                            modo_navegacion = "solo_nueva"
                            continue
                        except Exception as error:
                            self._actualizar_checkpoint(
                                item.camara,
                                ESTADO_ERROR,
                                detalle=str(error),
                            )
                            self._reportar_mantenimiento(
                                item,
                                "error",
                                cantidad_fotos_esperadas,
                                detail={"error_type": type(error).__name__},
                            )
                            raise

                        if self.modo_automatico and self.eliminar_fotos_tras_exito:
                            limpieza_evidencias_completa = (
                                self._eliminar_archivos(
                                    self.fotos_por_camara[item.camara],
                                    "evidencia",
                                )
                                and limpieza_evidencias_completa
                            )

                        self._actualizar_checkpoint(
                            item.camara,
                            ESTADO_COMPLETADO,
                            pdf=destino_pdf,
                        )
                        self._reportar_mantenimiento(
                            item,
                            "completed",
                            cantidad_fotos_esperadas,
                            pdf=destino_pdf,
                            detail={
                                "mode": (
                                    "automatic" if self.modo_automatico else "assisted"
                                )
                            },
                        )
                        modo_navegacion = "solo_nueva"

                    if (
                        self.modo_automatico
                        and self.eliminar_fotos_tras_exito
                        and self.eliminar_art_tras_exito
                        and limpieza_evidencias_completa
                    ):
                        fotos_art = [
                            foto
                            for sector in {item.sector for item in self.plan}
                            for foto in self.fotos_art_por_sector[sector]
                        ]
                        limpieza_evidencias_completa = (
                            self._eliminar_archivos(fotos_art, "ART")
                            and limpieza_evidencias_completa
                        )
                    elif (
                        self.modo_automatico
                        and self.eliminar_fotos_tras_exito
                        and not self.eliminar_art_tras_exito
                    ):
                        self.mensaje.emit(
                            "Las ART se conservaron porque el plan no "
                            "incluyó todas las cámaras detectadas."
                        )
                    elif (
                        self.modo_automatico
                        and self.eliminar_fotos_tras_exito
                        and not limpieza_evidencias_completa
                    ):
                        self.mensaje.emit(
                            "Las ART se conservaron porque no fue posible "
                            "limpiar todas las evidencias."
                        )

            self.resultado_limpieza.emit(limpieza_evidencias_completa)
            self._emitir_resumen_checkpoint()
            salida.flush()
            self.finalizado.emit()
        except Exception:
            self._emitir_resumen_checkpoint()
            salida.flush()
            self.error.emit(traceback.format_exc())
