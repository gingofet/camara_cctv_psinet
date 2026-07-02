#CCTVFlow

Automatización del flujo de trabajo de mantenciones preventivas de cámaras CCTV para minería subterránea mediante integración con la plataforma PSINet.

Objetivo

Reducir el tiempo dedicado a tareas administrativas repetitivas durante la gestión de mantenciones preventivas, permitiendo que el personal se enfoque en las actividades de terreno.

Funcionalidades

Actualmente el proyecto permite:

Administración de sectores y cámaras.
Generación automática de planes de ejecución.
Organización automática de evidencias fotográficas.
Asociación fotografía ↔ cámara.
Preparación automática de información para PSINet.
Arquitectura
App Android
        │
        ▼
Captura fotografías
        │
        ▼
runtime/fotos
        │
        ▼
lector_fotos.py
        │
        ▼
runtime/evidencias.json
        │
        ▼
generar_plan_desde_fotos.py
        │
        ▼
runtime/plan_ejecucion.json
        │
        ▼
psinet_auto.py
        │
        ▼
Suite PSINet
Estructura del proyecto
camara_cctv_psinet/

│
├── automatizacion/
│   ├── data/
│   ├── psinet/
│   ├── utils/
│   ├── runtime/
│   ├── menu_psinet.py
│   ├── lector_fotos.py
│   ├── generar_plan.py
│   ├── generar_plan_desde_fotos.py
│   └── psinet_auto.py
│
├── .vscode/
│
├── requirements.txt
│
└── README.md
Instalación
git clone ...
pip install -r requirements.txt
playwright install

Crear

.env
Roadmap
v0.1

✔ Menú por sectores

✔ Horarios automáticos

✔ JSON de ejecución

v0.2

✔ Asociación automática de fotografías

✔ Detección de evidencias

v0.3

Automatización PSINet

Creación automática de tareas

v0.4

Subida automática de fotografías

Descarga automática de PDF

v1.0

Aplicación Android

Sincronización automática

Flujo completamente automatizado

Tecnologías
Python
Playwright
VS Code
Git
GitHub
Licencia

Proyecto privado.