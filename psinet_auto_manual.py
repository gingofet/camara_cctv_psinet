from datetime import datetime, timedelta
from pathlib import Path
from psinet.descargas import descargar_pdf_abierto
from psinet.login import login_psinet
from psinet.navegador import iniciar_navegador
from psinet.tareas import crear_mantenimiento


FORMATO_HORA = "%H:%M"
DURACION_MINUTOS = 10
# Directorio raíz del proyecto.
DIRECTORIO_PROYECTO = Path(__file__).resolve().parent

# Carpeta donde se almacenan las fotografías permanentes de la ART.
DIRECTORIO_ART = (
    DIRECTORIO_PROYECTO
    / "automatizacion"
    / "data"
    / "art"
)

# Nombres esperados, sin extensión.
NOMBRES_FOTOS_ART = [
    "ART",
    "ART_atras",
]

EXTENSIONES_IMAGEN_PERMITIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
}
# Participantes que se seleccionarán automáticamente en cada actividad.
# Los nombres deben coincidir exactamente con los mostrados por PSINet.
PARTICIPANTES_DEFAULT = [
    "Louis Rivera",
    "Emgelbert Pizarro",
]

# Configuración predeterminada del cierre.
APR_PARTICIPA_DEFAULT = False
EQUIPO_ALZA_HOMBRE_DEFAULT = False


def sumar_minutos(hora: str, minutos: int) -> str:
    """Suma minutos a una hora expresada en formato HH:MM."""

    base = datetime.strptime(hora, FORMATO_HORA)
    nueva = base + timedelta(minutes=minutos)

    return nueva.strftime(FORMATO_HORA)


def pedir_hora_inicio() -> str:
    """Solicita la hora del primer mantenimiento."""

    hora = input(
        "Hora inicial del primer mantenimiento (ej: 17:00): "
    ).strip()

    if not hora:
        hora = "17:00"

    # Valida que la hora tenga un formato correcto.
    datetime.strptime(hora, FORMATO_HORA)

    return hora


def pedir_area() -> str | None:
    """Solicita el nombre de la cámara o finaliza el ciclo."""

    while True:
        area = input(
            "Nombre exacto de la cámara/área en PSINet "
            "('salir' para terminar): "
        ).strip()

        if area.lower() in {"salir", "exit", "q"}:
            return None

        if area:
            return area

        print("Debes escribir un nombre de cámara o 'salir'.")

def buscar_imagen_por_nombre(
    directorio: Path,
    nombre: str,
) -> Path:
    """
    Busca una imagen por su nombre base, sin exigir una extensión específica.

    Ejemplos válidos:
        ART.jpg
        ART.jpeg
        ART.png
    """

    if not directorio.exists():
        raise FileNotFoundError(
            f"No existe la carpeta de fotografías ART: {directorio}"
        )

    for archivo in directorio.iterdir():
        if not archivo.is_file():
            continue

        if archivo.suffix.lower() not in EXTENSIONES_IMAGEN_PERMITIDAS:
            continue

        if archivo.stem.casefold() == nombre.casefold():
            return archivo.resolve()

    raise FileNotFoundError(
        f"No se encontró la fotografía '{nombre}' en: {directorio}"
    )


def obtener_fotos_art() -> list[str]:
    """
    Obtiene las fotografías delantera y trasera de la ART.

    Mantiene el siguiente orden:
        1. ART
        2. ART_atras
    """

    fotos_art: list[str] = []

    for nombre in NOMBRES_FOTOS_ART:
        ruta = buscar_imagen_por_nombre(
            directorio=DIRECTORIO_ART,
            nombre=nombre,
        )

        fotos_art.append(str(ruta))

    return fotos_art

def crear_evidencia_manual(
    area: str,
    hora_inicio: str,
) -> dict:
    """Construye la evidencia utilizada por crear_mantenimiento()."""

    hora_fin = sumar_minutos(
        hora=hora_inicio,
        minutos=DURACION_MINUTOS,
    )

    return {
        "area": area,
        "area_busqueda": area,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,

        # Participantes de la actividad.
        "participantes": PARTICIPANTES_DEFAULT.copy(),

        # Opciones del cierre.
        "apr_participa": APR_PARTICIPA_DEFAULT,
        "equipo_alza_hombre": EQUIPO_ALZA_HOMBRE_DEFAULT,

        # Las fotografías siguen cargándose manualmente durante las pruebas.
        "fotos": obtener_fotos_art(),
    }


def main() -> None:
    """Ejecuta mantenciones manuales consecutivas usando la misma sesión."""

    hora_actual = pedir_hora_inicio()
    modo_navegacion = "completa"

    with iniciar_navegador(headless=False) as page:
        login_psinet(page)

        while True:
            area = pedir_area()

            if area is None:
                print("Proceso finalizado.")
                break

            evidencia = crear_evidencia_manual(
                area=area,
                hora_inicio=hora_actual,
            )

            print()
            print(
                f"Cargando mantenimiento: {area} "
                f"({evidencia['hora_inicio']} - "
                f"{evidencia['hora_fin']})"
            )
            print(
                "Participantes configurados: "
                f"{', '.join(evidencia['participantes'])}"
            )

            crear_mantenimiento(
                page=page,
                evidencia=evidencia,
                modo_navegacion=modo_navegacion,
            )

            input(
                "\nSube manualmente la fotografía del mantenimiento.\n"
                "Cuando esté cargada, presiona Enter para que CCTVFlow guarde "
                "la mantención y descargue el PDF..."
            )

            with page.expect_popup(timeout=30_000) as popup_info:
                page.get_by_role(
                    "button",
                    name="Guardar",
                    exact=True,
                ).click()

            pagina_pdf = popup_info.value
            pagina_pdf.wait_for_load_state("domcontentloaded")

            descargar_pdf_abierto(page)

            # La hora final de esta cámara pasa a ser la hora inicial
            # de la siguiente.
            hora_actual = evidencia["hora_fin"]

            # Después de la primera mantención ya estamos dentro del módulo
            # de tareas, por lo que solo se abre una tarea nueva.
            modo_navegacion = "solo_nueva"


if __name__ == "__main__":
    main()