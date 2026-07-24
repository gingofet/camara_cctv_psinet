"""Automatización de tareas y mantenciones preventivas en PSINet.

Este módulo concentra únicamente las acciones relacionadas con el flujo de
Tareas / Actividades de PSINet. La navegación del navegador, el inicio de
sesión y la futura descarga de informes PDF deben permanecer en módulos
separados para mantener una arquitectura clara y mantenible.
"""

from __future__ import annotations

from collections.abc import Sequence
import re
from pathlib import Path
from typing import Any

from automatizacion.data.config import (
    ALZA_HOMBRE,
    APR_PARTICIPA,
    CAUSA_DEFAULT,
    MAXIMO_FOTOS,
    OBSERVACION_DEFAULT,
    PARTICIPANTES_DEFAULT,
    RESPONSABLE_DEFAULT,
    TIPO_ACTIVIDAD_DEFAULT,
    TIPO_TAREA_DEFAULT,
    UBICACION_DEFAULT,
)
from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


# ---------------------------------------------------------------------------
# Configuración general del flujo
# ---------------------------------------------------------------------------

OBSERVACION_TAREA_DEFAULT = OBSERVACION_DEFAULT
OBSERVACION_ACTIVIDAD_DEFAULT = OBSERVACION_DEFAULT
OBSERVACION_GENERAL_DEFAULT = OBSERVACION_DEFAULT

TIMEOUT_CORTO_MS = 800
TIMEOUT_NORMAL_MS = 10_000


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _patron_texto_exacto(texto: str) -> re.Pattern[str]:
    """Crea un patrón que acepta espacios externos y omite mayúsculas."""

    return re.compile(rf"^\s*{re.escape(texto)}\s*$", re.IGNORECASE)


def _escapar_valor_atributo_css(valor: str) -> str:
    """Escapa un valor antes de insertarlo en un selector CSS de atributo."""

    return valor.replace("\\", "\\\\").replace('"', '\\"')


def _buscar_input_asociado(page: Page, control: Locator) -> Locator | None:
    """Busca el checkbox o radio asociado a una etiqueta visible.

    PSINet utiliza controles Bootstrap personalizados: el ``input`` real suele
    estar oculto y el usuario interactúa con un ``label``. Esta función intenta
    localizar ese input mediante el atributo ``for`` y, como respaldo, mediante
    la estructura HTML cercana.
    """

    try:
        identificador = control.get_attribute("for")
    except Exception:
        identificador = None

    if identificador:
        identificador_escapado = _escapar_valor_atributo_css(identificador)
        candidato = page.locator(f'[id="{identificador_escapado}"]').first

        if candidato.count() > 0:
            return candidato

    # Estructura frecuente: <input ...><label ...>Nombre</label>
    candidato = control.locator(
        "xpath=preceding-sibling::input["
        "@type='checkbox' or @type='radio'"
        "][1]"
    ).first

    if candidato.count() > 0:
        return candidato

    # Respaldo para controles envueltos por un contenedor Bootstrap.
    candidato = control.locator(
        "xpath=ancestor::*["
        "contains(concat(' ', normalize-space(@class), ' '), ' custom-control ')"
        "][1]//input[@type='checkbox' or @type='radio'][1]"
    ).first

    if candidato.count() > 0:
        return candidato

    # Último respaldo: buscar un input dentro del padre inmediato.
    candidato = control.locator(
        "xpath=parent::*//input[@type='checkbox' or @type='radio'][1]"
    ).first

    if candidato.count() > 0:
        return candidato

    return None


