"""
Proyecto: Cámara CCTV PSINet
Archivo: utils/horarios.py

Descripción:
Funciones para calcular horarios de mantenciones CCTV.
"""

from datetime import datetime, timedelta


def calcular_horarios(areas, hora_inicio, duracion_minutos):
    """Calcula inicio y fin secuencial para cada cámara."""
    inicio = datetime.strptime(hora_inicio, "%H:%M")
    resultado = []

    for area in areas:
        fin = inicio + timedelta(minutes=duracion_minutos)

        resultado.append({
            "area": area,
            "inicio": inicio.strftime("%H:%M"),
            "fin": fin.strftime("%H:%M"),
        })

        inicio = fin

    return resultado
