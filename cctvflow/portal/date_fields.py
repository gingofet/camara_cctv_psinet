"""Adaptación de la fecha de mantenimiento a controles del portal."""

from __future__ import annotations

from typing import Protocol

from cctvflow.models import normalizar_fecha_mantenimiento


SELECTOR_CAMPO_FECHA = ", ".join(
    (
        'input[type="date"]',
        'input[id*="fecha" i]',
        'input[name*="fecha" i]',
        'input[id^="date_" i]',
        'input[name^="date_" i]',
        'input[id*="_date" i]',
        'input[name*="_date" i]',
    )
)


class CampoFecha(Protocol):
    def get_attribute(self, nombre: str) -> str | None: ...

    def input_value(self) -> str: ...

    def is_visible(self) -> bool: ...

    def is_enabled(self) -> bool: ...

    def fill(self, valor: str) -> None: ...

    def evaluate(self, script: str, valor: str) -> object: ...

    def dispatch_event(self, nombre: str) -> None: ...


class ColeccionCamposFecha(Protocol):
    def count(self) -> int: ...

    def nth(self, indice: int) -> CampoFecha: ...


class FormularioFecha(Protocol):
    def locator(self, selector: str) -> ColeccionCamposFecha: ...


def _valor_fecha_para_campo(
    campo: CampoFecha,
    fecha_iso: str,
) -> str:
    """Adapta la fecha al formato que muestra un input del portal."""

    tipo = (campo.get_attribute("type") or "").casefold()

    if tipo == "date":
        return fecha_iso

    referencia = " ".join(
        (
            campo.get_attribute("placeholder") or "",
            campo.input_value() or "",
        )
    ).casefold()
    anio, mes, dia = fecha_iso.split("-")

    if "/" in referencia:
        return f"{dia}/{mes}/{anio}"

    if referencia.strip().startswith(("yyyy", "aaaa", anio)):
        return fecha_iso

    return f"{dia}-{mes}-{anio}"


def _valor_corresponde_a_fecha(valor: str, fecha_iso: str) -> bool:
    anio, mes, dia = fecha_iso.split("-")
    return valor.strip() in {
        fecha_iso,
        f"{dia}/{mes}/{anio}",
        f"{dia}-{mes}-{anio}",
    }


def establecer_fecha_mantenimiento(
    formulario: FormularioFecha,
    fecha_mantenimiento: str,
) -> int:
    """Completa todos los campos de fecha visibles de un formulario."""

    fecha_iso = normalizar_fecha_mantenimiento(fecha_mantenimiento)
    campos = formulario.locator(SELECTOR_CAMPO_FECHA)
    actualizados = 0

    for indice in range(campos.count()):
        campo = campos.nth(indice)

        if not campo.is_visible() or not campo.is_enabled():
            continue

        valor = _valor_fecha_para_campo(campo, fecha_iso)

        try:
            campo.fill(valor)
        except Exception:
            # Algunos calendarios dejan el input como readonly. El setter
            # nativo mantiene los eventos que la aplicación espera observar.
            campo.evaluate(
                """(elemento, valorNuevo) => {
                    const descriptor = Object.getOwnPropertyDescriptor(
                        HTMLInputElement.prototype,
                        "value"
                    );
                    descriptor.set.call(elemento, valorNuevo);
                    elemento.dispatchEvent(new Event("input", {bubbles: true}));
                    elemento.dispatchEvent(new Event("change", {bubbles: true}));
                }""",
                valor,
            )

        campo.dispatch_event("change")

        if _valor_corresponde_a_fecha(campo.input_value(), fecha_iso):
            actualizados += 1

    if actualizados:
        dia, mes, anio = fecha_iso.split("-")[::-1]
        print(
            f"Fecha de mantenimiento: {dia}-{mes}-{anio} "
            f"({actualizados} campo(s) confirmado(s))"
        )

    return actualizados
