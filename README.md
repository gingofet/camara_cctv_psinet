# CCTVFlow

Automatización asistida de mantenciones preventivas de cámaras CCTV.

CCTVFlow prepara y ejecuta lotes de mantenimiento en un portal web, completa
los checklist, adjunta evidencias, descarga el informe PDF y conserva un punto
de control para continuar después de una interrupción.

> CCTVFlow es un proyecto independiente. No es un producto oficial, patrocinado
> ni propiedad del proveedor del portal o de las empresas donde se utilice.

## Funciones principales

- Selección por división, sector o cámara.
- Planificación automática de intervalos consecutivos.
- Procesamiento de carpetas exportadas por CCTVFlow Camera.
- Selección de participantes y opciones operacionales.
- Checklist diferenciado para cámaras IP y no IP.
- Carga verificada de ART y evidencias fotográficas.
- Descarga y validación del número de páginas del PDF.
- Continuación del lote cuando un informe sale incompleto.
- Checkpoint para reanudar únicamente cámaras que nunca comenzaron.
- Fecha de mantenimiento configurable para registrar trabajos históricos.
- Eliminación opcional de evidencias solo después de validar el informe.
- Conexión opcional con CCTVFlow Web mediante un token revocable por equipo.
- Sincronización exclusiva de estados y metadatos; nunca sube fotos ni PDF.

## Arquitectura

El código de la aplicación vive en un único paquete. Las carpetas principales
del repositorio quedan reducidas a la aplicación, sus pruebas y los datos de
ejecución:

```text
CCTVFlow/
├── cctvflow/
│   ├── portal/              # Selectores y flujo del portal web
│   ├── resources/
│   │   ├── art/             # ART.jpg y ART_atras.jpg (solo locales)
│   │   └── catalogs/        # Catálogos por división
│   ├── ui/                  # Ventana principal y ejecutor en segundo plano
│   ├── checkpoint.py        # Recuperación segura de lotes
│   ├── config.py            # Configuración y rutas
│   ├── models.py            # Modelos inmutables
│   ├── photo_batch.py       # Detección de evidencias
│   └── planning.py          # Búsqueda y horarios
├── tests/
├── runtime/
├── downloads/
├── pyproject.toml
└── requirements.txt
```

La GUI no contiene selectores del portal. El ejecutor coordina el lote y el
paquete `cctvflow.portal` concentra todos los detalles de Playwright. Los datos
que cruzan ambas capas usan modelos inmutables en lugar de diccionarios sin
tipo.

## Instalación

Requiere Python 3.12 o superior.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
playwright install chromium
```

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
playwright install chromium
```

## Configuración local

Copia `.env.example` como `.env` y completa los datos del portal:

```dotenv
CCTVFLOW_PORTAL_URL=https://direccion-del-portal/login
CCTVFLOW_PORTAL_USER=usuario@ejemplo.cl
CCTVFLOW_PORTAL_PASSWORD=contraseña
CCTVFLOW_SERVER_URL=https://cctvflow-mindcel.duckdns.org
CCTVFLOW_AGENT_TOKEN=cctvflow_agent_TOKEN_ENTREGADO_POR_EL_SERVIDOR
```

El archivo `.env` está excluido de Git. No publiques credenciales, fotografías
operacionales ni informes.

Las variables del servidor son opcionales. Si no están configuradas, CCTVFlow
continúa funcionando en modo exclusivamente local. En el ejecutable de
Windows, el archivo se guarda en:

```text
%LOCALAPPDATA%\CCTVFlow\.env
```

El agente solo informa identificador de evento, fecha, cámara, división,
estado, cantidad de fotos y metadatos del PDF (nombre, hash y páginas). Las
credenciales del portal, fotos, rutas locales y contenido del PDF no se envían.

Guarda las fotografías permanentes del ART en:

```text
cctvflow/resources/art/ART.jpg
cctvflow/resources/art/ART_atras.jpg
```

## Ejecución

```bash
python -m cctvflow
```

El comando histórico continúa disponible durante la transición:

```bash
python -m cctvflow_gui
```

La fecha de mantenimiento comienza en el día actual. Para cargar trabajo
atrasado, selecciónala en el calendario antes de ejecutar. CCTVFlow escribe la
misma fecha en todas las cámaras del lote, la envía como fecha de auditoría al
servidor y la conserva si luego se usa **Reanudar pendientes**. Por seguridad,
la interfaz no admite fechas futuras.

## Fotografías

CCTVFlow Camera genera archivos con el formato:

```text
<nombre_camara>_<correlativo>.jpg
```

Ejemplo:

```text
RTAPIP001-Vista_oruga_1_0001.jpg
```

La GUI analiza una carpeta de forma recursiva y relaciona cada imagen con el
catálogo de la división seleccionada. Cada mantención admite hasta 13
evidencias porque dos espacios se reservan para el ART.

## Recuperación y seguridad

El estado del lote se guarda atómicamente en:

```text
runtime/ejecucion_pendiente.json
```

- Un PDF incompleto se marca para revisión y no detiene las cámaras siguientes.
- Las imágenes relacionadas se conservan.
- Una ejecución reanudada omite registros completos o de estado incierto.
- Los archivos solo se eliminan después de validar el PDF.
- No se borran automáticamente registros ya guardados en el portal.

## Pruebas

```bash
python -m unittest discover -s tests -v
python -m compileall -q cctvflow tests cctvflow_gui.py
```

## Paquete standalone para Windows

El paquete se construye de forma nativa en Windows e incluye Chromium. No
contiene `.env`, tokens, fotografías, ART ni informes operacionales.

```powershell
.\packaging\windows\build.ps1
```

El resultado queda en:

```text
dist\CCTVFlow-Windows-x64.zip
```

También puede iniciarse manualmente el workflow `Build Windows agent` desde
GitHub Actions. El ejecutable principal queda dentro de la carpeta `CCTVFlow`
del ZIP.

La prueba de identidad también evita que la antigua marca externa reaparezca
en nombres de archivo, código, configuración o documentación.

## Autoría

Copyright © 2026 Louis Rivera Ovalle. Todos los derechos reservados.

Consulta [CODE_REVIEW.md](CODE_REVIEW.md) para conocer las decisiones de la
reestructuración y [ROADMAP.md](ROADMAP.md) para los pendientes.
