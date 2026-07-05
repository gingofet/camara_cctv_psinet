from psinet.login import login_psinet
from psinet.navegador import iniciar_navegador
from psinet.tareas import abrir_nueva_tarea, ir_a_tareas


def main():
    with iniciar_navegador(headless=False) as page:
        login_psinet(page)
        ir_a_tareas(page)
        abrir_nueva_tarea(page)

        input("Presiona Enter para cerrar...")


if __name__ == "__main__":
    main()