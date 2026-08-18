"""Cliente HTTPS opcional para sincronizar solo metadatos con CCTVFlow Web."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid4, uuid5

from dotenv import load_dotenv
from pypdf import PdfReader

from cctvflow import __version__
from cctvflow.config import LOCAL_ENV_PATH
from cctvflow.models import normalizar_fecha_mantenimiento


class ServerClientError(RuntimeError):
    """Error controlado de configuración o comunicación con el servidor."""


@dataclass(frozen=True, slots=True)
class MaintenanceEvent:
    event_id: str
    maintenance_date: str
    camera_name: str
    division: str
    status: str
    pdf_filename: str | None = None
    pdf_sha256: str | None = None
    pdf_page_count: int | None = None
    photo_count: int | None = None
    detail: dict[str, Any] | None = None

    def payload(self) -> dict[str, Any]:
        data = asdict(self)
        data["detail"] = self.detail or {}
        return data


class CCTVFlowServerClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 12,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if not cleaned_url.startswith("https://"):
            raise ServerClientError("CCTVFLOW_SERVER_URL debe utilizar HTTPS.")
        cleaned_token = token.strip()
        if not cleaned_token.startswith("cctvflow_agent_"):
            raise ServerClientError("CCTVFLOW_AGENT_TOKEN no tiene un formato válido.")
        self.base_url = cleaned_url
        self.token = cleaned_token
        self.timeout = timeout
        self._opener = opener

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": f"CCTVFlow-Agent/{__version__}",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = f"HTTP {error.code}"
            try:
                error_payload = json.loads(error.read().decode("utf-8"))
                detail = str(error_payload.get("detail", detail))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
            raise ServerClientError(
                f"El servidor rechazó la solicitud: {detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise ServerClientError(
                "No fue posible comunicarse con CCTVFlow Web."
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ServerClientError(
                "El servidor devolvió una respuesta inválida."
            ) from error

        if not isinstance(result, dict):
            raise ServerClientError("El servidor devolvió una respuesta inesperada.")
        return result

    def heartbeat(self) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/agent/heartbeat",
            {
                "platform": platform.platform()[:120] or platform.system(),
                "agent_version": __version__,
            },
        )

    def report_maintenance(self, event: MaintenanceEvent) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/agent/maintenance-events",
            event.payload(),
        )


def configured_server_client() -> CCTVFlowServerClient | None:
    load_dotenv(dotenv_path=LOCAL_ENV_PATH)
    url = os.getenv("CCTVFLOW_SERVER_URL", "").strip()
    token = os.getenv("CCTVFLOW_AGENT_TOKEN", "").strip()
    if not url and not token:
        return None
    if not url or not token:
        raise ServerClientError(
            "Configura CCTVFLOW_SERVER_URL y CCTVFLOW_AGENT_TOKEN juntos."
        )
    return CCTVFlowServerClient(url, token)


def maintenance_event_id(
    camera_name: str,
    checkpoint_path: str | Path | None,
) -> str:
    if checkpoint_path:
        path = Path(checkpoint_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            seed = "|".join(
                (
                    str(data["creado"]),
                    str(data["division"]),
                    camera_name,
                )
            )
            return str(uuid5(NAMESPACE_URL, f"cctvflow:{seed}"))
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            pass
    return str(uuid4())


def _pdf_metadata(
    path: str | Path | None,
) -> tuple[str | None, str | None, int | None]:
    if path is None:
        return None, None, None
    pdf = Path(path)
    try:
        available = pdf.is_file() and pdf.stat().st_size > 0
    except OSError:
        available = False
    if not available:
        return pdf.name, None, None

    digest = hashlib.sha256()
    try:
        with pdf.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return pdf.name, None, None

    try:
        page_count = len(PdfReader(str(pdf)).pages)
    except Exception:
        page_count = None
    return pdf.name, digest.hexdigest(), page_count


def build_maintenance_event(
    *,
    event_id: str,
    maintenance_date: str | None = None,
    camera_name: str,
    division: str,
    status: str,
    photo_count: int,
    pdf: str | Path | None = None,
    detail: dict[str, Any] | None = None,
) -> MaintenanceEvent:
    filename, sha256, page_count = _pdf_metadata(pdf)
    return MaintenanceEvent(
        event_id=event_id,
        maintenance_date=normalizar_fecha_mantenimiento(
            maintenance_date or date.today().isoformat()
        ),
        camera_name=camera_name,
        division=division,
        status=status,
        pdf_filename=filename,
        pdf_sha256=sha256,
        pdf_page_count=page_count,
        photo_count=max(0, photo_count),
        detail=detail or {},
    )
