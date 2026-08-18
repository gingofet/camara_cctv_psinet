from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from cctvflow.server_client import (
    CCTVFlowServerClient,
    ServerClientError,
    build_maintenance_event,
    maintenance_event_id,
)


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


class ServerClientTest(unittest.TestCase):
    def test_rechaza_servidor_sin_https(self) -> None:
        with self.assertRaisesRegex(ServerClientError, "HTTPS"):
            CCTVFlowServerClient(
                "http://servidor.invalid",
                "cctvflow_agent_token",
            )

    def test_heartbeat_envia_bearer_sin_exponerlo_en_payload(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["authorization"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data.decode())
            captured["timeout"] = timeout
            return _Response({"status": "ok"})

        client = CCTVFlowServerClient(
            "https://cctvflow.invalid",
            "cctvflow_agent_secreto",
            opener=opener,
        )
        self.assertEqual(client.heartbeat(), {"status": "ok"})
        self.assertEqual(
            captured["authorization"],
            "Bearer cctvflow_agent_secreto",
        )
        self.assertNotIn("token", captured["payload"])

    def test_evento_de_checkpoint_es_idempotente(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint.json"
            path.write_text(
                json.dumps(
                    {
                        "creado": "2026-08-18T14:00:00-04:00",
                        "division": "DRT",
                    }
                ),
                encoding="utf-8",
            )
            first = maintenance_event_id("CAMARA 1", path)
            second = maintenance_event_id("CAMARA 1", path)
        self.assertEqual(first, second)

    def test_evento_envia_metadatos_pero_no_la_ruta_del_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "informe.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with path.open("wb") as handle:
                writer.write(handle)

            event = build_maintenance_event(
                event_id="3249c8b7-8d4b-4461-ab05-66f9de94e74c",
                camera_name="CAMARA 1",
                division="DRT",
                status="completed",
                photo_count=3,
                pdf=path,
            )

        payload = event.payload()
        self.assertEqual(payload["pdf_filename"], "informe.pdf")
        self.assertEqual(payload["pdf_page_count"], 1)
        self.assertEqual(len(payload["pdf_sha256"]), 64)
        self.assertNotIn(temporary, json.dumps(payload))

    def test_evento_conserva_fecha_historica_seleccionada(self) -> None:
        event = build_maintenance_event(
            event_id="3249c8b7-8d4b-4461-ab05-66f9de94e74c",
            maintenance_date="2026-07-28",
            camera_name="CAMARA 1",
            division="DRT",
            status="running",
            photo_count=3,
        )

        self.assertEqual(event.maintenance_date, "2026-07-28")


if __name__ == "__main__":
    unittest.main()
