"""Orquestación del formulario completo de una mantención."""

from __future__ import annotations

from collections.abc import Sequence

from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from cctvflow.config import OBSERVACION_DEFAULT
from cctvflow.models import SolicitudMantenimiento
from cctvflow.portal.checklists import (
    completar_conexiones,
    completar_estado_general,
)
from cctvflow.portal.controls import (
    TIMEOUT_NORMAL_MS,
    activar_control_etiquetado,
    patron_texto_exacto,
)
from cctvflow.portal.manual import (
    ConfirmacionManual,
    esperar_confirmacion_manual,
)
from cctvflow.portal.task_form import (
    abrir_nueva_tarea,
    crear_actividad,
    crear_tarea_base,
    ir_a_tareas,
)
from cctvflow.portal.uploads import subir_fotos


def seleccionar_opcion_bloque(
    page: Page,
    titulo_bloque: str,
    opcion: str,
    timeout: int = TIMEOUT_NORMAL_MS,
) -> None:
    """Selecciona Sí/No dentro de la tarjeta de una pregunta concreta."""

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

    # Limitar la búsqueda a la tarjeta evita confundir las dos respuestas No.
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

    controles = bloque.locator(
        "label, button, [role='button']"
    ).filter(has_text=patron_texto_exacto(texto_opcion))

    if controles.count() == 0:
        texto_visible = bloque.get_by_text(
            texto_opcion,
            exact=True,
        ).first

        if texto_visible.count() > 0:
            controles = texto_visible.locator(
                "xpath=ancestor-or-self::*["
                "self::label or self::button or @role='button'"
                "][1]"
            )

    if controles.count() == 0:
        raise RuntimeError(
            f"No se encontró {texto_opcion!r} dentro de {titulo_bloque!r}."
        )

    if not activar_control_etiquetado(
        page,
        controles.first,
        timeout,
    ):
        raise RuntimeError(
            f"No fue posible confirmar {texto_opcion!r} en "
            f"{titulo_bloque!r}."
        )

    print(f"{titulo_bloque}: {texto_opcion}")


def completar_cierre(
    page: Page,
    fotos: Sequence[str],
    apr_participa: bool,
    equipo_alza_hombre: bool,
    observacion: str,
    dejar_campo_extra: bool,
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Completa opciones finales, observación y fotografías."""

    configuraciones = (
        (
            "APR participa en la actividad?",
            "Si" if apr_participa else "No",
        ),
        (
            "Apoyo de equipo alza hombre?",
            "Si" if equipo_alza_hombre else "No",
        ),
    )
    errores: list[str] = []

    for pregunta, opcion in configuraciones:
        try:
            seleccionar_opcion_bloque(page, pregunta, opcion)
        except Exception as error:
            errores.append(f"{pregunta}: {error}")

    if errores:
        print("\nNo pude completar automáticamente estas opciones:")

        for error in errores:
            print(f"  - {error}")

        esperar_confirmacion_manual(
            "Selecciona manualmente las opciones pendientes en el portal.",
            confirmar_manual,
        )

    page.get_by_role(
        "textbox",
        name="Observaciones generales:",
    ).fill(observacion.strip() or OBSERVACION_DEFAULT)
    subir_fotos(page, fotos, dejar_campo_extra)

    if dejar_campo_extra:
        print("\nLas ART fueron cargadas automáticamente.")
        print("Agrega manualmente la fotografía del mantenimiento.")
        print("La mantención aún no se guardará.")
    else:
        print(
            f"\nLas {len(fotos)} fotografías fueron cargadas "
            "automáticamente."
        )
        print("El formulario está listo para guardarse.")


def crear_mantenimiento(
    page: Page,
    solicitud: SolicitudMantenimiento,
    modo_navegacion: str = "completa",
    confirmar_manual: ConfirmacionManual | None = None,
) -> None:
    """Ejecuta el formulario completo usando datos previamente validados."""

    if modo_navegacion == "completa":
        ir_a_tareas(page)
        abrir_nueva_tarea(page)
    elif modo_navegacion == "solo_nueva":
        abrir_nueva_tarea(page)
    elif modo_navegacion == "ninguna":
        print("Usando el formulario de Nueva tarea ya abierto...")
    else:
        raise ValueError(
            f"Modo de navegación no válido: {modo_navegacion}"
        )

    crear_tarea_base(
        page,
        solicitud.area_busqueda,
        solicitud.area,
        solicitud.ubicacion_portal,
        confirmar_manual,
    )
    crear_actividad(
        page,
        solicitud.hora_inicio,
        solicitud.hora_fin,
        solicitud.participantes,
        confirmar_manual,
    )
    completar_estado_general(page)
    completar_conexiones(page, solicitud.camara_ip)
    completar_cierre(
        page,
        solicitud.fotos,
        solicitud.apr_participa,
        solicitud.equipo_alza_hombre,
        solicitud.observacion,
        solicitud.dejar_campo_extra,
        confirmar_manual,
    )

    if solicitud.dejar_campo_extra:
        print(
            "\nFormulario preparado para revisión."
            "\nLa mantención NO ha sido guardada ni finalizada."
            "\nRevisa participantes, opciones y fotografías en el portal."
        )
    else:
        print(
            "\nFormulario completo."
            "\nCCTVFlow guardará la mantención y descargará el PDF."
        )
