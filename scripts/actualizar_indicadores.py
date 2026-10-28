import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def consultar(ruta):
    cabeceras = {"Accept": "application/vnd.github+json", "User-Agent": "perfil-em4nu3i69dll"}
    if os.environ.get("GITHUB_TOKEN"):
        cabeceras["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request("https://api.github.com/" + ruta, headers=cabeceras), timeout=25) as respuesta:
        return json.load(respuesta)


def indicador(nombre, valor, destino):
    destino.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="150" height="26" role="img" '
        f'aria-label="{nombre} {valor}"><title>{nombre} {valor}</title>'
        '<rect x=".5" y=".5" width="149" height="25" rx="5" fill="#fff" stroke="#d1d9e0"/>'
        '<g font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="#1f2328">'
        f'<text x="12" y="17">{nombre}</text><text x="138" y="17" text-anchor="end" '
        f'font-weight="600" fill="#0969da">{valor}</text></g></svg>\n', encoding="utf-8"
    )


def actualizar():
    usuario = "em4nu3i69dll"
    perfil = consultar("users/" + usuario)
    estrellas = 0
    pagina = 1
    while True:
        repositorios = consultar(f"users/{usuario}/repos?type=owner&per_page=100&page={pagina}")
        estrellas += sum(repo["stargazers_count"] for repo in repositorios)
        if len(repositorios) < 100:
            break
        pagina += 1
    carpeta = Path(__file__).resolve().parents[1] / "assets"
    indicador("Seguidores", perfil["followers"], carpeta / "seguidores.svg")
    indicador("Estrellas", estrellas, carpeta / "estrellas.svg")
    print(f"Seguidores {perfil['followers']} · Estrellas {estrellas}")


if __name__ == "__main__":
    actualizar()
