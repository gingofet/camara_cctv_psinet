"""Ventana principal de CCTVFlow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTime, Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from automatizacion.data.config import (
    OBSERVACION_DEFAULT,
    PARTICIPANTES_DEFAULT,
)
from gui.planificador import (
    cargar_catalogo,
    divisiones_disponibles,
    filtrar_camaras,
    generar_plan,
)
from gui.worker import EjecutorPSINet
from psinet_auto_manual import obtener_fotos_art


FILTRO_IMAGENES = "Imágenes (*.jpg *.jpeg *.png)"
OBSERVACIONES_SUGERIDAS = [
    OBSERVACION_DEFAULT,
    "Mantenimiento preventivo CCTV",
    "Limpieza, inspección y ajuste de cámara CCTV",
    "Revisión de funcionamiento y conectividad CCTV",
]


class VentanaCCTVFlow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTVFlow · PSINet")
        self.resize(1180, 760)

        self.catalogo: dict[str, list[str]] = {}
        self.seleccionadas: set[str] = set()
        self.plan_actual = []
        self.hilo: QThread | None = None
        self.ejecutor: EjecutorPSINet | None = None

        self._construir_interfaz()
        self._conectar_eventos()
        self._cambiar_division()

    def _construir_interfaz(self) -> None:
        central = QWidget()
        principal = QVBoxLayout(central)

        titulo = QLabel("CCTVFlow")
        titulo.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitulo = QLabel(
            "Planificación y ejecución de mantenciones preventivas en PSINet"
        )
        principal.addWidget(titulo)
        principal.addWidget(subtitulo)

        configuracion = QGroupBox("Configuración")
        formulario = QFormLayout(configuracion)

        self.combo_division = QComboBox()
        self.combo_division.addItems(divisiones_disponibles())
        self.combo_sector = QComboBox()
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Filtrar por nombre o código...")
        self.hora_inicio = QTimeEdit()
        self.hora_inicio.setDisplayFormat("HH:mm")
        self.hora_inicio.setTime(QTime.currentTime())
        self.duracion = QSpinBox()
        self.duracion.setRange(1, 240)
        self.duracion.setValue(10)
        self.duracion.setSuffix(" min")
        self.participantes = QLineEdit(", ".join(PARTICIPANTES_DEFAULT))
        self.apr = QCheckBox("Sí")
        self.alza = QCheckBox("Sí")
        self.observacion = QComboBox()
        self.observacion.setEditable(True)
        self.observacion.addItems(OBSERVACIONES_SUGERIDAS)

        self.art_anverso = QLineEdit()
        self.art_anverso.setReadOnly(True)
        self.art_reverso = QLineEdit()
        self.art_reverso.setReadOnly(True)
        self.boton_art_anverso = QPushButton("Examinar…")
        self.boton_art_reverso = QPushButton("Examinar…")

        fila_art_anverso = QHBoxLayout()
        fila_art_anverso.addWidget(self.art_anverso, 1)
        fila_art_anverso.addWidget(self.boton_art_anverso)

        fila_art_reverso = QHBoxLayout()
        fila_art_reverso.addWidget(self.art_reverso, 1)
        fila_art_reverso.addWidget(self.boton_art_reverso)

        formulario.addRow("División", self.combo_division)
        formulario.addRow("Sector", self.combo_sector)
        formulario.addRow("Buscar cámara", self.busqueda)
        formulario.addRow("Hora inicial", self.hora_inicio)
        formulario.addRow("Duración por cámara", self.duracion)
        formulario.addRow("Participantes", self.participantes)
        formulario.addRow("APR participa", self.apr)
        formulario.addRow("Equipo alza hombre", self.alza)
        formulario.addRow("Observaciones", self.observacion)
        formulario.addRow("ART anverso", fila_art_anverso)
        formulario.addRow("ART reverso", fila_art_reverso)
        principal.addWidget(configuracion)

        self._cargar_art_predeterminadas()

        divisor = QSplitter(Qt.Orientation.Horizontal)

        bloque_camaras = QWidget()
        layout_camaras = QVBoxLayout(bloque_camaras)
        self.etiqueta_resultados = QLabel()
        self.lista_camaras = QListWidget()
        self.lista_camaras.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        botones_lista = QHBoxLayout()
        self.boton_todas = QPushButton("Marcar visibles")
        self.boton_limpiar = QPushButton("Limpiar selección")
        botones_lista.addWidget(self.boton_todas)
        botones_lista.addWidget(self.boton_limpiar)
        layout_camaras.addWidget(self.etiqueta_resultados)
        layout_camaras.addWidget(self.lista_camaras)
        layout_camaras.addLayout(botones_lista)

        bloque_plan = QWidget()
        layout_plan = QVBoxLayout(bloque_plan)
        self.etiqueta_plan = QLabel("Plan: 0 mantenciones")
        self.tabla_plan = QTableWidget(0, 4)
        self.tabla_plan.setHorizontalHeaderLabels(
            ["Sector", "Cámara", "Inicio", "Fin"]
        )
        self.tabla_plan.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tabla_plan.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tabla_plan.horizontalHeader().setStretchLastSection(True)
        layout_plan.addWidget(self.etiqueta_plan)
        layout_plan.addWidget(self.tabla_plan)

        divisor.addWidget(bloque_camaras)
        divisor.addWidget(bloque_plan)
        divisor.setSizes([520, 660])
        principal.addWidget(divisor, 1)

        self.pestanas = QTabWidget()
        panel_ejecucion = QWidget()
        layout_ejecucion = QVBoxLayout(panel_ejecucion)
        self.estado = QLabel("Listo para planificar.")
        self.progreso = QProgressBar()
        self.progreso.setRange(0, 1)
        self.progreso.setValue(0)
        self.registro = QTextEdit()
        self.registro.setReadOnly(True)
        self.registro.setMinimumHeight(120)
        layout_ejecucion.addWidget(self.estado)
        layout_ejecucion.addWidget(self.progreso)
        layout_ejecucion.addWidget(self.registro)
        self.pestanas.addTab(panel_ejecucion, "Ejecución")
        principal.addWidget(self.pestanas)

        acciones = QHBoxLayout()
        self.boton_actualizar = QPushButton("Actualizar plan")
        self.boton_ejecutar = QPushButton("Ejecutar en PSINet")
        self.boton_confirmar = QPushButton(
            "Foto cargada · Guardar y continuar"
        )
        self.boton_confirmar.setEnabled(False)
        self.boton_detener = QPushButton("Detener")
        self.boton_detener.setEnabled(False)
        acciones.addWidget(self.boton_actualizar)
        acciones.addStretch()
        acciones.addWidget(self.boton_confirmar)
        acciones.addWidget(self.boton_detener)
        acciones.addWidget(self.boton_ejecutar)
        principal.addLayout(acciones)

        self.setCentralWidget(central)

    def _conectar_eventos(self) -> None:
        self.combo_division.currentTextChanged.connect(
            self._cambiar_division
        )
        self.combo_sector.currentTextChanged.connect(self._refrescar_lista)
        self.busqueda.textChanged.connect(self._refrescar_lista)
        self.lista_camaras.itemChanged.connect(self._cambio_seleccion)
        self.boton_todas.clicked.connect(self._marcar_visibles)
        self.boton_limpiar.clicked.connect(self._limpiar_seleccion)
        self.boton_actualizar.clicked.connect(self._actualizar_plan)
        self.boton_ejecutar.clicked.connect(self._iniciar_ejecucion)
        self.boton_confirmar.clicked.connect(self._confirmar_foto)
        self.boton_detener.clicked.connect(self._detener)
        self.boton_art_anverso.clicked.connect(
            lambda: self._elegir_foto_art(self.art_anverso)
        )
        self.boton_art_reverso.clicked.connect(
            lambda: self._elegir_foto_art(self.art_reverso)
        )

    def _cargar_art_predeterminadas(self) -> None:
        """Muestra las ART permanentes si están disponibles."""

        try:
            fotos = obtener_fotos_art()
        except (FileNotFoundError, ValueError):
            return

        if len(fotos) >= 2:
            self.art_anverso.setText(fotos[0])
            self.art_reverso.setText(fotos[1])

    def _elegir_foto_art(self, destino: QLineEdit) -> None:
        ruta_actual = destino.text().strip()
        directorio = (
            str(Path(ruta_actual).parent)
            if ruta_actual
            else str(Path.home())
        )
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar fotografía ART",
            directorio,
            FILTRO_IMAGENES,
        )

        if ruta:
            destino.setText(ruta)

    def _fotos_art(self) -> list[str]:
        fotos = [
            self.art_anverso.text().strip(),
            self.art_reverso.text().strip(),
        ]

        if not all(fotos):
            raise ValueError(
                "Selecciona las fotografías de anverso y reverso del ART."
            )

        for foto in fotos:
            ruta = Path(foto)

            if not ruta.is_file():
                raise FileNotFoundError(
                    f"No se encontró la fotografía ART: {ruta}"
                )

            if ruta.suffix.casefold() not in {".jpg", ".jpeg", ".png"}:
                raise ValueError(
                    f"Formato de imagen no permitido: {ruta.name}"
                )

        return fotos

    def _observacion(self) -> str:
        return self.observacion.currentText().strip() or OBSERVACION_DEFAULT

    @Slot()
    def _cambiar_division(self) -> None:
        try:
            self.catalogo = cargar_catalogo(self.combo_division.currentText())
        except Exception as error:
            QMessageBox.critical(self, "Catálogo", str(error))
            return

        self.seleccionadas.clear()
        self.combo_sector.blockSignals(True)
        self.combo_sector.clear()
        self.combo_sector.addItem("Todos los sectores", None)

        for sector in self.catalogo:
            self.combo_sector.addItem(sector, sector)

        self.combo_sector.blockSignals(False)
        self._refrescar_lista()
        self._actualizar_plan()

    @Slot()
    def _refrescar_lista(self) -> None:
        sector = self.combo_sector.currentData()
        resultados = filtrar_camaras(
            self.catalogo,
            sector=sector,
            consulta=self.busqueda.text(),
        )

        self.lista_camaras.blockSignals(True)
        self.lista_camaras.clear()

        for nombre_sector, camara in resultados:
            item = QListWidgetItem(f"[{nombre_sector}] {camara}")
            item.setData(Qt.ItemDataRole.UserRole, (nombre_sector, camara))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            estado = (
                Qt.CheckState.Checked
                if camara in self.seleccionadas
                else Qt.CheckState.Unchecked
            )
            item.setCheckState(estado)
            self.lista_camaras.addItem(item)

        self.lista_camaras.blockSignals(False)
        self.etiqueta_resultados.setText(
            f"{len(resultados)} cámaras visibles · "
            f"{len(self.seleccionadas)} seleccionadas"
        )

    @Slot(QListWidgetItem)
    def _cambio_seleccion(self, item: QListWidgetItem) -> None:
        _, camara = item.data(Qt.ItemDataRole.UserRole)

        if item.checkState() == Qt.CheckState.Checked:
            self.seleccionadas.add(camara)
        else:
            self.seleccionadas.discard(camara)

        self._refrescar_etiqueta()
        self._actualizar_plan()

    def _refrescar_etiqueta(self) -> None:
        self.etiqueta_resultados.setText(
            f"{self.lista_camaras.count()} cámaras visibles · "
            f"{len(self.seleccionadas)} seleccionadas"
        )

    @Slot()
    def _marcar_visibles(self) -> None:
        for indice in range(self.lista_camaras.count()):
            item = self.lista_camaras.item(indice)
            _, camara = item.data(Qt.ItemDataRole.UserRole)
            self.seleccionadas.add(camara)
            item.setCheckState(Qt.CheckState.Checked)

        self._actualizar_plan()

    @Slot()
    def _limpiar_seleccion(self) -> None:
        self.seleccionadas.clear()
        self._refrescar_lista()
        self._actualizar_plan()

    def _seleccion_ordenada(self) -> list[tuple[str, str]]:
        seleccion: list[tuple[str, str]] = []

        for sector, camaras in self.catalogo.items():
            for camara in camaras:
                if camara in self.seleccionadas:
                    seleccion.append((sector, camara))

        return seleccion

    @Slot()
    def _actualizar_plan(self) -> None:
        hora = self.hora_inicio.time().toString("HH:mm")
        self.plan_actual = generar_plan(
            self._seleccion_ordenada(),
            hora,
            self.duracion.value(),
        )

        self.tabla_plan.setRowCount(len(self.plan_actual))

        for fila, item in enumerate(self.plan_actual):
            valores = (
                item.sector,
                item.camara,
                item.hora_inicio,
                item.hora_fin,
            )

            for columna, valor in enumerate(valores):
                self.tabla_plan.setItem(
                    fila,
                    columna,
                    QTableWidgetItem(valor),
                )

        self.tabla_plan.resizeColumnsToContents()
        self.etiqueta_plan.setText(
            f"Plan: {len(self.plan_actual)} mantenciones"
        )

    def _participantes(self) -> list[str]:
        return [
            nombre.strip()
            for nombre in self.participantes.text().split(",")
            if nombre.strip()
        ]

    @Slot()
    def _iniciar_ejecucion(self) -> None:
        self._actualizar_plan()

        if not self.plan_actual:
            QMessageBox.warning(
                self,
                "Sin cámaras",
                "Selecciona al menos una cámara.",
            )
            return

        if not self._participantes():
            QMessageBox.warning(
                self,
                "Sin participantes",
                "Configura al menos un participante.",
            )
            return

        try:
            fotos_art = self._fotos_art()
        except Exception as error:
            QMessageBox.critical(self, "Fotografías ART", str(error))
            return

        confirmacion = QMessageBox.question(
            self,
            "Iniciar ejecución",
            f"Se procesarán {len(self.plan_actual)} mantenciones en "
            f"{self.combo_division.currentText()}.\n\n"
            "¿Deseas abrir PSINet y continuar?",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        self.hilo = QThread(self)
        self.ejecutor = EjecutorPSINet(
            division=self.combo_division.currentText(),
            plan=self.plan_actual.copy(),
            participantes=self._participantes(),
            apr_participa=self.apr.isChecked(),
            equipo_alza_hombre=self.alza.isChecked(),
            fotos_art=fotos_art,
            observacion=self._observacion(),
        )
        self.ejecutor.moveToThread(self.hilo)
        self.hilo.started.connect(self.ejecutor.ejecutar)
        self.ejecutor.mensaje.connect(self._registrar)
        self.ejecutor.progreso.connect(self._mostrar_progreso)
        self.ejecutor.espera_foto.connect(self._esperar_foto)
        self.ejecutor.finalizado.connect(self._ejecucion_finalizada)
        self.ejecutor.detenido.connect(self._ejecucion_detenida)
        self.ejecutor.error.connect(self._ejecucion_error)

        for senal in (
            self.ejecutor.finalizado,
            self.ejecutor.detenido,
            self.ejecutor.error,
        ):
            senal.connect(self.hilo.quit)

        self.hilo.finished.connect(self.ejecutor.deleteLater)
        self.hilo.finished.connect(self.hilo.deleteLater)
        self.hilo.finished.connect(self._limpiar_hilo)

        self.registro.clear()
        self.progreso.setRange(0, len(self.plan_actual))
        self._bloquear_configuracion(True)
        self.estado.setText("Abriendo Chromium e iniciando sesión...")
        self.hilo.start()

    def _bloquear_configuracion(self, ejecutando: bool) -> None:
        for control in (
            self.combo_division,
            self.combo_sector,
            self.busqueda,
            self.lista_camaras,
            self.hora_inicio,
            self.duracion,
            self.participantes,
            self.apr,
            self.alza,
            self.observacion,
            self.art_anverso,
            self.art_reverso,
            self.boton_art_anverso,
            self.boton_art_reverso,
            self.boton_todas,
            self.boton_limpiar,
            self.boton_actualizar,
            self.boton_ejecutar,
        ):
            control.setEnabled(not ejecutando)

        self.boton_detener.setEnabled(ejecutando)

    @Slot(str)
    def _registrar(self, texto: str) -> None:
        self.registro.append(texto)
        barra = self.registro.verticalScrollBar()
        barra.setValue(barra.maximum())

    @Slot(int, int, str)
    def _mostrar_progreso(self, actual: int, total: int, camara: str) -> None:
        self.progreso.setRange(0, total)
        self.progreso.setValue(actual - 1)
        self.estado.setText(f"Preparando {actual}/{total}: {camara}")
        self._registrar(f"\n▶ {actual}/{total} · {camara}")

    @Slot(str)
    def _esperar_foto(self, camara: str) -> None:
        self.estado.setText(
            f"Sube la fotografía del mantenimiento en Chromium: {camara}"
        )
        self.boton_confirmar.setEnabled(True)
        QApplication.alert(self, 0)
        QMessageBox.information(
            self,
            "Fotografía pendiente",
            "Las fotografías ART ya fueron cargadas.\n\n"
            "Sube manualmente la fotografía del mantenimiento en Chromium "
            "y luego presiona «Foto cargada · Guardar y continuar».",
        )

    @Slot()
    def _confirmar_foto(self) -> None:
        if self.ejecutor is None:
            return

        self.boton_confirmar.setEnabled(False)
        self.estado.setText("Guardando la mantención...")
        self.ejecutor.confirmar_foto()

    @Slot()
    def _detener(self) -> None:
        if self.ejecutor is None:
            return

        self.estado.setText(
            "Detención solicitada; se cerrará al terminar el paso actual."
        )
        self.boton_detener.setEnabled(False)
        self.ejecutor.solicitar_detencion()

    @Slot()
    def _ejecucion_finalizada(self) -> None:
        self.progreso.setValue(self.progreso.maximum())
        self.estado.setText("Plan completado correctamente.")
        self._registrar("\n✓ Ejecución finalizada.")
        self._bloquear_configuracion(False)
        self.boton_confirmar.setEnabled(False)

    @Slot()
    def _ejecucion_detenida(self) -> None:
        self.estado.setText("Ejecución detenida.")
        self._registrar("\n■ Ejecución detenida por el usuario.")
        self._bloquear_configuracion(False)
        self.boton_confirmar.setEnabled(False)

    @Slot(str)
    def _ejecucion_error(self, detalle: str) -> None:
        self.estado.setText("La ejecución terminó con un error.")
        self._registrar(f"\nERROR:\n{detalle}")
        self._bloquear_configuracion(False)
        self.boton_confirmar.setEnabled(False)
        QMessageBox.critical(
            self,
            "Error de ejecución",
            "CCTVFlow encontró un error. Revisa el registro de ejecución.",
        )

    @Slot()
    def _limpiar_hilo(self) -> None:
        self.hilo = None
        self.ejecutor = None

    def closeEvent(self, evento: QCloseEvent) -> None:
        if self.hilo is not None and self.hilo.isRunning():
            QMessageBox.warning(
                self,
                "Ejecución activa",
                "Detén la ejecución antes de cerrar CCTVFlow.",
            )
            evento.ignore()
            return

        evento.accept()
