[1mdiff --git a/psinet/tareas.py b/psinet/tareas.py[m
[1mindex cee15cb..70c807b 100644[m
[1m--- a/psinet/tareas.py[m
[1m+++ b/psinet/tareas.py[m
[36m@@ -1,23 +1,246 @@[m
[32m+[m[32m"""Automatización de tareas y mantenciones preventivas en PSINet.[m
[32m+[m
[32m+[m[32mEste módulo concentra únicamente las acciones relacionadas con el flujo de[m
[32m+[m[32mTareas / Actividades de PSINet. La navegación del navegador, el inicio de[m
[32m+[m[32msesión y la futura descarga de informes PDF deben permanecer en módulos[m
[32m+[m[32mseparados para mantener una arquitectura clara y mantenible.[m
[32m+[m[32m"""[m
[32m+[m
[32m+[m[32mfrom __future__ import annotations[m
[32m+[m[32mfrom collections.abc import Sequence[m
[32m+[m[32mimport re[m
 from pathlib import Path[m
[32m+[m[32mfrom typing import Any, Sequence[m
[32m+[m[32mfrom automatizacion.data.config import ([m
[32m+[m[32m    OBSERVACION_DEFAULT,[m
[32m+[m[32m    TIPO_TAREA_DEFAULT,[m
[32m+[m[32m    UBICACION_DEFAULT,[m
[32m+[m[32m    TIPO_ACTIVIDAD_DEFAULT,[m
[32m+[m[32m    CAUSA_DEFAULT,[m
[32m+[m[32m    RESPONSABLE_DEFAULT,[m
[32m+[m[32m    PARTICIPANTES_DEFAULT,[m
[32m+[m[32m    APR_PARTICIPA,[m
[32m+[m[32m    ALZA_HOMBRE,[m
[32m+[m[32m    MAXIMO_FOTOS,[m
[32m+[m[32m)[m
[32m+[m[32mfrom playwright.sync_api import ([m
[32m+[m[32m    Locator,[m
[32m+[m[32m    Page,[m
[32m+[m[32m    TimeoutError as PlaywrightTimeoutError,[m
[32m+[m[32m)[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Configuración general del flujo[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m[32m# Texto utilizado al crear la tarea base.[m
[32m+[m[32mOBSERVACION_TAREA_DEFAULT = "Mantenimiento CCTV"[m
[32m+[m
[32m+[m[32m# Texto utilizado al crear la actividad.[m
[32m+[m[32mOBSERVACION_ACTIVIDAD_DEFAULT = "Mantenimiento CCTV"[m
[32m+[m
[32m+[m[32m# Texto utilizado al cerrar la mantención.[m
[32m+[m[32mOBSERVACION_GENERAL_DEFAULT = "Mantenimiento CCTV"[m
[32m+[m
[32m+[m[32mTIPO_TAREA_DEFAULT = "Mantencion Programada"[m
[32m+[m[32mUBICACION_DEFAULT = "DCH-SUBTE"[m
[32m+[m[32mTIPO_ACTIVIDAD_DEFAULT = "Mantenimiento Preventivo"[m
[32m+[m[32mCAUSA_DEFAULT = "CCTV"[m
[32m+[m[32mRESPONSABLE_DEFAULT = "Louis Rivera"[m
[32m+[m
[32m+[m[32mTIMEOUT_CORTO_MS = 800[m
[32m+[m[32mTIMEOUT_NORMAL_MS = 10_000[m
[32m+[m[32mMAXIMO_FOTOS = 15[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Utilidades internas[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef _patron_texto_exacto(texto: str) -> re.Pattern[str]:[m
[32m+[m[32m    """Crea un patrón que acepta espacios externos y omite mayúsculas."""[m
[32m+[m
[32m+[m[32m    return re.compile(rf"^\s*{re.escape(texto)}\s*$", re.IGNORECASE)[m
[32m+[m
[32m+[m
[32m+[m[32mdef _escapar_valor_atributo_css(valor: str) -> str:[m
[32m+[m[32m    """Escapa un valor antes de insertarlo en un selector CSS de atributo."""[m
[32m+[m
[32m+[m[32m    return valor.replace("\\", "\\\\").replace('"', '\\"')[m
[32m+[m
[32m+[m
[32m+[m[32mdef _buscar_input_asociado(page: Page, control: Locator) -> Locator | None:[m
[32m+[m[32m    """Busca el checkbox o radio asociado a una etiqueta visible.[m
[32m+[m
[32m+[m[32m    PSINet utiliza controles Bootstrap personalizados: el ``input`` real suele[m
[32m+[m[32m    estar oculto y el usuario interactúa con un ``label``. Esta función intenta[m
[32m+[m[32m    localizar ese input mediante el atributo ``for`` y, como respaldo, mediante[m
[32m+[m[32m    la estructura HTML cercana.[m
[32m+[m[32m    """[m
 [m
[31m-from playwright.sync_api import Page[m
[32m+[m[32m    try:[m
[32m+[m[32m        identificador = control.get_attribute("for")[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        identificador = None[m
[32m+[m
[32m+[m[32m    if identificador:[m
[32m+[m[32m        identificador_escapado = _escapar_valor_atributo_css(identificador)[m
[32m+[m[32m        candidato = page.locator(f'[id="{identificador_escapado}"]').first[m
[32m+[m
[32m+[m[32m        if candidato.count() > 0:[m
[32m+[m[32m            return candidato[m
[32m+[m
[32m+[m[32m    # Estructura frecuente: <input ...><label ...>Nombre</label>[m
[32m+[m[32m    candidato = control.locator([m
[32m+[m[32m        "xpath=preceding-sibling::input["[m
[32m+[m[32m        "@type='checkbox' or @type='radio'"[m
[32m+[m[32m        "][1]"[m
[32m+[m[32m    ).first[m
[32m+[m
[32m+[m[32m    if candidato.count() > 0:[m
[32m+[m[32m        return candidato[m
[32m+[m
[32m+[m[32m    # Respaldo para controles envueltos por un contenedor Bootstrap.[m
[32m+[m[32m    candidato = control.locator([m
[32m+[m[32m        "xpath=ancestor::*["[m
[32m+[m[32m        "contains(concat(' ', normalize-space(@class), ' '), ' custom-control ')"[m
[32m+[m[32m        "][1]//input[@type='checkbox' or @type='radio'][1]"[m
[32m+[m[32m    ).first[m
[32m+[m
[32m+[m[32m    if candidato.count() > 0:[m
[32m+[m[32m        return candidato[m
[32m+[m
[32m+[m[32m    # Último respaldo: buscar un input dentro del padre inmediato.[m
[32m+[m[32m    candidato = control.locator([m
[32m+[m[32m        "xpath=parent::*//input[@type='checkbox' or @type='radio'][1]"[m
[32m+[m[32m    ).first[m
[32m+[m
[32m+[m[32m    if candidato.count() > 0:[m
[32m+[m[32m        return candidato[m
[32m+[m
[32m+[m[32m    return None[m
 [m
 [m
[31m-OBSERVACION_DEFAULT = "Mantenimiento CCTV"[m
[32m+[m[32mdef _activar_control_etiquetado([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    control: Locator,[m
[32m+[m[32m    timeout: int = TIMEOUT_NORMAL_MS,[m
[32m+[m[32m) -> bool:[m
[32m+[m[32m    """Activa un checkbox/radio personalizado y confirma su estado.[m
[32m+[m
[32m+[m[32m    Retorna ``True`` cuando el control quedó seleccionado. Si no existe un[m
[32m+[m[32m    input verificable, considera exitoso el clic sobre el elemento visible.[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    control.wait_for(state="visible", timeout=timeout)[m
[32m+[m[32m    control.scroll_into_view_if_needed()[m
[32m+[m
[32m+[m[32m    input_asociado = _buscar_input_asociado(page, control)[m
[32m+[m
[32m+[m[32m    if input_asociado is not None:[m
[32m+[m[32m        try:[m
[32m+[m[32m            if input_asociado.is_checked():[m
[32m+[m[32m                return True[m
[32m+[m[32m        except Exception:[m
[32m+[m[32m            # Algunos componentes todavía no están listos para consultar su[m
[32m+[m[32m            # estado; se intentará el clic igualmente.[m
[32m+[m[32m            pass[m
[32m+[m
[32m+[m[32m    # Primer intento: interacción normal con la etiqueta visible.[m
[32m+[m[32m    try:[m
[32m+[m[32m        control.click()[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        # Algunos labels quedan parcialmente cubiertos por componentes de la[m
[32m+[m[32m        # interfaz. En ese caso Playwright puede forzar el clic.[m
[32m+[m[32m        control.click(force=True)[m
[32m+[m
[32m+[m[32m    page.wait_for_timeout(250)[m
[32m+[m
[32m+[m[32m    if input_asociado is None:[m
[32m+[m[32m        return True[m
[32m+[m
[32m+[m[32m    try:[m
[32m+[m[32m        if input_asociado.is_checked():[m
[32m+[m[32m            return True[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        pass[m
[32m+[m
[32m+[m[32m    # Segundo intento: marcar directamente el input oculto.[m
[32m+[m[32m    try:[m
[32m+[m[32m        input_asociado.check(force=True)[m
[32m+[m[32m        page.wait_for_timeout(200)[m
[32m+[m[32m        return input_asociado.is_checked()[m
[32m+[m[32m    except Exception:[m
[32m+[m[32m        return False[m
[32m+[m
[32m+[m
[32m+[m[32mdef _normalizar_participantes([m
[32m+[m[32m    valor: Any,[m
[32m+[m[32m    responsable: str = RESPONSABLE_DEFAULT,[m
[32m+[m[32m) -> list[str]:[m
[32m+[m[32m    """Convierte la configuración de participantes en una lista limpia."""[m
[32m+[m
[32m+[m[32m    if valor is None:[m
[32m+[m[32m        return [responsable][m
[32m+[m
[32m+[m[32m    if isinstance(valor, str):[m
[32m+[m[32m        participantes = [valor][m
[32m+[m[32m    elif isinstance(valor, Sequence):[m
[32m+[m[32m        participantes = [str(nombre) for nombre in valor][m
[32m+[m[32m    else:[m
[32m+[m[32m        raise TypeError([m
[32m+[m[32m            "'participantes' debe ser un nombre o una lista de nombres."[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    # Elimina nombres vacíos y duplicados conservando el orden original.[m
[32m+[m[32m    resultado: list[str] = [][m
[32m+[m[32m    vistos: set[str] = set()[m
 [m
[32m+[m[32m    for nombre in participantes:[m
[32m+[m[32m        nombre_limpio = nombre.strip()[m
[32m+[m[32m        clave = nombre_limpio.casefold()[m
 [m
[31m-def _click_opcion(page: Page, textos: list[str]):[m
[31m-    for texto in textos:[m
[31m-        opcion = page.get_by_text(texto, exact=True)[m
[32m+[m[32m        if nombre_limpio and clave not in vistos:[m
[32m+[m[32m            resultado.append(nombre_limpio)[m
[32m+[m[32m            vistos.add(clave)[m
 [m
[31m-        if opcion.count() > 0:[m
[31m-            opcion.first.click()[m
[31m-            return[m
[32m+[m[32m    return resultado[m
 [m
[31m-    raise RuntimeError(f"No se encontró ninguna opción: {textos}")[m
 [m
[32m+[m[32mdef _convertir_a_bool(valor: Any, nombre_campo: str) -> bool:[m
[32m+[m[32m    """Acepta booleanos y textos como ``Sí``/``No`` provenientes de JSON."""[m
[32m+[m
[32m+[m[32m    if isinstance(valor, bool):[m
[32m+[m[32m        return valor[m
[32m+[m
[32m+[m[32m    if isinstance(valor, int) and valor in {0, 1}:[m
[32m+[m[32m        return bool(valor)[m
[32m+[m
[32m+[m[32m    if isinstance(valor, str):[m
[32m+[m[32m        valor_normalizado = valor.strip().casefold()[m
[32m+[m
[32m+[m[32m        if valor_normalizado in {"si", "sí", "true", "1"}:[m
[32m+[m[32m            return True[m
[32m+[m
[32m+[m[32m        if valor_normalizado in {"no", "false", "0"}:[m
[32m+[m[32m            return False[m
[32m+[m
[32m+[m[32m    raise ValueError([m
[32m+[m[32m        f"Valor inválido para '{nombre_campo}': {valor!r}. "[m
[32m+[m[32m        "Usa True/False o Sí/No."[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Navegación hacia el formulario de tareas[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef ir_a_tareas(page: Page) -> None:[m
[32m+[m[32m    """Abre el módulo Tareas / Actividades y luego la sección Tareas."""[m
 [m
[31m-def ir_a_tareas(page: Page):[m
     page.get_by_role("link", name="Tareas / Actividades").click()[m
     page.wait_for_load_state("networkidle")[m
 [m
[36m@@ -25,40 +248,76 @@[m [mdef ir_a_tareas(page: Page):[m
     page.wait_for_load_state("networkidle")[m
 [m
 [m
[31m-def abrir_nueva_tarea(page: Page):[m
[32m+[m[32mdef abrir_nueva_tarea(page: Page) -> None:[m
[32m+[m[32m    """Abre el formulario para crear una nueva tarea."""[m
[32m+[m
     page.get_by_text("Nueva", exact=True).click()[m
     page.wait_for_load_state("networkidle")[m
 [m
[31m-def seleccionar_camara(page: Page, area_busqueda: str, area_psinet: str):[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Creación de la tarea base[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef seleccionar_camara([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    area_busqueda: str,[m
[32m+[m[32m    area_psinet: str,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Busca y selecciona una cámara en el árbol de PSINet.[m
[32m+[m
[32m+[m[32m    PSINet presenta un error conocido: al escribir el nombre completo puede no[m
[32m+[m[32m    mostrar resultados. Cuando ocurre, se elimina automáticamente el último[m
[32m+[m[32m    carácter para forzar la actualización de la lista.[m
[32m+[m[32m    """[m
[32m+[m
     campo_busqueda = page.get_by_role("textbox").nth(5)[m
 [m
     campo_busqueda.fill(area_busqueda)[m
[31m-    page.wait_for_timeout(800)[m
[32m+[m[32m    page.wait_for_timeout(TIMEOUT_CORTO_MS)[m
 [m
[31m-    opcion = page.get_by_role("treeitem", name=area_psinet)[m
[32m+[m[32m    opcion = page.get_by_role("treeitem", name=area_psinet, exact=True)[m
 [m
     if opcion.count() == 0 and len(area_busqueda) > 1:[m
         campo_busqueda.press("Backspace")[m
[31m-        page.wait_for_timeout(800)[m
[31m-        opcion = page.get_by_role("treeitem", name=area_psinet)[m
[32m+[m[32m        page.wait_for_timeout(TIMEOUT_CORTO_MS)[m
[32m+[m[32m        opcion = page.get_by_role("treeitem", name=area_psinet, exact=True)[m
 [m
     if opcion.count() > 0:[m
         opcion.first.click()[m
[32m+[m[32m        print(f"Cámara seleccionada: {area_psinet}")[m
         return[m
 [m
[31m-    print("")[m
[31m-    print("No pude seleccionar la cámara automáticamente.")[m
[32m+[m[32m    print("\nNo pude seleccionar la cámara automáticamente.")[m
     print("Selecciona la cámara manualmente en PSINet.")[m
[31m-    print("Cuando la selecciones, presiona Enter aquí para continuar.")[m
[31m-    input()[m
[32m+[m[32m    input("Cuando la selecciones, presiona Enter aquí para continuar...")[m
 [m
[31m-def crear_tarea_base(page: Page, area_busqueda: str, area_psinet: str):[m
[32m+[m
[32m+[m[32mdef crear_tarea_base([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    area_busqueda: str,[m
[32m+[m[32m    area_psinet: str,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Completa y crea la tarea principal de mantenimiento."""[m
[32m+[m
[32m+[m[32m    # Tipo de tarea: Mantención Programada.[m
     page.get_by_label("", exact=True).nth(1).click()[m
[31m-    page.get_by_role("treeitem", name="Mantencion Programada").click()[m
[32m+[m[32m    page.get_by_role([m
[32m+[m[32m        "treeitem",[m
[32m+[m[32m        name=TIPO_TAREA_DEFAULT,[m
[32m+[m[32m        exact=True,[m
[32m+[m[32m    ).click()[m
 [m
[32m+[m[32m    # Ubicación/contrato: DCH-SUBTE.[m
     page.get_by_label("", exact=True).nth(1).click()[m
[31m-    page.get_by_role("treeitem", name="DCH-SUBTE").click()[m
[32m+[m[32m    page.get_by_role([m
[32m+[m[32m        "treeitem",[m
[32m+[m[32m        name=UBICACION_DEFAULT,[m
[32m+[m[32m        exact=True,[m
[32m+[m[32m    ).click()[m
 [m
[32m+[m[32m    # Selector de cámara dentro del formulario de nueva tarea.[m
     page.locator("#forms_add_tarea").get_by_label("", exact=True).click()[m
 [m
     seleccionar_camara([m
[36m@@ -67,136 +326,527 @@[m [mdef crear_tarea_base(page: Page, area_busqueda: str, area_psinet: str):[m
         area_psinet=area_psinet,[m
     )[m
 [m
[31m-    page.locator('input[name="text_observacion_tarea"]').fill(OBSERVACION_DEFAULT)[m
[32m+[m[32m    page.locator([m
[32m+[m[32m        'input[name="text_observacion_tarea"]'[m
[32m+[m[32m    ).fill(OBSERVACION_TAREA_DEFAULT)[m
 [m
     print("Voy a presionar Ingresar para crear la tarea base...")[m
[31m-    page.get_by_role("button", name="Ingresar").click()[m
[32m+[m[32m    page.get_by_role("button", name="Ingresar", exact=True).click()[m
     page.wait_for_load_state("networkidle")[m
 [m
[31m-def seleccionar_opcion_select2(page: Page, etiqueta: str, opcion: str):[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Creación de la actividad y selección de participantes[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef seleccionar_opcion_select2([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    etiqueta: str,[m
[32m+[m[32m    opcion: str,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Selecciona una opción en un componente Select2 usando su etiqueta."""[m
[32m+[m
     selector = ([m
         f"xpath=//*[normalize-space()='{etiqueta}']"[m
[31m-        "/following::*[@role='combobox' or contains(@class, 'select2-selection')][1]"[m
[32m+[m[32m        "/following::*["[m
[32m+[m[32m        "@role='combobox' or contains(@class, 'select2-selection')"[m
[32m+[m[32m        "][1]"[m
     )[m
 [m
     page.locator(selector).click()[m
[31m-    page.get_by_role("treeitem", name=opcion).click()[m
[32m+[m[32m    page.get_by_role("treeitem", name=opcion, exact=True).click()[m
[32m+[m
[32m+[m
[32m+[m[32mdef seleccionar_participante([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    nombre_participante: str,[m
[32m+[m[32m    timeout: int = TIMEOUT_NORMAL_MS,[m
[32m+[m[32m) -> bool:[m
[32m+[m[32m    """Busca un participante por su nombre y activa su interruptor.[m
[32m+[m
[32m+[m[32m    La función localiza específicamente el ``label`` del trabajador, busca el[m
[32m+[m[32m    input asociado y comprueba que haya quedado marcado. Esto evita seleccionar[m
[32m+[m[32m    por posición, lo cual era inestable debido a las tres columnas de PSINet.[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    nombre_participante = nombre_participante.strip()[m
[32m+[m
[32m+[m[32m    if not nombre_participante:[m
[32m+[m[32m        raise ValueError("El nombre del participante no puede estar vacío.")[m
[32m+[m
[32m+[m[32m    print(f"Buscando participante: {nombre_participante}")[m
[32m+[m
[32m+[m[32m    patron = _patron_texto_exacto(nombre_participante)[m
[32m+[m[32m    etiquetas = page.locator("label").filter(has_text=patron)[m
[32m+[m
[32m+[m[32m    # Respaldo por si el texto está dentro de un span alojado en el label.[m
[32m+[m[32m    if etiquetas.count() == 0:[m
[32m+[m[32m        texto = page.get_by_text(nombre_participante, exact=True).first[m
[32m+[m
[32m+[m[32m        if texto.count() > 0:[m
[32m+[m[32m            etiquetas = texto.locator("xpath=ancestor-or-self::label[1]")[m
[32m+[m
[32m+[m[32m    if etiquetas.count() == 0:[m
[32m+[m[32m        print(f"No se encontró al participante: {nombre_participante}")[m
[32m+[m[32m        return False[m
[32m+[m
[32m+[m[32m    if etiquetas.count() > 1:[m
[32m+[m[32m        print([m
[32m+[m[32m            f"Advertencia: hay {etiquetas.count()} coincidencias para "[m
[32m+[m[32m            f"'{nombre_participante}'. Se utilizará la primera."[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    etiqueta = etiquetas.first[m
[32m+[m
[32m+[m[32m    try:[m
[32m+[m[32m        seleccionado = _activar_control_etiquetado([m
[32m+[m[32m            page=page,[m
[32m+[m[32m            control=etiqueta,[m
[32m+[m[32m            timeout=timeout,[m
[32m+[m[32m        )[m
[32m+[m[32m    except PlaywrightTimeoutError:[m
[32m+[m[32m        print(f"El participante no quedó visible: {nombre_participante}")[m
[32m+[m[32m        return False[m
[32m+[m[32m    except Exception as error:[m
[32m+[m[32m        print([m
[32m+[m[32m            f"No se pudo seleccionar a {nombre_participante}. "[m
[32m+[m[32m            f"Detalle: {error}"[m
[32m+[m[32m        )[m
[32m+[m[32m        return False[m
[32m+[m
[32m+[m[32m    if seleccionado:[m
[32m+[m[32m        print(f"Participante seleccionado: {nombre_participante}")[m
[32m+[m[32m        return True[m
[32m+[m
[32m+[m[32m    print(f"No fue posible confirmar a: {nombre_participante}")[m
[32m+[m[32m    return False[m
[32m+[m
[32m+[m
[32m+[m[32mdef seleccionar_participantes([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    participantes: Sequence[str],[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Selecciona todos los participantes configurados.[m
[32m+[m
[32m+[m[32m    Si alguno no puede marcarse automáticamente, el flujo se detiene para que[m
[32m+[m[32m    el usuario corrija únicamente los participantes pendientes.[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    participantes_limpios = _normalizar_participantes([m
[32m+[m[32m        participantes,[m
[32m+[m[32m        responsable=RESPONSABLE_DEFAULT,[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    if not participantes_limpios:[m
[32m+[m[32m        print("\nNo se configuraron participantes para esta actividad.")[m
[32m+[m[32m        input([m
[32m+[m[32m            "Selecciona los participantes manualmente y presiona Enter "[m
[32m+[m[32m            "para continuar..."[m
[32m+[m[32m        )[m
[32m+[m[32m        return[m
[32m+[m
[32m+[m[32m    no_seleccionados: list[str] = [][m
[32m+[m
[32m+[m[32m    for participante in participantes_limpios:[m
[32m+[m[32m        if not seleccionar_participante(page, participante):[m
[32m+[m[32m            no_seleccionados.append(participante)[m
[32m+[m
[32m+[m[32m    if no_seleccionados:[m
[32m+[m[32m        print("\nNo se pudieron seleccionar automáticamente:")[m
[32m+[m
[32m+[m[32m        for participante in no_seleccionados:[m
[32m+[m[32m            print(f"  - {participante}")[m
[32m+[m
[32m+[m[32m        input([m
[32m+[m[32m            "Selecciona manualmente los participantes pendientes y "[m
[32m+[m[32m            "presiona Enter para continuar..."[m
[32m+[m[32m        )[m
[32m+[m[32m        return[m
[32m+[m
[32m+[m[32m    print("Todos los participantes fueron seleccionados correctamente.")[m
 [m
 [m
 def crear_actividad([m
     page: Page,[m
     hora_inicio: str = "17:00",[m
     hora_fin: str = "17:10",[m
[31m-    responsable: str = "Louis Rivera",[m
[31m-):[m
[32m+[m[32m    responsable: str = RESPONSABLE_DEFAULT,[m
[32m+[m[32m    participantes: Sequence[str] | None = None,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Crea la actividad asociada a la tarea base."""[m
[32m+[m
     page.locator(".btn.btn-outline-info").first.click()[m
[31m-    page.wait_for_timeout(1000)[m
[32m+[m[32m    page.wait_for_timeout(1_000)[m
 [m
[31m-    seleccionar_opcion_select2(page, "Tipo de Actividad:", "Mantenimiento Preventivo")[m
[31m-    seleccionar_opcion_select2(page, "Causa:", "CCTV")[m
[32m+[m[32m    seleccionar_opcion_select2([m
[32m+[m[32m        page,[m
[32m+[m[32m        "Tipo de Actividad:",[m
[32m+[m[32m        TIPO_ACTIVIDAD_DEFAULT,[m
[32m+[m[32m    )[m
[32m+[m[32m    seleccionar_opcion_select2(page, "Causa:", CAUSA_DEFAULT)[m
 [m
     page.locator("#time_inicio_actividad").fill(hora_inicio)[m
     page.locator('input[name="time_cierre_actividad"]').fill(hora_fin)[m
[31m-    page.locator('input[name="text_observacion_actividad"]').fill(OBSERVACION_DEFAULT)[m
 [m
[31m-    print("")[m
[31m-    print("Selecciona manualmente los participantes/trabajadores.")[m
[31m-    print("Cuando estén seleccionados, presiona Enter aquí para continuar.")[m
[31m-    input()[m
[32m+[m[32m    page.locator([m
[32m+[m[32m        'input[name="text_observacion_actividad"]'[m
[32m+[m[32m    ).fill(OBSERVACION_ACTIVIDAD_DEFAULT)[m
[32m+[m
[32m+[m[32m    participantes_objetivo = ([m
[32m+[m[32m        list(participantes) if participantes is not None else [responsable][m
[32m+[m[32m    )[m
[32m+[m[32m    seleccionar_participantes(page, participantes_objetivo)[m
 [m
[32m+[m[32m    # PSINet incluye un selector adicional que actualmente aparece con valor[m
[32m+[m[32m    # "No" y que el flujo original cambia a "Si". Se mantiene esta acción para[m
[32m+[m[32m    # no alterar el comportamiento ya validado. Cuando conozcamos la etiqueta[m
[32m+[m[32m    # exacta de ese campo, convendrá reemplazar este selector por uno etiquetado.[m
     page.get_by_role("textbox", name="No", exact=True).click()[m
[31m-    page.get_by_role("treeitem", name="Si").click()[m
[32m+[m[32m    page.get_by_role("treeitem", name="Si", exact=True).click()[m
 [m
     print("Voy a presionar Ingresar para crear la actividad...")[m
[31m-    page.get_by_role("button", name="Ingresar").click()[m
[32m+[m[32m    page.get_by_role("button", name="Ingresar", exact=True).click()[m
     page.wait_for_load_state("networkidle")[m
 [m
[31m-def seleccionar_no_por_pregunta(page: Page, pregunta: str):[m
[31m-    opcion_no = page.locator([m
[31m-        f"xpath=//*[contains(normalize-space(), '{pregunta}')]"[m
[31m-        "/following::*[normalize-space()='No'][1]"[m
[31m-    )[m
[31m-    opcion_no.click()[m
 [m
[31m-def completar_estado_general(page: Page):[m
[31m-    page.get_by_role("link", name="ESTADO GENERAL").click()[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Checklist de mantenimiento[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
 [m
[31m-    for indice in range(6):[m
[31m-        page.get_by_text("B", exact=True).nth(indice).click()[m
[31m-[m
[31m-    page.locator("div:nth-child(7) > div > .custom-control-label").first.click()[m
 [m
[31m-    page.get_by_role("link", name="ESTADO GENERAL").click()[m
[32m+[m[32mdef completar_estado_general(page: Page) -> None:[m
[32m+[m[32m    """Completa la sección ESTADO GENERAL con los valores ya validados."""[m
 [m
[32m+[m[32m    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()[m
 [m
[31m-def completar_conexiones(page: Page):[m
[31m-    page.get_by_role("link", name="CONEXIONES").click()[m
[32m+[m[32m    # PSINet muestra seis evaluaciones cuyo estado correcto es "B".[m
[32m+[m[32m    for indice in range(6):[m
[32m+[m[32m        page.get_by_text("B", exact=True).nth(indice).click()[m
 [m
[32m+[m[32m    # Último control de la sección. Se conserva el selector validado en terreno.[m
     page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div > div:nth-child(5) > .custom-control-label"[m
[31m-    ).first.click()[m
[31m-    page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div:nth-child(2) > div > .custom-control-label"[m
[31m-    ).first.click()[m
[31m-    page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div:nth-child(3) > div:nth-child(5) > .custom-control-label"[m
[31m-    ).click()[m
[31m-    page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div:nth-child(4) > div > .custom-control-label"[m
[31m-    ).first.click()[m
[31m-    page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div:nth-child(5) > div > .custom-control-label"[m
[31m-    ).first.click()[m
[31m-    page.locator([m
[31m-        "#collapse1543 > .card-body > .container > div:nth-child(6) > div > .custom-control-label"[m
[32m+[m[32m        "div:nth-child(7) > div > .custom-control-label"[m
     ).first.click()[m
 [m
[31m-    page.get_by_role("link", name="CONEXIONES").click()[m
[32m+[m[32m    # Cierra el acordeón para continuar con la siguiente sección.[m
[32m+[m[32m    page.get_by_role("link", name="ESTADO GENERAL", exact=True).click()[m
[32m+[m
[32m+[m
[32m+[m[32mdef completar_conexiones(page: Page) -> None:[m
[32m+[m[32m    """Completa la sección CONEXIONES con los valores ya validados."""[m
[32m+[m
[32m+[m[32m    page.get_by_role("link", name="CONEXIONES", exact=True).click()[m
[32m+[m
[32m+[m[32m    # Estos selectores corresponden a la estructura actual del checklist de[m
[32m+[m[32m    # PSINet. Se mantienen agrupados para facilitar su reemplazo si la interfaz[m
[32m+[m[32m    # cambia en el futuro.[m
[32m+[m[32m    selectores = [[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > div > "[m
[32m+[m[32m            "div:nth-child(5) > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > "[m
[32m+[m[32m            "div:nth-child(2) > div > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > "[m
[32m+[m[32m            "div:nth-child(3) > div:nth-child(5) > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > "[m
[32m+[m[32m            "div:nth-child(4) > div > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > "[m
[32m+[m[32m            "div:nth-child(5) > div > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "#collapse1543 > .card-body > .container > "[m
[32m+[m[32m            "div:nth-child(6) > div > .custom-control-label"[m
[32m+[m[32m        ),[m
[32m+[m[32m    ][m
[32m+[m
[32m+[m[32m    for selector in selectores:[m
[32m+[m[32m        page.locator(selector).first.click()[m
[32m+[m
[32m+[m[32m    page.get_by_role("link", name="CONEXIONES", exact=True).click()[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Cierre: APR, equipo alza hombre, observaciones y fotografías[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef seleccionar_opcion_bloque([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    titulo_bloque: str,[m
[32m+[m[32m    opcion: str,[m
[32m+[m[32m    timeout: int = TIMEOUT_NORMAL_MS,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Selecciona ``Si`` o ``No`` dentro de una tarjeta del formulario.[m
[32m+[m
[32m+[m[32m    El bloque se identifica por su pregunta, por lo que no se confunde el ``No``[m
[32m+[m[32m    de APR con el ``No`` de equipo alza hombre.[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    opcion_normalizada = opcion.strip().casefold()[m
[32m+[m
[32m+[m[32m    if opcion_normalizada in {"si", "sí"}:[m
[32m+[m[32m        texto_opcion = "Si"[m
[32m+[m[32m    elif opcion_normalizada == "no":[m
[32m+[m[32m        texto_opcion = "No"[m
[32m+[m[32m    else:[m
[32m+[m[32m        raise ValueError([m
[32m+[m[32m            f"Opción inválida: {opcion!r}. Debe ser 'Sí' o 'No'."[m
[32m+[m[32m        )[m
 [m
[32m+[m[32m    titulo = page.get_by_text(titulo_bloque, exact=True).first[m
 [m
[31m-def completar_cierre(page: Page, fotos: list[str]):[m
     try:[m
[31m-        seleccionar_no_por_pregunta(page, "APR participa en la actividad")[m
[31m-        seleccionar_no_por_pregunta(page, "Apoyo de equipo alza hombre")[m
[31m-    except Exception as error:[m
[31m-        print("")[m
[31m-        print("No pude seleccionar automaticamente APR/Alza hombre.")[m
[31m-        print("Selecciona manualmente los 'No' y luego presiona Enter aqui.")[m
[31m-        print(f"Detalle: {error}")[m
[31m-        input()[m
[32m+[m[32m        titulo.wait_for(state="visible", timeout=timeout)[m
[32m+[m[32m    except PlaywrightTimeoutError as error:[m
[32m+[m[32m        raise RuntimeError([m
[32m+[m[32m            f"No se encontró el bloque: {titulo_bloque}"[m
[32m+[m[32m        ) from error[m
[32m+[m
[32m+[m[32m    # Busca el ancestro más cercano que contenga simultáneamente las opciones[m
[32m+[m[32m    # Si y No. En la interfaz actual corresponde a la tarjeta completa.[m
[32m+[m[32m    bloque = titulo.locator([m
[32m+[m[32m        "xpath=ancestor::*["[m
[32m+[m[32m        ".//*[normalize-space()='Si'] and "[m
[32m+[m[32m        ".//*[normalize-space()='No']"[m
[32m+[m[32m        "][1]"[m
[32m+[m[32m    ).first[m
[32m+[m
[32m+[m[32m    if bloque.count() == 0:[m
[32m+[m[32m        raise RuntimeError([m
[32m+[m[32m            f"No se pudo identificar la tarjeta de: {titulo_bloque}"[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    patron_opcion = _patron_texto_exacto(texto_opcion)[m
[32m+[m[32m    controles = bloque.locator([m
[32m+[m[32m        "label, button, [role='button']"[m
[32m+[m[32m    ).filter(has_text=patron_opcion)[m
[32m+[m
[32m+[m[32m    if controles.count() == 0:[m
[32m+[m[32m        # Respaldo para interfaces donde el texto está dentro de un span.[m
[32m+[m[32m        texto_visible = bloque.get_by_text(texto_opcion, exact=True).first[m
[32m+[m
[32m+[m[32m        if texto_visible.count() > 0:[m
[32m+[m[32m            controles = texto_visible.locator([m
[32m+[m[32m                "xpath=ancestor-or-self::*["[m
[32m+[m[32m                "self::label or self::button or @role='button'"[m
[32m+[m[32m                "][1]"[m
[32m+[m[32m            )[m
[32m+[m
[32m+[m[32m    if controles.count() == 0:[m
[32m+[m[32m        raise RuntimeError([m
[32m+[m[32m            f"No se encontró la opción '{texto_opcion}' dentro de "[m
[32m+[m[32m            f"'{titulo_bloque}'."[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    seleccionado = _activar_control_etiquetado([m
[32m+[m[32m        page=page,[m
[32m+[m[32m        control=controles.first,[m
[32m+[m[32m        timeout=timeout,[m
[32m+[m[32m    )[m
 [m
[31m-    page.get_by_role("textbox", name="Observaciones generales:").fill(OBSERVACION_DEFAULT)[m
[32m+[m[32m    if not seleccionado:[m
[32m+[m[32m        raise RuntimeError([m
[32m+[m[32m            f"No fue posible confirmar '{texto_opcion}' en "[m
[32m+[m[32m            f"'{titulo_bloque}'."[m
[32m+[m[32m        )[m
 [m
[31m-    if fotos:[m
[31m-        subir_fotos(page, fotos)[m
[32m+[m[32m    print(f"{titulo_bloque}: {texto_opcion}")[m
[32m+[m
[32m+[m
[32m+[m[32mdef subir_fotos([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    fotos: Sequence[str],[m
[32m+[m[32m    dejar_campo_extra: bool = False,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """[m
[32m+[m[32m    Adjunta automáticamente las fotografías recibidas.[m
[32m+[m
[32m+[m[32m    Cuando dejar_campo_extra=True, después de subir las fotografías[m
[32m+[m[32m    se crea un campo adicional vacío para que el usuario pueda agregar[m
[32m+[m[32m    manualmente otra imagen.[m
 [m
[31m-    print("")[m
[31m-    print("Formulario listo para adjuntar fotos y guardar.")[m
[31m-    print("Sube las fotos manualmente y presiona Guardar en PSINet.")[m
[32m+[m[32m    En el flujo manual se utiliza para:[m
 [m
[32m+[m[32m        1. ART delantera.[m
[32m+[m[32m        2. ART trasera.[m
[32m+[m[32m        3. Fotografía del mantenimiento agregada manualmente.[m
[32m+[m[32m    """[m
 [m
[31m-def subir_fotos(page: Page, fotos: list[str]):[m
     if not fotos:[m
         return[m
 [m
[32m+[m[32m    if len(fotos) > MAXIMO_FOTOS:[m
[32m+[m[32m        raise ValueError([m
[32m+[m[32m            f"Se recibieron {len(fotos)} fotografías, pero PSINet "[m
[32m+[m[32m            f"permite un máximo de {MAXIMO_FOTOS}."[m
[32m+[m[32m        )[m
[32m+[m
     for indice, foto in enumerate(fotos, start=1):[m
         ruta_foto = Path(foto)[m
 [m
[32m+[m[32m        if not ruta_foto.exists():[m
[32m+[m[32m            raise FileNotFoundError([m
[32m+[m[32m                f"No se encontró la fotografía: {ruta_foto}"[m
[32m+[m[32m            )[m
[32m+[m
[32m+[m[32m        print([m
[32m+[m[32m            f"Adjuntando fotografía {indice}/{len(fotos)}: "[m
[32m+[m[32m            f"{ruta_foto.name}"[m
[32m+[m[32m        )[m
[32m+[m
         if indice == 1:[m
[31m-            page.get_by_role("button", name="Choose File").set_input_files(str(ruta_foto))[m
[32m+[m[32m            selector_archivo = page.get_by_role([m
[32m+[m[32m                "button",[m
[32m+[m[32m                name="Choose File",[m
[32m+[m[32m            )[m
         else:[m
[31m-            page.locator(f"#inputFoto{indice}").set_input_files(str(ruta_foto))[m
[32m+[m[32m            selector_archivo = page.locator([m
[32m+[m[32m                f"#inputFoto{indice}"[m
[32m+[m[32m            )[m
 [m
[32m+[m[32m        selector_archivo.set_input_files(str(ruta_foto))[m
[32m+[m
[32m+[m[32m        # Mientras queden fotografías por subir, crea el siguiente campo.[m
         if indice < len(fotos):[m
             page.locator(f"#plus{indice}").click()[m
[32m+[m[32m            page.wait_for_timeout(300)[m
[32m+[m
[32m+[m[32m    # Después de cargar las ART, crea un campo vacío adicional[m
[32m+[m[32m    # para la fotografía manual del mantenimiento.[m
[32m+[m[32m    if dejar_campo_extra and len(fotos) < MAXIMO_FOTOS:[m
[32m+[m[32m        boton_agregar = page.locator([m
[32m+[m[32m            f"#plus{len(fotos)}"[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        if boton_agregar.count() > 0:[m
[32m+[m[32m            boton_agregar.click()[m
[32m+[m[32m            page.wait_for_timeout(300)[m
[32m+[m
[32m+[m[32m            print([m
[32m+[m[32m                "Campo adicional preparado para la fotografía "[m
[32m+[m[32m                "manual del mantenimiento."[m
[32m+[m[32m            )[m
[32m+[m[32m        else:[m
[32m+[m[32m            print([m
[32m+[m[32m                "No se encontró el botón para crear un campo "[m
[32m+[m[32m                "fotográfico adicional."[m
[32m+[m[32m            )[m
 [m
 [m
[31m-def crear_mantenimiento(page: Page, evidencia: dict, modo_navegacion: str = "completa"):[m
[32m+[m[32mdef completar_cierre([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    fotos: Sequence[str],[m
[32m+[m[32m    apr_participa: bool = False,[m
[32m+[m[32m    equipo_alza_hombre: bool = False,[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Completa los datos finales antes de guardar la mantención."""[m
[32m+[m
[32m+[m[32m    configuraciones = [[m
[32m+[m[32m        ([m
[32m+[m[32m            "APR participa en la actividad?",[m
[32m+[m[32m            "Si" if apr_participa else "No",[m
[32m+[m[32m        ),[m
[32m+[m[32m        ([m
[32m+[m[32m            "Apoyo de equipo alza hombre?",[m
[32m+[m[32m            "Si" if equipo_alza_hombre else "No",[m
[32m+[m[32m        ),[m
[32m+[m[32m    ][m
[32m+[m
[32m+[m[32m    errores: list[str] = [][m
[32m+[m
[32m+[m[32m    for pregunta, opcion in configuraciones:[m
[32m+[m[32m        try:[m
[32m+[m[32m            seleccionar_opcion_bloque([m
[32m+[m[32m                page=page,[m
[32m+[m[32m                titulo_bloque=pregunta,[m
[32m+[m[32m                opcion=opcion,[m
[32m+[m[32m            )[m
[32m+[m[32m        except Exception as error:[m
[32m+[m[32m            errores.append(f"{pregunta}: {error}")[m
[32m+[m
[32m+[m[32m    if errores:[m
[32m+[m[32m        print("\nNo pude completar automáticamente estas opciones:")[m
[32m+[m
[32m+[m[32m        for error in errores:[m
[32m+[m[32m            print(f"  - {error}")[m
[32m+[m
[32m+[m[32m        input([m
[32m+[m[32m            "Selecciona manualmente las opciones pendientes y presiona "[m
[32m+[m[32m            "Enter para continuar..."[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    page.get_by_role([m
[32m+[m[32m        "textbox",[m
[32m+[m[32m        name="Observaciones generales:",[m
[32m+[m[32m    ).fill(OBSERVACION_DEFAULT)[m
[32m+[m
[32m+[m[32m    if fotos:[m
[32m+[m[32m        subir_fotos([m
[32m+[m[32m            page=page,[m
[32m+[m[32m            fotos=fotos,[m
[32m+[m[32m            dejar_campo_extra=True,[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    print()[m
[32m+[m[32m    print("Las fotografías de la ART fueron cargadas automáticamente.")[m
[32m+[m[32m    print("Agrega manualmente la fotografía del mantenimiento.")[m
[32m+[m[32m    print("La mantención NO se guardará automáticamente durante esta prueba.")[m
[32m+[m
[32m+[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m[32m# Orquestador principal de una mantención[m
[32m+[m[32m# ---------------------------------------------------------------------------[m
[32m+[m
[32m+[m
[32m+[m[32mdef crear_mantenimiento([m
[32m+[m[32m    page: Page,[m
[32m+[m[32m    evidencia: dict[str, Any],[m
[32m+[m[32m    modo_navegacion: str = "completa",[m
[32m+[m[32m) -> None:[m
[32m+[m[32m    """Ejecuta el flujo completo de una mantención preventiva.[m
[32m+[m
[32m+[m[32m    Claves opcionales admitidas dentro de ``evidencia``::[m
[32m+[m
[32m+[m[32m        {[m
[32m+[m[32m            "participantes": ["Louis Rivera", "Emgelbert Pizarro"],[m
[32m+[m[32m            "apr_participa": false,[m
[32m+[m[32m            "equipo_alza_hombre": false[m
[32m+[m[32m        }[m
[32m+[m
[32m+[m[32m    Cuando no se entrega ``participantes``, se selecciona a Louis Rivera por[m
[32m+[m[32m    defecto. APR y equipo alza hombre quedan en ``No`` por defecto.[m
[32m+[m[32m    """[m
[32m+[m
     area = evidencia["area"][m
     area_busqueda = evidencia.get("area_busqueda", area)[m
     fotos = evidencia.get("fotos", [])[m
     hora_inicio = evidencia.get("hora_inicio", "17:00")[m
     hora_fin = evidencia.get("hora_fin", "17:10")[m
[32m+[m[32m    responsable = str([m
[32m+[m[32m        evidencia.get("responsable", RESPONSABLE_DEFAULT)[m
[32m+[m[32m    ).strip()[m
[32m+[m
[32m+[m[32m    participantes = _normalizar_participantes([m
[32m+[m[32m        evidencia.get("participantes"),[m
[32m+[m[32m        responsable=responsable,[m
[32m+[m[32m    )[m
[32m+[m[32m    apr_participa = _convertir_a_bool([m
[32m+[m[32m        evidencia.get("apr_participa", False),[m
[32m+[m[32m        "apr_participa",[m
[32m+[m[32m    )[m
[32m+[m[32m    equipo_alza_hombre = _convertir_a_bool([m
[32m+[m[32m        evidencia.get("equipo_alza_hombre", False),[m
[32m+[m[32m        "equipo_alza_hombre",[m
[32m+[m[32m    )[m
 [m
     if modo_navegacion == "completa":[m
         ir_a_tareas(page)[m
[36m@@ -206,7 +856,9 @@[m [mdef crear_mantenimiento(page: Page, evidencia: dict, modo_navegacion: str = "com[m
     elif modo_navegacion == "ninguna":[m
         print("Usando formulario de Nueva tarea ya abierto...")[m
     else:[m
[31m-        raise ValueError(f"Modo de navegación no válido: {modo_navegacion}")[m
[32m+[m[32m        raise ValueError([m
[32m+[m[32m            f"Modo de navegación no válido: {modo_navegacion}"[m
[32m+[m[32m        )[m
 [m
     crear_tarea_base([m
         page=page,[m
[36m@@ -218,10 +870,21 @@[m [mdef crear_mantenimiento(page: Page, evidencia: dict, modo_navegacion: str = "com[m
         page=page,[m
         hora_inicio=hora_inicio,[m
         hora_fin=hora_fin,[m
[32m+[m[32m        responsable=responsable,[m
[32m+[m[32m        participantes=participantes,[m
     )[m
 [m
     completar_estado_general(page)[m
     completar_conexiones(page)[m
[31m-    completar_cierre(page, fotos)[m
[32m+[m[32m    completar_cierre([m
[32m+[m[32m        page=page,[m
[32m+[m[32m        fotos=fotos,[m
[32m+[m[32m        apr_participa=apr_participa,[m
[32m+[m[32m        equipo_alza_hombre=equipo_alza_hombre,[m
[32m+[m[32m    )[m
 [m
[31m-    print("Mantención completada. Sube las fotos manualmente y guarda.")[m
\ No newline at end of file[m
[32m+[m[32mprint([m
[32m+[m[32m    "\nFormulario preparado para pruebas."[m
[32m+[m[32m    "\nLa mantención NO ha sido guardada ni finalizada."[m
[32m+[m[32m    "\nRevisa participantes, APR, alza hombre y fotografías en PSINet."[m
[32m+[m[32m)[m
\ No newline at end of file[m
[1mdiff --git a/psinet_auto_manual.py b/psinet_auto_manual.py[m
[1mindex 094082c..f83acff 100644[m
[1m--- a/psinet_auto_manual.py[m
[1m+++ b/psinet_auto_manual.py[m
[36m@@ -1,4 +1,5 @@[m
 from datetime import datetime, timedelta[m
[32m+[m[32mfrom pathlib import Path[m
 from psinet.descargas import descargar_pdf_abierto[m
 from psinet.login import login_psinet[m
 from psinet.navegador import iniciar_navegador[m
[36m@@ -7,27 +8,73 @@[m [mfrom psinet.tareas import crear_mantenimiento[m
 [m
 FORMATO_HORA = "%H:%M"[m
 DURACION_MINUTOS = 10[m
[32m+[m[32m# Directorio raíz del proyecto.[m
[32m+[m[32mDIRECTORIO_PROYECTO = Path(__file__).resolve().parent[m
[32m+[m
[32m+[m[32m# Carpeta donde se almacenan las fotografías permanentes de la ART.[m
[32m+[m[32mDIRECTORIO_ART = ([m
[32m+[m[32m    DIRECTORIO_PROYECTO[m
[32m+[m[32m    / "automatizacion"[m
[32m+[m[32m    / "data"[m
[32m+[m[32m    / "art"[m
[32m+[m[32m)[m
[32m+[m
[32m+[m[32m# Nombres esperados, sin extensión.[m
[32m+[m[32mNOMBRES_FOTOS_ART = [[m
[32m+[m[32m    "ART",[m
[32m+[m[32m    "ART_atras",[m
[32m+[m[32m][m
[32m+[m
[32m+[m[32mEXTENSIONES_IMAGEN_PERMITIDAS = {[m
[32m+[m[32m    ".jpg",[m
[32m+[m[32m    ".jpeg",[m
[32m+[m[32m    ".png",[m
[32m+[m[32m}[m
[32m+[m[32m# Participantes que se seleccionarán automáticamente en cada actividad.[m
[32m+[m[32m# Los nombres deben coincidir exactamente con los mostrados por PSINet.[m
[32m+[m[32mPARTICIPANTES_DEFAULT = [[m
[32m+[m[32m    "Louis Rivera",[m
[32m+[m[32m    "Emgelbert Pizarro",[m
[32m+[m[32m][m
[32m+[m
[32m+[m[32m# Configuración predeterminada del cierre.[m
[32m+[m[32mAPR_PARTICIPA_DEFAULT = False[m
[32m+[m[32mEQUIPO_ALZA_HOMBRE_DEFAULT = False[m
 [m
 [m
 def sumar_minutos(hora: str, minutos: int) -> str:[m
[32m+[m[32m    """Suma minutos a una hora expresada en formato HH:MM."""[m
[32m+[m
     base = datetime.strptime(hora, FORMATO_HORA)[m
     nueva = base + timedelta(minutes=minutos)[m
[32m+[m
     return nueva.strftime(FORMATO_HORA)[m
 [m
 [m
[31m-def pedir_hora_inicio():[m
[31m-    hora = input("Hora inicial del primer mantenimiento (ej: 17:00): ").strip()[m
[32m+[m[32mdef pedir_hora_inicio() -> str:[m
[32m+[m[32m    """Solicita la hora del primer mantenimiento."""[m
[32m+[m
[32m+[m[32m    hora = input([m
[32m+[m[32m        "Hora inicial del primer mantenimiento (ej: 17:00): "[m
[32m+[m[32m    ).strip()[m
 [m
     if not hora:[m
         hora = "17:00"[m
 [m
[32m+[m[32m    # Valida que la hora tenga un formato correcto.[m
     datetime.strptime(hora, FORMATO_HORA)[m
[32m+[m
     return hora[m
 [m
 [m
[31m-def pedir_area():[m
[32m+[m[32mdef pedir_area() -> str | None:[m
[32m+[m[32m    """Solicita el nombre de la cámara o finaliza el ciclo."""[m
[32m+[m
     while True:[m
[31m-        area = input("Nombre exacto de la cámara/área en PSINet ('salir' para terminar): ").strip()[m
[32m+[m[32m        area = input([m
[32m+[m[32m            "Nombre exacto de la cámara/área en PSINet "[m
[32m+[m[32m            "('salir' para terminar): "[m
[32m+[m[32m        ).strip()[m
 [m
         if area.lower() in {"salir", "exit", "q"}:[m
             return None[m
[36m@@ -37,20 +84,92 @@[m [mdef pedir_area():[m
 [m
         print("Debes escribir un nombre de cámara o 'salir'.")[m
 [m
[32m+[m[32mdef buscar_imagen_por_nombre([m
[32m+[m[32m    directorio: Path,[m
[32m+[m[32m    nombre: str,[m
[32m+[m[32m) -> Path:[m
[32m+[m[32m    """[m
[32m+[m[32m    Busca una imagen por su nombre base, sin exigir una extensión específica.[m
[32m+[m
[32m+[m[32m    Ejemplos válidos:[m
[32m+[m[32m        ART.jpg[m
[32m+[m[32m        ART.jpeg[m
[32m+[m[32m        ART.png[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    if not directorio.exists():[m
[32m+[m[32m        raise FileNotFoundError([m
[32m+[m[32m            f"No existe la carpeta de fotografías ART: {directorio}"[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    for archivo in directorio.iterdir():[m
[32m+[m[32m        if not archivo.is_file():[m
[32m+[m[32m            continue[m
[32m+[m
[32m+[m[32m        if archivo.suffix.lower() not in EXTENSIONES_IMAGEN_PERMITIDAS:[m
[32m+[m[32m            continue[m
[32m+[m
[32m+[m[32m        if archivo.stem.casefold() == nombre.casefold():[m
[32m+[m[32m            return archivo.resolve()[m
[32m+[m
[32m+[m[32m    raise FileNotFoundError([m
[32m+[m[32m        f"No se encontró la fotografía '{nombre}' en: {directorio}"[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m
[32m+[m[32mdef obtener_fotos_art() -> list[str]:[m
[32m+[m[32m    """[m
[32m+[m[32m    Obtiene las fotografías delantera y trasera de la ART.[m
[32m+[m
[32m+[m[32m    Mantiene el siguiente orden:[m
[32m+[m[32m        1. ART[m
[32m+[m[32m        2. ART_atras[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    fotos_art: list[str] = [][m
[32m+[m
[32m+[m[32m    for nombre in NOMBRES_FOTOS_ART:[m
[32m+[m[32m        ruta = buscar_imagen_por_nombre([m
[32m+[m[32m            directorio=DIRECTORIO_ART,[m
[32m+[m[32m            nombre=nombre,[m
[32m+[m[32m        )[m
 [m
[31m-def crear_evidencia_manual(area: str, hora_inicio: str):[m
[31m-    hora_fin = sumar_minutos(hora_inicio, DURACION_MINUTOS)[m
[32m+[m[32m        fotos_art.append(str(ruta))[m
[32m+[m
[32m+[m[32m    return fotos_art[m
[32m+[m
[32m+[m[32mdef crear_evidencia_manual([m
[32m+[m[32m    area: str,[m
[32m+[m[32m    hora_inicio: str,[m
[32m+[m[32m) -> dict:[m
[32m+[m[32m    """Construye la evidencia utilizada por crear_mantenimiento()."""[m
[32m+[m
[32m+[m[32m    hora_fin = sumar_minutos([m
[32m+[m[32m        hora=hora_inicio,[m
[32m+[m[32m        minutos=DURACION_MINUTOS,[m
[32m+[m[32m    )[m
 [m
     return {[m
         "area": area,[m
         "area_busqueda": area,[m
         "hora_inicio": hora_inicio,[m
         "hora_fin": hora_fin,[m
[31m-        "fotos": [],[m
[32m+[m
[32m+[m[32m        # Participantes de la actividad.[m
[32m+[m[32m        "participantes": PARTICIPANTES_DEFAULT.copy(),[m
[32m+[m
[32m+[m[32m        # Opciones del cierre.[m
[32m+[m[32m        "apr_participa": APR_PARTICIPA_DEFAULT,[m
[32m+[m[32m        "equipo_alza_hombre": EQUIPO_ALZA_HOMBRE_DEFAULT,[m
[32m+[m
[32m+[m[32m        # Las fotografías siguen cargándose manualmente durante las pruebas.[m
[32m+[m[32m        "fotos": obtener_fotos_art(),[m
     }[m
 [m
 [m
[31m-def main():[m
[32m+[m[32mdef main() -> None:[m
[32m+[m[32m    """Ejecuta mantenciones manuales consecutivas usando la misma sesión."""[m
[32m+[m
     hora_actual = pedir_hora_inicio()[m
     modo_navegacion = "completa"[m
 [m
[36m@@ -64,25 +183,53 @@[m [mdef main():[m
                 print("Proceso finalizado.")[m
                 break[m
 [m
[31m-            evidencia = crear_evidencia_manual(area, hora_actual)[m
[32m+[m[32m            evidencia = crear_evidencia_manual([m
[32m+[m[32m                area=area,[m
[32m+[m[32m                hora_inicio=hora_actual,[m
[32m+[m[32m            )[m
 [m
[32m+[m[32m            print()[m
             print([m
                 f"Cargando mantenimiento: {area} "[m
[31m-                f"({evidencia['hora_inicio']} - {evidencia['hora_fin']})"[m
[32m+[m[32m                f"({evidencia['hora_inicio']} - "[m
[32m+[m[32m                f"{evidencia['hora_fin']})"[m
[32m+[m[32m            )[m
[32m+[m[32m            print([m
[32m+[m[32m                "Participantes configurados: "[m
[32m+[m[32m                f"{', '.join(evidencia['participantes'])}"[m
             )[m
 [m
[31m-            crear_mantenimiento(page, evidencia, modo_navegacion=modo_navegacion)[m
[32m+[m[32m            crear_mantenimiento([m
[32m+[m[32m                page=page,[m
[32m+[m[32m                evidencia=evidencia,[m
[32m+[m[32m                modo_navegacion=modo_navegacion,[m
[32m+[m[32m            )[m
 [m
             input([m
[31m-                "Sube las fotos y guarda manualmente. "[m
[31m-                "Cuando se abra el PDF o PSINet vuelva al listado, presiona Enter..."[m
[32m+[m[32m                "\nSube manualmente la fotografía del mantenimiento.\n"[m
[32m+[m[32m                "Cuando esté cargada, presiona Enter para que CCTVFlow guarde "[m
[32m+[m[32m                "la mantención y descargue el PDF..."[m
             )[m
 [m
[32m+[m[32m            with page.expect_popup(timeout=30_000) as popup_info:[m
[32m+[m[32m                page.get_by_role([m
[32m+[m[32m                    "button",[m
[32m+[m[32m                    name="Guardar",[m
[32m+[m[32m                    exact=True,[m
[32m+[m[32m                ).click()[m
[32m+[m
[32m+[m[32m            pagina_pdf = popup_info.value[m
[32m+[m[32m            pagina_pdf.wait_for_load_state("domcontentloaded")[m
[32m+[m
             descargar_pdf_abierto(page)[m
 [m
[32m+[m[32m            # La hora final de esta cámara pasa a ser la hora inicial[m
[32m+[m[32m            # de la siguiente.[m
             hora_actual = evidencia["hora_fin"][m
[31m-            modo_navegacion = "solo_nueva"[m
 [m
[32m+[m[32m            # Después de la primera mantención ya estamos dentro del módulo[m
[32m+[m[32m            # de tareas, por lo que solo se abre una tarea nueva.[m
[32m+[m[32m            modo_navegacion = "solo_nueva"[m
 [m
 [m
 if __name__ == "__main__":[m
[1mdiff --git a/requirements.txt b/requirements.txt[m
[1mindex d93b449..1ca4634 100644[m
[1m--- a/requirements.txt[m
[1m+++ b/requirements.txt[m
[36m@@ -1,2 +1,9 @@[m
[31m-playwright[m
[31m-python-dotenv[m
\ No newline at end of file[m
[32m+[m[32mgreenlet==3.5.3[m
[32m+[m[32mplaywright==1.61.0[m
[32m+[m[32mpyee==13.0.1[m
[32m+[m[32mPySide6==6.11.1[m
[32m+[m[32mPySide6_Addons==6.11.1[m
[32m+[m[32mPySide6_Essentials==6.11.1[m
[32m+[m[32mpython-dotenv==1.2.2[m
[32m+[m[32mshiboken6==6.11.1[m
[32m+[m[32mtyping_extensions==4.16.0[m
