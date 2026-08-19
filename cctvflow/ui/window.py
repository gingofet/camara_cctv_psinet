"""Ventana principal de CCTVFlow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, Qt, QThread, QTime, QTimer, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
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

from cctvflow.checkpoint import (
    CHECKPOINT_PATH,
    ESTADO_EN_PROCESO,
    ESTADO_ERROR,
    ESTADO_INCOMPLETO,
    cargar_checkpoint,
    crear_checkpoint,
    plan_pendiente,
    resumen_checkpoint,
)
from cctvflow.config import (
    OBSERVACION_DEFAULT,
    PARTICIPANTES_DEFAULT,
)
from cctvflow.photo_batch import (
    EXTENSIONES_IMAGEN,
    LoteFotografico,
    analizar_carpeta,
    validar_lote,
)
from cctvflow.planning import (
    MantenimientoPlanificado,
    cargar_catalogo,
    divisiones_disponibles,
    filtrar_camaras,
    generar_plan,
)
from cctvflow.resources import obtener_fotos_art
from cctvflow.ui.runner import EjecutorMantenimientos

if TYPE_CHECKING:
    from cctvflow.server_client import AgentIdentity, CCTVFlowServerClient
    from cctvflow.ui.theme import ThemeController


FILTRO_IMAGENES = "Imágenes (*.jpg *.jpeg *.png)"
OBSERVACIONES_SUGERIDAS = [
    OBSERVACION_DEFAULT,
    "Mantenimiento preventivo CCTV",
    "Limpieza, inspección y ajuste de cámara CCTV",
    "Revisión de funcionamiento y conectividad CCTV",
]
RUTA_LOGO = Path(__file__).resolve().parent / "assets" / "cctvflow_logo.svg"


class VentanaCCTVFlow(QMainWindow):
    def __init__(
        self,
        theme_controller: ThemeController | None = None,
        server_client: CCTVFlowServerClient | None = None,
        server_autoconfigure: bool = True,
        user_identity: AgentIdentity | None = None,
    ):
        super().__init__()
        self.theme_controller = theme_controller
        self.server_client = server_client
        self.server_autoconfigure = server_autoconfigure
        self.user_identity = user_identity
        self.setWindowTitle("CCTVFlow")
        self.resize(1180, 700)
        self.setMinimumSize(980, 640)

        self.catalogo: dict[str, list[str]] = {}
        self.seleccionadas: set[str] = set()
        self.plan_actual = []
        self.lote_fotos: LoteFotografico | None = None
        self.arts_por_sector: dict[str, list[str]] = {}
        self.lote_completo_en_ejecucion = False
        self.limpieza_lote_completa = False
        self.resumen_ejecucion: dict[str, int] = {}
        self.checkpoint_activo: str | None = None
        self.hilo: QThread | None = None
        self.ejecutor: EjecutorMantenimientos | None = None
        self._cerrar_al_finalizar = False

        self._construir_interfaz()
        self._conectar_eventos()
        self._cambiar_division()
        self._actualizar_boton_reanudar()

    def _construir_interfaz(self) -> None:
        central = QWidget()
        principal = QVBoxLayout(central)

        encabezado = QHBoxLayout()
        logo = QSvgWidget(str(RUTA_LOGO))
        logo.setFixedSize(310, 70)
        logo.setAccessibleName(
            "CCTVFlow · Automatización de mantenimiento CCTV"
        )
        encabezado.addWidget(
            logo,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        encabezado.addStretch()

        if self.user_identity is not None:
            identity = QLabel(
                f"{self.user_identity.display_name} · "
                f"{self.user_identity.device_name}"
            )
            identity.setToolTip(
                f"Sesión: {self.user_identity.username} · "
                f"Rol: {self.user_identity.role}"
            )
            encabezado.addWidget(identity)

        if self.theme_controller is not None:
            from cctvflow.ui.theme import THEME_OPTIONS

            encabezado.addWidget(QLabel("Tema"))
            self.combo_tema = QComboBox()
            self.combo_tema.setAccessibleName("Tema visual")
            for label, value in THEME_OPTIONS:
                self.combo_tema.addItem(label, value)
            selected = self.combo_tema.findData(self.theme_controller.mode)
            self.combo_tema.setCurrentIndex(max(0, selected))
            self.combo_tema.setMinimumWidth(120)
            encabezado.addWidget(self.combo_tema)

        principal.addLayout(encabezado)

        configuracion = QGroupBox("Configuración")
        self.grupo_configuracion = configuracion
        configuracion.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        formulario = QGridLayout(configuracion)
        formulario.setColumnStretch(1, 1)
        formulario.setColumnStretch(3, 1)
        formulario.setColumnMinimumWidth(0, 135)
        formulario.setColumnMinimumWidth(2, 145)
        formulario.setHorizontalSpacing(10)
        formulario.setVerticalSpacing(7)

        self.combo_division = QComboBox()
        self.combo_division.addItems(divisiones_disponibles())
        self.combo_sector = QComboBox()
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Filtrar por nombre o código...")
        self.fecha_mantenimiento = QDateEdit()
        self.fecha_mantenimiento.setCalendarPopup(True)
        self.fecha_mantenimiento.setDisplayFormat("dd-MM-yyyy")
        self.fecha_mantenimiento.setDate(QDate.currentDate())
        self.fecha_mantenimiento.setMaximumDate(QDate.currentDate())
        self.fecha_mantenimiento.setToolTip(
            "Fecha real en que se realizó el mantenimiento."
        )
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

        filas_izquierda = (
            ("División", self.combo_division),
            ("Sector", self.combo_sector),
            ("Buscar cámara", self.busqueda),
            ("Participantes", self.participantes),
            ("APR participa", self.apr),
            ("Equipo alza hombre", self.alza),
        )
        for fila, (texto, control) in enumerate(filas_izquierda):
            formulario.addWidget(QLabel(texto), fila, 0)
            formulario.addWidget(control, fila, 1)

        filas_derecha = (
            ("Fecha de mantenimiento", self.fecha_mantenimiento),
            ("Hora inicial", self.hora_inicio),
            ("Duración por cámara", self.duracion),
            ("Observaciones", self.observacion),
        )
        for fila, (texto, control) in enumerate(filas_derecha):
            formulario.addWidget(QLabel(texto), fila, 2)
            formulario.addWidget(control, fila, 3)

        formulario.addWidget(QLabel("ART anverso"), 4, 2)
        formulario.addLayout(fila_art_anverso, 4, 3)
        formulario.addWidget(QLabel("ART reverso"), 5, 2)
        formulario.addLayout(fila_art_reverso, 5, 3)
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
        divisor.setChildrenCollapsible(False)
        divisor.setSizes([520, 660])
        divisor.setMinimumHeight(125)

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

        panel_fotos = QWidget()
        layout_fotos = QVBoxLayout(panel_fotos)

        fila_carpeta = QHBoxLayout()
        self.carpeta_fotos = QLineEdit()
        self.carpeta_fotos.setReadOnly(True)
        self.carpeta_fotos.setPlaceholderText(
            "Selecciona la carpeta transferida desde CCTVFlow Camera..."
        )
        self.boton_importar_fotos = QPushButton(
            "Importar carpeta de fotografías"
        )
        fila_carpeta.addWidget(self.carpeta_fotos, 1)
        fila_carpeta.addWidget(self.boton_importar_fotos)

        self.resumen_fotos = QLabel(
            "Sin lote importado: se utilizará el flujo manual."
        )
        self.tabla_art = QTableWidget(0, 5)
        self.tabla_art.setHorizontalHeaderLabels(
            [
                "Área detectada",
                "Cámaras",
                "Evidencias",
                "ART anverso",
                "ART reverso",
            ]
        )
        self.tabla_art.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tabla_art.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        for columna in range(1, 5):
            self.tabla_art.horizontalHeader().setSectionResizeMode(
                columna,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        self.no_detectadas = QTextEdit()
        self.no_detectadas.setReadOnly(True)
        self.no_detectadas.setMaximumHeight(90)
        self.no_detectadas.setPlaceholderText(
            "Aquí aparecerán las imágenes cuyos nombres no correspondan "
            "al catálogo seleccionado."
        )

        self.eliminar_fotos = QCheckBox(
            "Eliminar evidencias y ART después de confirmar su uso"
        )
        self.eliminar_fotos.setChecked(True)
        nota_eliminacion = QLabel(
            "Las evidencias se eliminan cámara por cámara solo después de "
            "guardar en el portal y descargar el PDF. Las ART se eliminan al "
            "completar correctamente todas las cámaras detectadas. Los "
            "archivos fallidos, pendientes o no detectados se conservan."
        )
        nota_eliminacion.setWordWrap(True)

        layout_fotos.addLayout(fila_carpeta)
        layout_fotos.addWidget(self.resumen_fotos)
        layout_fotos.addWidget(self.tabla_art)
        layout_fotos.addWidget(QLabel("Fotografías no detectadas"))
        layout_fotos.addWidget(self.no_detectadas)
        layout_fotos.addWidget(self.eliminar_fotos)
        layout_fotos.addWidget(nota_eliminacion)
        self.pestanas.addTab(panel_fotos, "Fotografías")

        self.pestanas.setMinimumHeight(170)

        divisor_vertical = QSplitter(Qt.Orientation.Vertical)
        self.divisor_vertical = divisor_vertical
        divisor_vertical.setChildrenCollapsible(False)
        divisor_vertical.addWidget(divisor)
        divisor_vertical.addWidget(self.pestanas)
        divisor_vertical.setStretchFactor(0, 1)
        divisor_vertical.setStretchFactor(1, 2)
        divisor_vertical.setSizes([190, 250])
        principal.addWidget(divisor_vertical, 1)

        acciones = QHBoxLayout()
        self.boton_actualizar = QPushButton("Actualizar plan")
        self.boton_ejecutar = QPushButton("Ejecutar mantenimientos")
        self.boton_reanudar = QPushButton("Reanudar pendientes")
        self.boton_reanudar.setEnabled(False)
        self.boton_confirmar = QPushButton(
            "Continuar ejecución"
        )
        self.boton_confirmar.setEnabled(False)
        self.boton_detener = QPushButton("Detener")
        self.boton_detener.setEnabled(False)
        acciones.addWidget(self.boton_actualizar)
        acciones.addStretch()
        acciones.addWidget(self.boton_confirmar)
        acciones.addWidget(self.boton_detener)
        acciones.addWidget(self.boton_reanudar)
        acciones.addWidget(self.boton_ejecutar)
        principal.addLayout(acciones)

        self.setCentralWidget(central)

        self.atajo_enter = QShortcut(
            QKeySequence(Qt.Key.Key_Return),
            self,
        )
        self.atajo_enter.setContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        self.atajo_enter_teclado_numerico = QShortcut(
            QKeySequence(Qt.Key.Key_Enter),
            self,
        )
        self.atajo_enter_teclado_numerico.setContext(
            Qt.ShortcutContext.ApplicationShortcut
        )

    def _conectar_eventos(self) -> None:
        if self.theme_controller is not None:
            self.combo_tema.currentIndexChanged.connect(
                self._cambiar_tema
            )
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
        self.boton_reanudar.clicked.connect(self._reanudar_ejecucion)
        self.boton_confirmar.clicked.connect(
            self._confirmar_paso_manual
        )
        self.atajo_enter.activated.connect(
            self._confirmar_paso_manual
        )
        self.atajo_enter_teclado_numerico.activated.connect(
            self._confirmar_paso_manual
        )
        self.boton_detener.clicked.connect(self._detener)
        self.boton_art_anverso.clicked.connect(
            lambda: self._elegir_foto_art(self.art_anverso)
        )
        self.boton_art_reverso.clicked.connect(
            lambda: self._elegir_foto_art(self.art_reverso)
        )
        self.boton_importar_fotos.clicked.connect(
            self._importar_carpeta_fotos
        )

    @Slot()
    def _cambiar_tema(self) -> None:
        if self.theme_controller is not None:
            self.theme_controller.set_mode(
                str(self.combo_tema.currentData())
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

    @Slot()
    def _importar_carpeta_fotos(self) -> None:
        directorio_inicial = (
            self.carpeta_fotos.text().strip() or str(Path.home())
        )
        carpeta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de fotografías",
            directorio_inicial,
        )

        if not carpeta:
            return

        try:
            lote = analizar_carpeta(carpeta, self.catalogo)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Importar fotografías",
                str(error),
            )
            return

        if not lote.fotos_por_camara:
            QMessageBox.warning(
                self,
                "Sin coincidencias",
                "No se detectó ninguna cámara de la división "
                f"{self.combo_division.currentText()}.\n\n"
                "Revisa la división seleccionada y los nombres de archivo.",
            )

        self.lote_fotos = lote
        self.carpeta_fotos.setText(str(lote.carpeta))
        self.seleccionadas = set(lote.fotos_por_camara)
        self.arts_por_sector.clear()
        self._poblar_tabla_art()
        self._mostrar_resumen_lote()
        self._refrescar_lista()
        self._actualizar_plan()
        self.pestanas.setCurrentIndex(1)

    def _poblar_tabla_art(self) -> None:
        if self.lote_fotos is None:
            self.tabla_art.setRowCount(0)
            return

        anteriores = self.arts_por_sector
        self.arts_por_sector = {
            sector: anteriores.get(sector, ["", ""]).copy()
            for sector in self.lote_fotos.sectores
        }
        self.tabla_art.setRowCount(len(self.lote_fotos.sectores))

        for fila, sector in enumerate(self.lote_fotos.sectores):
            camaras = [
                camara
                for camara, area in (
                    self.lote_fotos.sector_por_camara.items()
                )
                if area == sector
            ]
            cantidad_fotos = sum(
                len(self.lote_fotos.fotos_por_camara[camara])
                for camara in camaras
            )

            self.tabla_art.setItem(
                fila,
                0,
                QTableWidgetItem(sector),
            )
            self.tabla_art.setItem(
                fila,
                1,
                QTableWidgetItem(str(len(camaras))),
            )
            self.tabla_art.setItem(
                fila,
                2,
                QTableWidgetItem(str(cantidad_fotos)),
            )

            for cara, columna in enumerate((3, 4)):
                boton = QPushButton()
                self._actualizar_texto_boton_art(
                    boton,
                    self.arts_por_sector[sector][cara],
                )
                boton.clicked.connect(
                    lambda _marcado=False,
                    area=sector,
                    indice=cara,
                    control=boton: self._elegir_art_sector(
                        area,
                        indice,
                        control,
                    )
                )
                self.tabla_art.setCellWidget(fila, columna, boton)

        self.tabla_art.resizeRowsToContents()

    def _actualizar_texto_boton_art(
        self,
        boton: QPushButton,
        ruta: str,
    ) -> None:
        if ruta:
            boton.setText(Path(ruta).name)
            boton.setToolTip(ruta)
        else:
            boton.setText("Seleccionar…")
            boton.setToolTip("")

    def _elegir_art_sector(
        self,
        sector: str,
        cara: int,
        boton: QPushButton,
    ) -> None:
        ruta_actual = self.arts_por_sector[sector][cara]
        directorio = (
            str(Path(ruta_actual).parent)
            if ruta_actual
            else (
                self.carpeta_fotos.text().strip()
                or str(Path.home())
            )
        )
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            f"Seleccionar ART para {sector}",
            directorio,
            FILTRO_IMAGENES,
        )

        if ruta:
            self.arts_por_sector[sector][cara] = ruta
            self._actualizar_texto_boton_art(boton, ruta)

    def _mostrar_resumen_lote(self) -> None:
        if self.lote_fotos is None:
            self.resumen_fotos.setText(
                "Sin lote importado: se utilizará el flujo manual."
            )
            self.no_detectadas.clear()
            return

        self.resumen_fotos.setText(
            f"{self.lote_fotos.cantidad_fotos} evidencias detectadas · "
            f"{len(self.lote_fotos.fotos_por_camara)} cámaras · "
            f"{len(self.lote_fotos.sectores)} áreas · "
            f"{len(self.lote_fotos.no_detectadas)} no detectadas"
        )
        self.no_detectadas.setPlainText(
            "\n".join(
                f"{item.ruta.name}: {item.motivo}"
                for item in self.lote_fotos.no_detectadas
            )
        )

    def _fotos_art_por_sector(
        self,
        sectores: set[str],
    ) -> dict[str, list[str]]:
        resultado: dict[str, list[str]] = {}

        for sector in sectores:
            fotos = self.arts_por_sector.get(sector, ["", ""])

            if len(fotos) != 2 or not all(fotos):
                raise ValueError(
                    f"Falta seleccionar el anverso o reverso del ART de "
                    f"{sector}."
                )

            for foto in fotos:
                ruta = Path(foto)

                if not ruta.is_file():
                    raise FileNotFoundError(
                        f"No se encontró la fotografía ART: {ruta}"
                    )

                if ruta.suffix.casefold() not in EXTENSIONES_IMAGEN:
                    raise ValueError(
                        f"Formato de imagen no permitido: {ruta.name}"
                    )

            resultado[sector] = fotos.copy()

        return resultado

    def _observacion(self) -> str:
        return self.observacion.currentText().strip() or OBSERVACION_DEFAULT

    def _fecha_mantenimiento(self) -> str:
        return self.fecha_mantenimiento.date().toString(Qt.DateFormat.ISODate)

    @Slot()
    def _cambiar_division(self) -> None:
        if self.lote_fotos is not None:
            self._limpiar_lote()

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

    def _limpiar_lote(self) -> None:
        self.lote_fotos = None
        self.arts_por_sector.clear()
        self.carpeta_fotos.clear()
        self.tabla_art.setRowCount(0)
        self.no_detectadas.clear()
        self._mostrar_resumen_lote()

    def _actualizar_boton_reanudar(self) -> None:
        try:
            datos = cargar_checkpoint()
        except RuntimeError as error:
            self.boton_reanudar.setEnabled(False)
            self.boton_reanudar.setToolTip(str(error))
            return

        if datos is None:
            self.boton_reanudar.setText("Reanudar pendientes")
            self.boton_reanudar.setEnabled(False)
            self.boton_reanudar.setToolTip(
                "No existe una ejecución pendiente."
            )
            return

        resumen = resumen_checkpoint(datos)
        pendientes = resumen.get("pendiente", 0)
        revision = sum(
            resumen.get(estado, 0)
            for estado in (
                ESTADO_EN_PROCESO,
                ESTADO_INCOMPLETO,
                ESTADO_ERROR,
            )
        )
        self.boton_reanudar.setText(
            f"Reanudar pendientes ({pendientes})"
        )
        self.boton_reanudar.setEnabled(pendientes > 0)
        self.boton_reanudar.setToolTip(
            f"{pendientes} cámara(s) no iniciadas y "
            f"{revision} que requieren revisión."
        )

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

        fotos_art: list[str] = []
        fotos_por_camara: dict[str, list[str]] = {}
        fotos_art_por_sector: dict[str, list[str]] = {}
        modo_automatico = self.lote_fotos is not None
        self.lote_completo_en_ejecucion = False

        try:
            if modo_automatico:
                assert self.lote_fotos is not None
                camaras = [item.camara for item in self.plan_actual]
                problemas = validar_lote(self.lote_fotos, camaras)

                if problemas:
                    detalle = "\n".join(f"• {error}" for error in problemas)
                    raise ValueError(
                        "El lote no puede ejecutarse automáticamente:\n"
                        f"{detalle}"
                    )

                sectores = {item.sector for item in self.plan_actual}
                fotos_art_por_sector = self._fotos_art_por_sector(
                    sectores
                )
                fotos_por_camara = {
                    camara: [
                        str(ruta)
                        for ruta in self.lote_fotos.fotos_por_camara[camara]
                    ]
                    for camara in camaras
                }
                self.lote_completo_en_ejecucion = (
                    set(camaras)
                    == set(self.lote_fotos.fotos_por_camara)
                )
            else:
                fotos_art = self._fotos_art()
        except Exception as error:
            QMessageBox.critical(self, "Fotografías", str(error))
            return

        if modo_automatico:
            cantidad_evidencias = sum(
                len(fotos) for fotos in fotos_por_camara.values()
            )
            limpieza = (
                "\n\nAl confirmar cada mantención se eliminarán sus "
                "evidencias. "
                + (
                    "Las ART se eliminarán al completar todo el lote."
                    if self.lote_completo_en_ejecucion
                    else (
                        "Las ART se conservarán porque quedaron cámaras "
                        "detectadas fuera del plan."
                    )
                )
                if self.eliminar_fotos.isChecked()
                else "\n\nLas fotografías originales se conservarán."
            )
            descripcion = (
                f"Se procesarán automáticamente "
                f"{len(self.plan_actual)} mantenciones con "
                f"{cantidad_evidencias} evidencias en "
                f"{len(fotos_art_por_sector)} áreas."
                f"{limpieza}"
            )
        else:
            descripcion = (
                f"Se procesarán {len(self.plan_actual)} mantenciones. "
                "La fotografía de cada cámara se cargará manualmente."
            )

        confirmacion = QMessageBox.question(
            self,
            "Iniciar ejecución",
            f"{descripcion}\n\n"
            f"División: {self.combo_division.currentText()}.\n"
            "Fecha de mantenimiento: "
            f"{self.fecha_mantenimiento.date().toString('dd-MM-yyyy')}.\n\n"
            "¿Deseas abrir el portal de mantenimiento y continuar?",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        checkpoint_path: str | None = None

        if modo_automatico:
            checkpoint_path = str(
                crear_checkpoint(
                    division=self.combo_division.currentText(),
                    fecha_mantenimiento=self._fecha_mantenimiento(),
                    plan=self.plan_actual.copy(),
                    participantes=self._participantes(),
                    apr_participa=self.apr.isChecked(),
                    equipo_alza_hombre=self.alza.isChecked(),
                    observacion=self._observacion(),
                    fotos_por_camara=fotos_por_camara,
                    fotos_art_por_sector=fotos_art_por_sector,
                    eliminar_fotos_tras_exito=(
                        self.eliminar_fotos.isChecked()
                    ),
                    eliminar_art_tras_exito=(
                        self.eliminar_fotos.isChecked()
                        and self.lote_completo_en_ejecucion
                    ),
                )
            )
            self.checkpoint_activo = checkpoint_path
            self._actualizar_boton_reanudar()

        self._lanzar_ejecutor(
            division=self.combo_division.currentText(),
            fecha_mantenimiento=self._fecha_mantenimiento(),
            plan=self.plan_actual.copy(),
            participantes=self._participantes(),
            apr_participa=self.apr.isChecked(),
            equipo_alza_hombre=self.alza.isChecked(),
            fotos_art=fotos_art,
            observacion=self._observacion(),
            fotos_por_camara=fotos_por_camara,
            fotos_art_por_sector=fotos_art_por_sector,
            eliminar_fotos_tras_exito=(
                modo_automatico and self.eliminar_fotos.isChecked()
            ),
            eliminar_art_tras_exito=(
                modo_automatico
                and self.eliminar_fotos.isChecked()
                and self.lote_completo_en_ejecucion
            ),
            checkpoint_path=checkpoint_path,
        )

    def _lanzar_ejecutor(
        self,
        *,
        division: str,
        fecha_mantenimiento: str,
        plan: list[MantenimientoPlanificado],
        participantes: list[str],
        apr_participa: bool,
        equipo_alza_hombre: bool,
        fotos_art: list[str],
        observacion: str,
        fotos_por_camara: dict[str, list[str]],
        fotos_art_por_sector: dict[str, list[str]],
        eliminar_fotos_tras_exito: bool,
        eliminar_art_tras_exito: bool,
        checkpoint_path: str | None,
    ) -> None:
        self.hilo = QThread(self)
        self.limpieza_lote_completa = False
        self.resumen_ejecucion = {}
        self.ejecutor = EjecutorMantenimientos(
            division=division,
            fecha_mantenimiento=fecha_mantenimiento,
            plan=plan,
            participantes=participantes,
            apr_participa=apr_participa,
            equipo_alza_hombre=equipo_alza_hombre,
            fotos_art=fotos_art,
            observacion=observacion,
            fotos_por_camara=fotos_por_camara,
            fotos_art_por_sector=fotos_art_por_sector,
            eliminar_fotos_tras_exito=eliminar_fotos_tras_exito,
            eliminar_art_tras_exito=eliminar_art_tras_exito,
            checkpoint_path=checkpoint_path,
            server_client=self.server_client,
            allow_server_autoconfigure=self.server_autoconfigure,
        )
        self.ejecutor.moveToThread(self.hilo)
        self.hilo.started.connect(self.ejecutor.ejecutar)
        self.ejecutor.mensaje.connect(self._registrar)
        self.ejecutor.progreso.connect(self._mostrar_progreso)
        self.ejecutor.espera_manual.connect(
            self._esperar_confirmacion_manual
        )
        self.ejecutor.resultado_limpieza.connect(
            self._registrar_resultado_limpieza
        )
        self.ejecutor.resumen.connect(self._registrar_resumen)
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
        self.progreso.setRange(0, len(plan))
        self._bloquear_configuracion(True)
        self.estado.setText("Abriendo Chromium e iniciando sesión...")
        self.hilo.start()

    @Slot()
    def _reanudar_ejecucion(self) -> None:
        try:
            datos = cargar_checkpoint()

            if datos is None:
                raise RuntimeError(
                    "No existe una ejecución pendiente para reanudar."
                )

            plan = plan_pendiente(datos)

            if not plan:
                raise RuntimeError(
                    "El último lote no tiene cámaras pendientes sin iniciar."
                )

            fotos_por_camara = {
                item.camara: list(
                    datos["fotos_por_camara"][item.camara]
                )
                for item in plan
            }
            sectores = {item.sector for item in plan}
            fotos_art_por_sector = {
                sector: list(datos["fotos_art_por_sector"][sector])
                for sector in sectores
            }

            rutas = [
                Path(ruta)
                for fotos in fotos_por_camara.values()
                for ruta in fotos
            ] + [
                Path(ruta)
                for fotos in fotos_art_por_sector.values()
                for ruta in fotos
            ]
            faltantes = [ruta for ruta in rutas if not ruta.is_file()]

            if faltantes:
                nombres = "\n".join(
                    f"• {ruta}" for ruta in faltantes[:10]
                )
                raise FileNotFoundError(
                    "Faltan archivos necesarios para reanudar:\n"
                    f"{nombres}"
                )
        except Exception as error:
            QMessageBox.critical(self, "Reanudar ejecución", str(error))
            self._actualizar_boton_reanudar()
            return

        resumen = resumen_checkpoint(datos)
        revision = sum(
            resumen.get(estado, 0)
            for estado in (
                ESTADO_EN_PROCESO,
                ESTADO_INCOMPLETO,
                ESTADO_ERROR,
            )
        )
        aviso_revision = (
            f"\n\n{revision} cámara(s) ya alcanzaron el portal y requieren "
            "revisión manual; no se repetirán para evitar duplicados."
            if revision
            else ""
        )
        confirmacion = QMessageBox.question(
            self,
            "Reanudar ejecución",
            f"Se ejecutarán únicamente {len(plan)} cámara(s) que nunca "
            "alcanzaron a iniciarse. Las completadas se omitirán."
            f"{aviso_revision}\n\n"
            "Fecha de mantenimiento conservada: "
            f"{datos['configuracion']['fecha_mantenimiento']}.\n\n"
            "¿Deseas continuar?",
        )

        if confirmacion != QMessageBox.StandardButton.Yes:
            return

        configuracion = datos["configuracion"]
        division = datos["division"]
        self.combo_division.setCurrentText(division)
        self.participantes.setText(
            ", ".join(configuracion["participantes"])
        )
        self.apr.setChecked(configuracion["apr_participa"])
        self.alza.setChecked(configuracion["equipo_alza_hombre"])
        self.observacion.setCurrentText(configuracion["observacion"])
        fecha_mantenimiento = QDate.fromString(
            configuracion["fecha_mantenimiento"],
            Qt.DateFormat.ISODate,
        )
        self.fecha_mantenimiento.setDate(fecha_mantenimiento)
        self.checkpoint_activo = str(CHECKPOINT_PATH)
        self.lote_completo_en_ejecucion = False
        self._lanzar_ejecutor(
            division=division,
            fecha_mantenimiento=configuracion["fecha_mantenimiento"],
            plan=plan,
            participantes=list(configuracion["participantes"]),
            apr_participa=configuracion["apr_participa"],
            equipo_alza_hombre=(
                configuracion["equipo_alza_hombre"]
            ),
            fotos_art=[],
            observacion=configuracion["observacion"],
            fotos_por_camara=fotos_por_camara,
            fotos_art_por_sector=fotos_art_por_sector,
            eliminar_fotos_tras_exito=(
                configuracion["eliminar_fotos_tras_exito"]
            ),
            # Nunca se eliminan ART si el lote contiene resultados
            # incompletos o de estado incierto.
            eliminar_art_tras_exito=(
                configuracion["eliminar_art_tras_exito"]
                and revision == 0
            ),
            checkpoint_path=str(CHECKPOINT_PATH),
        )

    def _bloquear_configuracion(self, ejecutando: bool) -> None:
        for control in (
            self.combo_division,
            self.combo_sector,
            self.busqueda,
            self.lista_camaras,
            self.fecha_mantenimiento,
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
            self.carpeta_fotos,
            self.boton_importar_fotos,
            self.tabla_art,
            self.eliminar_fotos,
            self.boton_todas,
            self.boton_limpiar,
            self.boton_actualizar,
            self.boton_reanudar,
            self.boton_ejecutar,
        ):
            control.setEnabled(not ejecutando)

        self.boton_detener.setEnabled(ejecutando)

    @Slot(str)
    def _registrar(self, texto: str) -> None:
        self.registro.append(texto)
        barra = self.registro.verticalScrollBar()
        barra.setValue(barra.maximum())

    @Slot(bool)
    def _registrar_resultado_limpieza(self, completa: bool) -> None:
        self.limpieza_lote_completa = completa

    @Slot(object)
    def _registrar_resumen(self, resumen: dict[str, int]) -> None:
        self.resumen_ejecucion = dict(resumen)

    @Slot(int, int, str)
    def _mostrar_progreso(self, actual: int, total: int, camara: str) -> None:
        self.progreso.setRange(0, total)
        self.progreso.setValue(actual - 1)
        self.estado.setText(f"Preparando {actual}/{total}: {camara}")
        self._registrar(f"\n▶ {actual}/{total} · {camara}")

    @Slot(str, str)
    def _esperar_confirmacion_manual(
        self,
        mensaje: str,
        texto_boton: str,
    ) -> None:
        self.estado.setText(mensaje)
        self.boton_confirmar.setText(texto_boton)
        self.boton_confirmar.setEnabled(True)
        QApplication.alert(self, 0)
        self._registrar(
            "\n⏸ Acción manual pendiente: "
            f"{mensaje}\n"
            "Cuando termines, vuelve a CCTVFlow y presiona Enter o "
            f"«{texto_boton}»."
        )

    @Slot()
    def _confirmar_paso_manual(self) -> None:
        if (
            self.ejecutor is None
            or not self.boton_confirmar.isEnabled()
        ):
            return

        self.boton_confirmar.setEnabled(False)
        self.estado.setText("Continuando la ejecución...")
        self.ejecutor.confirmar_paso_manual()

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
        lote_con_limpieza = (
            self.lote_fotos is not None
            and self.eliminar_fotos.isChecked()
        )
        lote_completo = self.lote_completo_en_ejecucion
        carpeta_lote = (
            self.lote_fotos.carpeta
            if self.lote_fotos is not None
            else None
        )
        self.progreso.setValue(self.progreso.maximum())
        incompletas = self.resumen_ejecucion.get(
            ESTADO_INCOMPLETO,
            0,
        )
        revision = sum(
            self.resumen_ejecucion.get(estado, 0)
            for estado in (ESTADO_EN_PROCESO, ESTADO_ERROR)
        )
        pendientes = self.resumen_ejecucion.get("pendiente", 0)

        if incompletas or revision or pendientes:
            self.estado.setText(
                "Lote terminado con mantenciones que requieren revisión."
            )
            self._registrar(
                "\n⚠ Ejecución terminada con incidencias: "
                f"{incompletas} PDF incompleto(s), "
                f"{revision} estado(s) incierto(s) y "
                f"{pendientes} pendiente(s)."
            )
        else:
            self.estado.setText("Plan completado correctamente.")
            self._registrar("\n✓ Ejecución finalizada.")

        self._bloquear_configuracion(False)
        self._actualizar_boton_reanudar()
        self.boton_confirmar.setEnabled(False)

        if (
            lote_con_limpieza
            and lote_completo
            and self.limpieza_lote_completa
        ):
            self._limpiar_lote()
            self.seleccionadas.clear()
            self._refrescar_lista()
            self._actualizar_plan()
        elif lote_con_limpieza and carpeta_lote is not None:
            try:
                self.lote_fotos = analizar_carpeta(
                    carpeta_lote,
                    self.catalogo,
                )
                self.seleccionadas = set(
                    self.lote_fotos.fotos_por_camara
                )
                self._poblar_tabla_art()
                self._mostrar_resumen_lote()
                self._refrescar_lista()
                self._actualizar_plan()
            except Exception as error:
                self._registrar(
                    f"No se pudo actualizar el lote pendiente: {error}"
                )

    @Slot()
    def _ejecucion_detenida(self) -> None:
        self.estado.setText("Ejecución detenida.")
        self._registrar("\n■ Ejecución detenida por el usuario.")
        self._bloquear_configuracion(False)
        self._actualizar_boton_reanudar()
        self.boton_confirmar.setEnabled(False)

    @Slot(str)
    def _ejecucion_error(self, detalle: str) -> None:
        self.estado.setText("La ejecución terminó con un error.")
        self._registrar(f"\nERROR:\n{detalle}")
        self._bloquear_configuracion(False)
        self._actualizar_boton_reanudar()
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

        if self._cerrar_al_finalizar:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, evento: QCloseEvent) -> None:
        if self.hilo is not None and self.hilo.isRunning():
            respuesta = QMessageBox.question(
                self,
                "Ejecución activa",
                "CCTVFlow todavía está ejecutando una mantención.\n\n"
                "¿Deseas detenerla y cerrar la aplicación?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if respuesta == QMessageBox.StandardButton.Yes:
                self._cerrar_al_finalizar = True
                self.estado.setText(
                    "Deteniendo la ejecución para cerrar CCTVFlow..."
                )
                self.boton_confirmar.setEnabled(False)
                self.boton_detener.setEnabled(False)

                if self.ejecutor is not None:
                    self.ejecutor.solicitar_detencion()

            evento.ignore()
            return

        evento.accept()
