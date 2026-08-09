# Revisión técnica de CCTVFlow

Fecha: 28 de julio de 2026.

## Resultado

La base funcional era correcta y ya incluía protecciones importantes:
checkpoint atómico, validación del PDF, conservación de evidencias ante fallos
y ejecución de Playwright fuera del hilo de la GUI. El problema principal no
era la orientación a objetos, sino el crecimiento incremental: coexistían
prototipos, dos flujos de ejecución, utilidades duplicadas y un módulo de más de
mil líneas.

## Hallazgos corregidos

| Prioridad | Hallazgo | Corrección |
| --- | --- | --- |
| Alta | La identidad externa aparecía en interfaz, módulos, variables y documentación. | Se reemplazó por la marca única CCTVFlow y nombres genéricos del portal. |
| Alta | Credenciales con nombres ligados a un proveedor. | Se migraron a variables `CCTVFLOW_PORTAL_*`. |
| Alta | Datos de mantención viajaban como diccionario sin contrato. | Se agregó `SolicitudMantenimiento`, inmutable y validada. |
| Alta | Un archivo concentraba navegación, participantes, checklist, fotos y cierre. | Se dividió en módulos pequeños dentro de `cctvflow.portal`. |
| Media | Existían scripts antiguos y dos utilidades JSON equivalentes. | Se retiraron los prototipos y duplicados. |
| Media | Catálogos y recursos estaban mezclados con scripts. | Se movieron a `cctvflow/resources`. |
| Media | Dependencias transitivas estaban fijadas manualmente. | `requirements.txt` conserva solo dependencias directas. |
| Media | No existía una barrera contra la reaparición de la marca anterior. | Se añadió una prueba automática de identidad. |
| Baja | Las rutas de salida se calculaban desde distintos módulos. | Se centralizaron en `cctvflow.config`. |

## Decisiones

- No se forzó una clase para cada módulo. Las funciones puras siguen siendo más
  claras para reglas, selectores y validaciones.
- Se usan clases donde existe estado real: modelos, ventana y ejecutor del lote.
- Los comentarios explican decisiones o fragilidad del portal; no repiten el
  nombre de una función o una línea evidente.
- Se mantiene el ejecutor visible y recuperable. No se automatiza el borrado de
  registros ya guardados.

## Riesgos restantes

- `cctvflow/ui/window.py` continúa siendo grande. Su división por pestañas debe
  hacerse con pruebas visuales en un entorno que disponga de PySide6.
- Algunos selectores dependen del texto y estructura actuales del portal.
- La validación por páginas confirma el contenido del PDF, pero no identifica
  cuál fotografía falta.
- El estado `en_proceso` es deliberadamente conservador y no se repite al
  reanudar para evitar duplicados.

## Criterio de comentarios

Se agregan comentarios cuando responden “por qué”:

- respaldos para controles Bootstrap ocultos;
- selector dinámico del acordeón;
- espera y verificación doble de fotografías;
- conservación de archivos y checkpoint.

No se comentan asignaciones obvias ni llamadas cuyo nombre ya describe la
acción.
