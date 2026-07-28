# CCTVFlow — Plan de trabajo

Última actualización: 24 de julio de 2026.

## Prioridad inmediata

- [ ] Validar en PSINet el nuevo selector dinámico del bloque **CONEXIONES** en
  DRT.
- [ ] Ejecutar una mantención DRT completa: tarea, actividad, checklist, ART,
  fotografía de mantención, guardado y descarga del PDF.
- [ ] Revisar que una segunda cámara pueda procesarse en la misma sesión sin
  perder el estado de navegación.
- [ ] Confirmar que la ubicación de PSINet se llama exactamente `DRT`.
- [ ] Revisar en PSINet los nombres ambiguos o posiblemente mal escritos del
  catálogo DRT, sin corregirlos hasta confirmar el texto original.
- [ ] Evitar tareas duplicadas cuando una ejecución se interrumpe después de
  presionar **Ingresar**.

## Integración del flujo

- [ ] Unir `automatizacion.menu_psinet` con el ejecutor Playwright.
- [ ] Permitir seleccionar división, sector y varias cámaras desde un único
  menú.
- [ ] Entregar automáticamente al ejecutor los horarios calculados por el menú.
- [ ] Conectar `lector_fotos.py` y `plan_ejecucion.json` con el motor principal.
- [x] Asociar y subir automáticamente las fotografías de cada mantención
  importadas desde la GUI.
- [ ] Validar en PSINet un lote completo con ART diferentes por área y limpieza
  posterior de las imágenes.
- [ ] Mantener el modo manual como respaldo técnico estable.

## Robustez y calidad

- [ ] Reemplazar selectores absolutos o IDs variables restantes por selectores
  basados en roles, etiquetas o texto.
- [ ] Agregar reintentos controlados para cargas lentas y búsquedas de cámaras.
- [ ] Capturar errores por etapa y mostrar un resumen claro al usuario.
- [ ] Guardar un estado de ejecución que permita reanudar un trabajo
  interrumpido.
- [ ] Agregar registros de ejecución sin incluir credenciales ni información
  sensible.
- [ ] Crear pruebas automatizadas para horarios, normalización, catálogos y
  generación de evidencias.
- [ ] Validar JSON y sintaxis automáticamente antes de cada publicación.
- [ ] Revisar y reducir dependencias que todavía no utiliza el flujo principal.

## Experiencia de usuario

- [ ] Validar entradas de hora y mostrar mensajes amigables ante formatos
  incorrectos.
- [ ] Permitir volver atrás o cancelar antes de crear una tarea.
- [ ] Mostrar una confirmación final con división, cámara, horario y
  participantes.
- [ ] Mostrar progreso por etapa durante la automatización.
- [ ] Preparar una interfaz gráfica para el agente local.
- [ ] Empaquetar el agente para Linux y Windows.

## Arquitectura híbrida

- [ ] Crear la estructura inicial de `server/` y `agent/`.
- [ ] Implementar modelos de usuario, dispositivo y trabajo.
- [ ] Agregar autenticación, roles y dispositivos autorizados.
- [ ] Crear endpoints para asignar trabajos y reportar estados.
- [ ] Migrar gradualmente `psinet_auto_manual.py` a `agent/runner.py` sin perder
  el respaldo funcional.
- [ ] Mantener las credenciales PSINet en cada equipo local.
- [ ] Reemplazar `.env` por un almacén seguro de credenciales en una etapa
  posterior.
- [ ] Registrar y almacenar los PDFs en el servidor central.

## Aplicación Android

- [ ] Diseñar el flujo de captura de evidencias.
- [ ] Seleccionar división, sector y cámara desde la aplicación.
- [ ] Generar automáticamente nombres con el formato acordado.
- [ ] Permitir registrar cámaras nuevas para revisión.
- [ ] Sincronizar las fotografías con CCTVFlow.

## Completado

- [x] Arquitectura modular con `psinet/`, `utils/` y `automatizacion/`.
- [x] Inicio de Chromium e inicio de sesión en PSINet.
- [x] Creación automática de la tarea base.
- [x] Creación y configuración automática de la actividad.
- [x] Horarios consecutivos de 10 minutos.
- [x] Selección automática de participantes configurados.
- [x] Configuración de APR y equipo alza hombre.
- [x] Automatización del bloque Estado General.
- [x] Automatización inicial del bloque Conexiones.
- [x] Carga automática de `ART` y `ART_atras`.
- [x] Campo adicional para la fotografía manual de la mantención.
- [x] Guardado de la actividad y descarga del PDF.
- [x] Conservación del nombre original del PDF.
- [x] Menú de planificación por sector o búsqueda manual.
- [x] Lectura y asociación de fotografías por nombre de cámara.
- [x] Generación de `evidencias.json` y `plan_ejecucion.json`.
- [x] Configuración centralizada de valores operacionales.
- [x] Selección dinámica entre `DCH-SUBTE` y `DRT`.
- [x] Catálogo DRT con 156 cámaras distribuidas en 11 áreas.
- [x] README actualizado con instalación, uso y estado real del proyecto.
