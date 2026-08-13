from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cctvflow.checkpoint import (
    VERSION_CHECKPOINT,
    cargar_checkpoint,
)
from cctvflow.portal.date_fields import establecer_fecha_mantenimiento


class _CampoFechaFalso:
    def __init__(
        self,
        *,
        tipo: str = "text",
        placeholder: str = "",
        valor: str = "",
        visible: bool = True,
        habilitado: bool = True,
        solo_lectura: bool = False,
    ) -> None:
        self.atributos = {
            "type": tipo,
            "placeholder": placeholder,
        }
        self.valor = valor
        self.visible = visible
        self.habilitado = habilitado
        self.solo_lectura = solo_lectura
        self.eventos: list[str] = []

    def get_attribute(self, nombre: str) -> str | None:
        return self.atributos.get(nombre)

    def input_value(self) -> str:
        return self.valor

    def is_visible(self) -> bool:
        return self.visible

    def is_enabled(self) -> bool:
        return self.habilitado

    def fill(self, valor: str) -> None:
        if self.solo_lectura:
            raise RuntimeError("readonly")
        self.valor = valor

    def evaluate(self, _script: str, valor: str) -> None:
        self.valor = valor

    def dispatch_event(self, nombre: str) -> None:
        self.eventos.append(nombre)


class _ColeccionCamposFalsa:
    def __init__(self, campos: list[_CampoFechaFalso]) -> None:
        self.campos = campos

    def count(self) -> int:
        return len(self.campos)

    def nth(self, indice: int) -> _CampoFechaFalso:
        return self.campos[indice]


class _FormularioFalso:
    def __init__(self, campos: list[_CampoFechaFalso]) -> None:
        self.campos = campos
        self.selector_usado = ""

    def locator(self, selector: str) -> _ColeccionCamposFalsa:
        self.selector_usado = selector
        return _ColeccionCamposFalsa(self.campos)


class CamposFechaPortalTest(unittest.TestCase):
    def test_adapta_fecha_a_inputs_html_y_localizados(self) -> None:
        campo_html = _CampoFechaFalso(tipo="date")
        campo_local = _CampoFechaFalso(
            placeholder="dd/mm/aaaa",
            solo_lectura=True,
        )
        campo_oculto = _CampoFechaFalso(tipo="date", visible=False)
        formulario = _FormularioFalso(
            [campo_html, campo_local, campo_oculto]
        )

        cantidad = establecer_fecha_mantenimiento(
            formulario,
            "2026-07-28",
        )

        self.assertEqual(cantidad, 2)
        self.assertEqual(campo_html.valor, "2026-07-28")
        self.assertEqual(campo_local.valor, "28/07/2026")
        self.assertEqual(campo_oculto.valor, "")
        self.assertIn('input[type="date"]', formulario.selector_usado)
        self.assertIn("change", campo_html.eventos)


class CompatibilidadCheckpointFechaTest(unittest.TestCase):
    def test_checkpoint_v1_recupera_fecha_de_creacion(self) -> None:
        datos = {
            "version": 1,
            "creado": "2026-07-28T22:31:45-04:00",
            "actualizado": "2026-07-28T22:31:45-04:00",
            "division": "DRT",
            "configuracion": {},
            "plan": [],
            "fotos_por_camara": {},
            "fotos_art_por_sector": {},
            "resultados": {},
        }

        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "checkpoint.json"
            ruta.write_text(json.dumps(datos), encoding="utf-8")
            recuperado = cargar_checkpoint(ruta)

        self.assertIsNotNone(recuperado)
        self.assertEqual(recuperado["version"], VERSION_CHECKPOINT)
        self.assertEqual(
            recuperado["configuracion"]["fecha_mantenimiento"],
            "2026-07-28",
        )


if __name__ == "__main__":
    unittest.main()
