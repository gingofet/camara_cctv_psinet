from psinet.login import login_psinet
from psinet.navegador import iniciar_navegador


def main():
    with iniciar_navegador(headless=False) as page:
        login_psinet(page)
        input("Presiona Enter para cerrar...")


if __name__ == "__main__":
    main()