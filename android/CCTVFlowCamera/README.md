# CCTVFlow Camera

Aplicación Android nativa para capturar evidencias fotográficas de cámaras CCTV
y guardarlas con nombres compatibles con el lector de evidencias de CCTVFlow.

## MVP 0.1

- Selección de división: `DCH-SUBTE` o `DRT`.
- Selección de turno: `A` o `B`.
- Selección de sector y cámara.
- Búsqueda de cámaras sin distinguir mayúsculas ni acentos.
- Vista previa y captura con CameraX.
- Correlativo independiente por cámara.
- Guardado en `Pictures/CCTVFlow`.
- Nombre compatible con CCTVFlow:

```text
20740_Cruce_Rampa_4_0001.jpg
```

La aplicación no solicita técnico ni plan matriz.

## Requisitos

- Android Studio compatible con Android Gradle Plugin 9.2.
- JDK 17.
- Android SDK 37 instalado.
- Teléfono o emulador con Android 10 (API 29) o superior.

## Abrir y ejecutar

1. Abre esta carpeta desde Android Studio.
2. Espera a que finalice la sincronización de Gradle.
3. Conecta el teléfono con depuración USB o crea un emulador.
4. Ejecuta la configuración `app`.
5. Acepta el permiso de cámara.

Las fotografías quedan disponibles por división y turno:

```text
Pictures/CCTVFlow/DRT/Turno_A/
```

Después puedes copiar esa carpeta hacia:

```text
camara_cctv_psinet/automatizacion/fotos/
```

y ejecutar el lector habitual.

## Arquitectura

```text
app/src/main/kotlin/cl/cctvflow/camera/
├── camera/     Integración CameraX
├── data/       Catálogos y correlativos locales
├── domain/     Modelos y generación de nombres
└── ui/         Estado, pantallas y tema Compose
```

Los catálogos se empaquetan en:

```text
app/src/main/assets/catalogos/
```

## Próximas iteraciones

- Revisar una foto antes de confirmarla.
- Registrar cámaras nuevas para revisión.
- Marcar cámaras temporalmente deshabilitadas.
- Exportar o sincronizar un lote de evidencias con el agente CCTVFlow.
- Importar catálogos actualizados sin recompilar la aplicación.
