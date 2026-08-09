# Roadmap de CCTVFlow

## Validación en terreno

- Validar un lote completo en DRT con limpieza automática activada.
- Confirmar nombres ambiguos del catálogo y corregirlos en el JSON de origen.
- Verificar el selector sin etiqueta estable usado al crear la actividad.
- Registrar ejemplos reales de formularios que cambien su estructura.

## Robustez

- Detectar una señal del servidor que confirme el procesamiento de cada imagen.
- Añadir una captura y HTML de diagnóstico al fallar un selector.
- Diferenciar en el checkpoint entre tarea creada, formulario completo y
  registro guardado.
- Añadir una opción manual para marcar como resuelta una revisión.

## Interfaz

- Separar gradualmente la ventana principal en componentes por pestaña.
- Mostrar el detalle de informes incompletos dentro de la aplicación.
- Incorporar una pantalla de configuración de credenciales sin guardarlas en
  el repositorio.

## Distribución

- Preparar un instalador para Fedora/Bazzite.
- Añadir versionado de catálogo compatible con CCTVFlow Camera.
- Evaluar firma de versiones y publicación de paquetes.
