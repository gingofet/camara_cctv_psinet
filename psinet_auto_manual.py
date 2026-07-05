from datetime import datetime, timedelta

from psinet.login import login_psinet
from psinet.navegador import iniciar_navegador
from psinet.tareas import crear_mantenimiento


FORMATO_HORA = "%H:%M"
DURACION_MINUTOS = 10


def sumar_minutos(hora: str, minutos: int) -> str:
    base = datetime.strptime(hora, FORMATO_HORA)
    nueva = base + timedelta(minutes=minutos)
    return nueva.strftime(FORMATO_HORA)


def pedir_hora_inicio():
    hora = input("Hora inicial del primer mantenimiento (ej: 17:00): ").strip()

    if not hora:
        hora = "17:00"

    datetime.strptime(hora, FORMATO_HORA)
    return hora


def pedir_area():
    while True:
        area = input("Nombre exacto de la cámara/área en PSINet ('salir' para terminar): ").strip()

        if area.lower() in {"salir", "exit", "q"}:
            return None

        if area:
            return area

        print("Debes escribir un nombre de cámara o 'salir'.")


def crear_evidencia_manual(area: str, hora_inicio: str):
    hora_fin = sumar_minutos(hora_inicio, DURACION_MINUTOS)

    return {
        "area": area,
        "area_busqueda": area,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "fotos": [],
    }


def main():
    hora_actual = pedir_hora_inicio()
    modo_navegacion = "completa"

    with iniciar_navegador(headless=False) as page:
        login_psinet(page)

        while True:
            area = pedir_area()

            if area is None:
                print("Proceso finalizado.")
                break

            evidencia = crear_evidencia_manual(area, hora_actual)

            print(
                f"Cargando mantenimiento: {area} "
                f"({evidencia['hora_inicio']} - {evidencia['hora_fin']})"
            )

            crear_mantenimiento(page, evidencia, modo_navegacion=modo_navegacion)

            input(
                "Sube las fotos y guarda manualmente. "
                "Cuando PSINet vuelva al listado de tareas, presiona Enter..."
            )

            hora_actual = evidencia["hora_fin"]
            modo_navegacion = "solo_nueva"


if __name__ == "__main__":
    main()