def _activar_control_etiquetado(
    page: Page,
    control: Locator,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> bool:
    """Activa un checkbox/radio personalizado y confirma su estado.

    Retorna ``True`` cuando el control quedó seleccionado. Si no existe un
    input verificable, considera exitoso el clic sobre el elemento visible.
    """

    control.wait_for(state="visible", timeout=timeout)
    control.scroll_into_view_if_needed()

    input_asociado = _buscar_input_asociado(page, control)

    if input_asociado is not None:
        try:
            if input_asociado.is_checked():
                return True
        except Exception:
            # Algunos componentes todavía no están listos para consultar su
            # estado; se intentará el clic igualmente.
            pass

    # Primer intento: interacción normal con la etiqueta visible.
    try:
        control.click()
    except Exception:
        # Algunos labels quedan parcialmente cubiertos por componentes de la
        # interfaz. En ese caso Playwright puede forzar el clic.
        control.click(force=True)

    page.wait_for_timeout(250)

    if input_asociado is None:
        return True

    try:
        if input_asociado.is_checked():
            return True
    except Exception:
        pass

    # Segundo intento: marcar directamente el input oculto.
    try:
        input_asociado.check(force=True)
        page.wait_for_timeout(200)
        return input_asociado.is_checked()
    except Exception:
        return False


def _normalizar_participantes(
    valor: Any,
    responsable: str = RESPONSABLE_DEFAULT,
) -> list[str]:
    """Convierte la configuración de participantes en una lista limpia."""

    if valor is None:
        return [responsable]

    if isinstance(valor, str):
        participantes = [valor]
    elif isinstance(valor, Sequence):
        participantes = [str(nombre) for nombre in valor]
    else:
        raise TypeError(
            "'participantes' debe ser un nombre o una lista de nombres."
        )

    # Elimina nombres vacíos y duplicados conservando el orden original.
    resultado: list[str] = []
    vistos: set[str] = set()

    for nombre in participantes:
        nombre_limpio = nombre.strip()
        clave = nombre_limpio.casefold()

        if nombre_limpio and clave not in vistos:
            resultado.append(nombre_limpio)
            vistos.add(clave)

    return resultado


def _convertir_a_bool(valor: Any, nombre_campo: str) -> bool:
    """Acepta booleanos y textos como ``Sí``/``No`` provenientes de JSON."""

    if isinstance(valor, bool):
        return valor

    if isinstance(valor, int) and valor in {0, 1}:
        return bool(valor)

    if isinstance(valor, str):
        valor_normalizado = valor.strip().casefold()

        if valor_normalizado in {"si", "sí", "true", "1"}:
            return True

        if valor_normalizado in {"no", "false", "0"}:
            return False

    raise ValueError(
        f"Valor inválido para '{nombre_campo}': {valor!r}. "
        "Usa True/False o Sí/No."
    )


# ---------------------------------------------------------------------------
# Navegación hacia el formulario de tareas
# ---------------------------------------------------------------------------


def ir_a_tareas(page: Page) -> None:
    """Abre el módulo Tareas / Actividades y luego la sección Tareas."""

    page.get_by_role("link", name="Tareas / Actividades").click()
    page.wait_for_load_state("networkidle")

    page.get_by_role("link", name="Tareas", exact=True).click()
    page.wait_for_load_state("networkidle")


def abrir_nueva_tarea(page: Page) -> None:
    """Abre el formulario para crear una nueva tarea."""

    page.get_by_text("Nueva", exact=True).click()
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Creación de la tarea base
# ---------------------------------------------------------------------------


def seleccionar_camara(
    page: Page,
    area_busqueda: str,
    area_psinet: str,
) -> None:
    """Busca y selecciona una cámara en el árbol de PSINet.

    PSINet presenta un error conocido: al escribir el nombre completo puede no
    mostrar resultados. Cuando ocurre, se elimina automáticamente el último
    carácter para forzar la actualización de la lista.
    """

    campo_busqueda = page.get_by_role("textbox").nth(5)

    campo_busqueda.fill(area_busqueda)
    page.wait_for_timeout(TIMEOUT_CORTO_MS)

    opcion = page.get_by_role("treeitem", name=area_psinet, exact=True)

    if opcion.count() == 0 and len(area_busqueda) > 1:
        campo_busqueda.press("Backspace")
        page.wait_for_timeout(TIMEOUT_CORTO_MS)
        opcion = page.get_by_role("treeitem", name=area_psinet, exact=True)

    if opcion.count() > 0:
        opcion.first.click()
        print(f"Cámara seleccionada: {area_psinet}")
        return

    print("\nNo pude seleccionar la cámara automáticamente.")
    print("Selecciona la cámara manualmente en PSINet.")
    input("Cuando la selecciones, presiona Enter aquí para continuar...")


def crear_tarea_base(
    page: Page,
    area_busqueda: str,
    area_psinet: str,
    ubicacion_psinet: str = UBICACION_DEFAULT,
) -> None:
    """Completa y crea la tarea principal de mantenimiento."""

    # Tipo de tarea: Mantención Programada.
    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role(
        "treeitem",
        name=TIPO_TAREA_DEFAULT,
        exact=True,
    ).click()

    # Ubicación/contrato correspondiente a la división elegida.
    page.get_by_label("", exact=True).nth(1).click()
    page.get_by_role(
        "treeitem",
        name=ubicacion_psinet,
        exact=True,
    ).click()

    # Selector de cámara dentro del formulario de nueva tarea.
    page.locator("#forms_add_tarea").get_by_label("", exact=True).click()

    seleccionar_camara(
        page=page,
        area_busqueda=area_busqueda,
        area_psinet=area_psinet,
    )

    page.locator(
        'input[name="text_observacion_tarea"]'
    ).fill(OBSERVACION_TAREA_DEFAULT)

    print("Voy a presionar Ingresar para crear la tarea base...")
    page.get_by_role("button", name="Ingresar", exact=True).click()
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Creación de la actividad y selección de participantes
# ---------------------------------------------------------------------------


def seleccionar_opcion_select2(
    page: Page,
    etiqueta: str,
    opcion: str,
) -> None:
    """Selecciona una opción en un componente Select2 usando su etiqueta."""

    selector = (
        f"xpath=//*[normalize-space()='{etiqueta}']"
        "/following::*["
        "@role='combobox' or contains(@class, 'select2-selection')"
        "][1]"
    )

    page.locator(selector).click()
    page.get_by_role("treeitem", name=opcion, exact=True).click()


def seleccionar_participante(
    page: Page,
    nombre_participante: str,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> bool:
    """Busca un participante por su nombre y activa su interruptor.

    La función localiza específicamente el ``label`` del trabajador, busca el
    input asociado y comprueba que haya quedado marcado. Esto evita seleccionar
    por posición, lo cual era inestable debido a las tres columnas de PSINet.
    """

    nombre_participante = nombre_participante.strip()

    if not nombre_participante:
        raise ValueError("El nombre del participante no puede estar vacío.")

    print(f"Buscando participante: {nombre_participante}")

    patron = _patron_texto_exacto(nombre_participante)
    etiquetas = page.locator("label").filter(has_text=patron)

    # Respaldo por si el texto está dentro de un span alojado en el label.
    if etiquetas.count() == 0:
        texto = page.get_by_text(nombre_participante, exact=True).first

        if texto.count() > 0:
            etiquetas = texto.locator("xpath=ancestor-or-self::label[1]")

    if etiquetas.count() == 0:
        print(f"No se encontró al participante: {nombre_participante}")
        return False

    if etiquetas.count() > 1:
        print(
            f"Advertencia: hay {etiquetas.count()} coincidencias para "
            f"'{nombre_participante}'. Se utilizará la primera."
        )

    etiqueta = etiquetas.first

    try:
        seleccionado = _activar_control_etiquetado(
            page=page,
            control=etiqueta,
            timeout=timeout,
        )
    except PlaywrightTimeoutError:
        print(f"El participante no quedó visible: {nombre_participante}")
        return False
    except Exception as error:
        print(
            f"No se pudo seleccionar a {nombre_participante}. "
            f"Detalle: {error}"
        )
        return False

    if seleccionado:
        print(f"Participante seleccionado: {nombre_participante}")
        return True

    print(f"No fue posible confirmar a: {nombre_participante}")
    return False


def seleccionar_participantes(
    page: Page,
    participantes: Sequence[str],
) -> None:
    """Selecciona todos los participantes configurados.

    Si alguno no puede marcarse automáticamente, el flujo se detiene para que
    el usuario corrija únicamente los participantes pendientes.
    """

    participantes_limpios = _normalizar_participantes(
        participantes,
        responsable=RESPONSABLE_DEFAULT,
    )

    if not participantes_limpios:
        print("\nNo se configuraron participantes para esta actividad.")
        input(
            "Selecciona los participantes manualmente y presiona Enter "
            "para continuar..."
        )
        return

    no_seleccionados: list[str] = []

    for participante in participantes_limpios:
        if not seleccionar_participante(page, participante):
            no_seleccionados.append(participante)

    if no_seleccionados:
        print("\nNo se pudieron seleccionar automáticamente:")

        for participante in no_seleccionados:
            print(f"  - {participante}")

        input(
            "Selecciona manualmente los participantes pendientes y "
            "presiona Enter para continuar..."
        )
        return

    print("Todos los participantes fueron seleccionados correctamente.")


def crear_actividad(
    page: Page,
    hora_inicio: str = "17:00",
    hora_fin: str = "17:10",
    responsable: str = RESPONSABLE_DEFAULT,
    participantes: Sequence[str] | None = None,
) -> None:
    """Crea la actividad asociada a la tarea base."""

    page.locator(".btn.btn-outline-info").first.click()
    page.wait_for_timeout(1_000)

    seleccionar_opcion_select2(
        page,
        "Tipo de Actividad:",
        TIPO_ACTIVIDAD_DEFAULT,
    )
    seleccionar_opcion_select2(page, "Causa:", CAUSA_DEFAULT)

    page.locator("#time_inicio_actividad").fill(hora_inicio)
    page.locator('input[name="time_cierre_actividad"]').fill(hora_fin)

    page.locator(
        'input[name="text_observacion_actividad"]'
    ).fill(OBSERVACION_ACTIVIDAD_DEFAULT)

    participantes_objetivo = (
        list(participantes) if participantes is not None else [responsable]
    )
    seleccionar_participantes(page, participantes_objetivo)

    # PSINet incluye un selector adicional que actualmente aparece con valor
    # "No" y que el flujo original cambia a "Si". Se mantiene esta acción para
    # no alterar el comportamiento ya validado. Cuando conozcamos la etiqueta
    # exacta de ese campo, convendrá reemplazar este selector por uno etiquetado.
    page.get_by_role("textbox", name="No", exact=True).click()
    page.get_by_role("treeitem", name="Si", exact=True).click()

    print("Voy a presionar Ingresar para crear la actividad...")
    page.get_by_role("button", name="Ingresar", exact=True).click()
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Checklist de mantenimiento
# ---------------------------------------------------------------------------


def completar_estado_general(page: Page) -> None:
    """Completa la sección ESTADO GENERAL con los valores ya validados."""

    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()

    # PSINet muestra seis evaluaciones cuyo estado correcto es "B".
    for indice in range(6):
        page.get_by_text("B", exact=True).nth(indice).click()

    # Último control de la sección. Se conserva el selector validado en terreno.
    page.locator(
        "div:nth-child(7) > div > .custom-control-label"
    ).first.click()

    # Cierra el acordeón para continuar con la siguiente sección.
    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()


def completar_conexiones(page: Page) -> None:
    """Completa la sección CONEXIONES con los valores ya validados."""

    enlace_conexiones = page.get_by_role(
        "link",
        name="CONEXIONES",
        exact=True,
    )

    # El ID del acordeón cambia según el checklist cargado por PSINet.
    # Se obtiene desde el propio enlace en vez de fijar "#collapse1543".
    id_panel = enlace_conexiones.get_attribute("aria-controls")

    if not id_panel:
        href_panel = enlace_conexiones.get_attribute("href") or ""
        id_panel = href_panel.removeprefix("#")

    if not id_panel:
        raise RuntimeError(
            "No se pudo identificar el panel de la sección CONEXIONES."
        )

    enlace_conexiones.click()

    panel_conexiones = page.locator(f"#{id_panel}")
    panel_conexiones.wait_for(state="visible")

    opciones_b = panel_conexiones.get_by_text("B", exact=True)
    cantidad_opciones = opciones_b.count()

    if cantidad_opciones != 6:
        raise RuntimeError(
            "Se esperaban 6 opciones 'B' en CONEXIONES, "
            f"pero PSINet mostró {cantidad_opciones}."
        )

    for indice in range(cantidad_opciones):
        opciones_b.nth(indice).click()

    enlace_conexiones.click()


# ---------------------------------------------------------------------------
# Cierre: APR, equipo alza hombre, observaciones y fotografías
# ---------------------------------------------------------------------------


def seleccionar_opcion_bloque(
    page: Page,
    titulo_bloque: str,
    opcion: str,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> None:
    """Selecciona ``Si`` o ``No`` dentro de una tarjeta del formulario.

    El bloque se identifica por su pregunta, por lo que no se confunde el ``No``
    de APR con el ``No`` de equipo alza hombre.
    """

    opcion_normalizada = opcion.strip().casefold()

    if opcion_normalizada in {"si", "sí"}:
        texto_opcion = "Si"
    elif opcion_normalizada == "no":
        texto_opcion = "No"
    else:
        raise ValueError(
            f"Opción inválida: {opcion!r}. Debe ser 'Sí' o 'No'."
        )

    titulo = page.get_by_text(titulo_bloque, exact=True).first

    try:
        titulo.wait_for(state="visible", timeout=timeout)
    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            f"No se encontró el bloque: {titulo_bloque}"
        ) from error

    # Busca el ancestro más cercano que contenga simultáneamente las opciones
    # Si y No. En la interfaz actual corresponde a la tarjeta completa.
    bloque = titulo.locator(
        "xpath=ancestor::*["
        ".//*[normalize-space()='Si'] and "
        ".//*[normalize-space()='No']"
        "][1]"
    ).first

    if bloque.count() == 0:
        raise RuntimeError(
            f"No se pudo identificar la tarjeta de: {titulo_bloque}"
        )

    patron_opcion = _patron_texto_exacto(texto_opcion)
    controles = bloque.locator(
        "label, button, [role='button']"
    ).filter(has_text=patron_opcion)

    if controles.count() == 0:
        # Respaldo para interfaces donde el texto está dentro de un span.
        texto_visible = bloque.get_by_text(texto_opcion, exact=True).first

        if texto_visible.count() > 0:
            controles = texto_visible.locator(
                "xpath=ancestor-or-self::*["
                "self::label or self::button or @role='button'"
                "][1]"
            )

    if controles.count() == 0:
        raise RuntimeError(
            f"No se encontró la opción '{texto_opcion}' dentro de "
            f"'{titulo_bloque}'."
        )

    seleccionado = _activar_control_etiquetado(
        page=page,
        control=controles.first,
        timeout=timeout,
    )

    if not seleccionado:
        raise RuntimeError(
            f"No fue posible confirmar '{texto_opcion}' en "
            f"'{titulo_bloque}'."
        )

    print(f"{titulo_bloque}: {texto_opcion}")


def subir_fotos(
    page: Page,
    fotos: Sequence[str],
    dejar_campo_extra: bool = False,
) -> None:
    """
    Adjunta automáticamente las fotografías recibidas.

    Cuando dejar_campo_extra=True, después de subir las fotografías
    se crea un campo adicional vacío para que el usuario pueda agregar
    manualmente otra imagen.

    En el flujo manual se utiliza para:

        1. ART delantera.
        2. ART trasera.
        3. Fotografía del mantenimiento agregada manualmente.
    """

    if not fotos:
        return

    if len(fotos) > MAXIMO_FOTOS:
        raise ValueError(
            f"Se recibieron {len(fotos)} fotografías, pero PSINet "
            f"permite un máximo de {MAXIMO_FOTOS}."
        )

    for indice, foto in enumerate(fotos, start=1):
        ruta_foto = Path(foto)

        if not ruta_foto.exists():
            raise FileNotFoundError(
                f"No se encontró la fotografía: {ruta_foto}"
            )

        print(
            f"Adjuntando fotografía {indice}/{len(fotos)}: "
            f"{ruta_foto.name}"
        )

        if indice == 1:
            selector_archivo = page.get_by_role(
                "button",
                name="Choose File",
            )
        else:
            selector_archivo = page.locator(
                f"#inputFoto{indice}"
            )

        selector_archivo.set_input_files(str(ruta_foto))

        # Mientras queden fotografías por subir, crea el siguiente campo.
        if indice < len(fotos):
            page.locator(f"#plus{indice}").click()
            page.wait_for_timeout(300)

    # Después de cargar las ART, crea un campo vacío adicional
    # para la fotografía manual del mantenimiento.
    if dejar_campo_extra and len(fotos) < MAXIMO_FOTOS:
        boton_agregar = page.locator(
            f"#plus{len(fotos)}"
        )

        if boton_agregar.count() > 0:
            boton_agregar.click()
            page.wait_for_timeout(300)

            print(
                "Campo adicional preparado para la fotografía "
                "manual del mantenimiento."
            )
        else:
            print(
                "No se encontró el botón para crear un campo "
                "fotográfico adicional."
            )


def completar_cierre(
    page: Page,
    fotos: Sequence[str],
    apr_participa: bool = False,
    equipo_alza_hombre: bool = False,
) -> None:
    """Completa los datos finales antes de guardar la mantención."""

    configuraciones = [
        (
            "APR participa en la actividad?",
            "Si" if apr_participa else "No",
        ),
        (
            "Apoyo de equipo alza hombre?",
            "Si" if equipo_alza_hombre else "No",
        ),
    ]

    errores: list[str] = []

    for pregunta, opcion in configuraciones:
        try:
            seleccionar_opcion_bloque(
                page=page,
                titulo_bloque=pregunta,
                opcion=opcion,
            )
        except Exception as error:
            errores.append(f"{pregunta}: {error}")

    if errores:
        print("\nNo pude completar automáticamente estas opciones:")

        for error in errores:
            print(f"  - {error}")

        input(
            "Selecciona manualmente las opciones pendientes y presiona "
            "Enter para continuar..."
        )

    page.get_by_role(
        "textbox",
        name="Observaciones generales:",
    ).fill(OBSERVACION_DEFAULT)

    if fotos:
        subir_fotos(
            page=page,
            fotos=fotos,
            dejar_campo_extra=True,
        )

    print()
    print("Las fotografías de la ART fueron cargadas automáticamente.")
    print("Agrega manualmente la fotografía del mantenimiento.")
    print("La mantención NO se guardará automáticamente durante esta prueba.")


# ---------------------------------------------------------------------------
# Orquestador principal de una mantención
# ---------------------------------------------------------------------------


def crear_mantenimiento(
    page: Page,
    evidencia: dict[str, Any],
    modo_navegacion: str = "completa",
) -> None:
    """Ejecuta el flujo completo de una mantención preventiva.

    Claves opcionales admitidas dentro de ``evidencia``::

        {
            "participantes": ["Louis Rivera", "Emgelbert Pizarro"],
            "apr_participa": false,
            "equipo_alza_hombre": false
        }

    Cuando una opción no viene en ``evidencia``, se utiliza el valor definido
    en ``automatizacion.data.config``.
    """

    area = evidencia["area"]
    area_busqueda = evidencia.get("area_busqueda", area)
    fotos = evidencia.get("fotos", [])
    hora_inicio = evidencia.get("hora_inicio", "17:00")
    hora_fin = evidencia.get("hora_fin", "17:10")
    ubicacion_psinet = str(
        evidencia.get("ubicacion_psinet", UBICACION_DEFAULT)
    ).strip()
    responsable = str(
        evidencia.get("responsable", RESPONSABLE_DEFAULT)
    ).strip()

    participantes = _normalizar_participantes(
        evidencia.get("participantes", PARTICIPANTES_DEFAULT),
        responsable=responsable,
    )
    apr_participa = _convertir_a_bool(
        evidencia.get("apr_participa", APR_PARTICIPA),
        "apr_participa",
    )
    equipo_alza_hombre = _convertir_a_bool(
        evidencia.get("equipo_alza_hombre", ALZA_HOMBRE),
        "equipo_alza_hombre",
    )

    if modo_navegacion == "completa":
        ir_a_tareas(page)
        abrir_nueva_tarea(page)
    elif modo_navegacion == "solo_nueva":
        abrir_nueva_tarea(page)
    elif modo_navegacion == "ninguna":
        print("Usando formulario de Nueva tarea ya abierto...")
    else:
        raise ValueError(
            f"Modo de navegación no válido: {modo_navegacion}"
        )

    crear_tarea_base(
        page=page,
        area_busqueda=area_busqueda,
        area_psinet=area,
        ubicacion_psinet=ubicacion_psinet,
    )

    crear_actividad(
        page=page,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        responsable=responsable,
        participantes=participantes,
    )

    completar_estado_general(page)
    completar_conexiones(page)
    completar_cierre(
        page=page,
        fotos=fotos,
        apr_participa=apr_participa,
        equipo_alza_hombre=equipo_alza_hombre,
    )

    print(
        "\nFormulario preparado para pruebas."
        "\nLa mantención NO ha sido guardada ni finalizada."
        "\nRevisa participantes, APR, alza hombre y fotografías en PSINet."
    )
