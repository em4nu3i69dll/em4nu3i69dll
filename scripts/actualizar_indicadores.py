import hashlib
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USUARIO = "em4nu3i69dll"


def consultar(ruta, datos=None):
    cabeceras = {"Accept": "application/vnd.github+json", "User-Agent": "perfil-" + USUARIO}
    if os.environ.get("GITHUB_TOKEN"):
        cabeceras["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    with urlopen(Request("https://api.github.com/" + ruta, data=cuerpo, headers=cabeceras), timeout=30) as respuesta:
        resultado = json.load(respuesta)
    if isinstance(resultado, dict) and resultado.get("errors"):
        raise RuntimeError("GitHub no pudo completar la consulta de contribuciones")
    return resultado


def lienzo(ancho, alto, titulo, contenido):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-label="{escape(titulo, quote=True)}">'
        f'<title>{escape(titulo)}</title><rect width="100%" height="100%" fill="#fff"/>'
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#1f2328}.azul{fill:#0969da}.suave{fill:#59636e}.valor{font-weight:600}</style>'
        + contenido + "</svg>\n"
    )


def texto(x, y, valor, clase="", tamano=13, ancla="start"):
    return f'<text x="{x}" y="{y}" class="{clase}" font-size="{tamano}" text-anchor="{ancla}">{escape(str(valor))}</text>'


def indicador(nombre, valor):
    return lienzo(150, 26, nombre, '<rect x=".5" y=".5" width="149" height="25" rx="5" fill="#fff" stroke="#d1d9e0"/>'
                  + texto(12, 17, nombre, tamano=12) + texto(138, 17, valor, "azul valor", 12, "end"))


def rachas(dias, hoy):
    ultimo = hoy if dias.get(hoy, 0) else hoy - timedelta(days=1)
    actual = 0
    while dias.get(ultimo - timedelta(days=actual), 0):
        actual += 1
    maxima = seguidos = 0
    anterior = None
    for dia in sorted(dias):
        if dias[dia]:
            seguidos = seguidos + 1 if anterior == dia - timedelta(days=1) else 1
            maxima = max(maxima, seguidos)
            anterior = dia
        else:
            seguidos = 0
            anterior = None
    return actual, maxima


def contribuciones(perfil, ahora):
    dias = {}
    commits = solicitudes = incidencias = 0
    creado = datetime.fromisoformat(perfil["created_at"].replace("Z", "+00:00"))
    for anio in range(creado.year, ahora.year + 1):
        inicio = max(creado, datetime(anio, 1, 1, tzinfo=timezone.utc))
        fin = min(ahora, datetime(anio, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        query = """query($usuario:String!,$inicio:DateTime!,$fin:DateTime!){
          user(login:$usuario){ contributionsCollection(from:$inicio,to:$fin){
            totalCommitContributions totalPullRequestContributions totalIssueContributions
            contributionCalendar { weeks { contributionDays { date contributionCount } } }
          }}
        }"""
        variables = {"usuario": USUARIO, "inicio": inicio.isoformat(), "fin": fin.isoformat()}
        datos = consultar("graphql", {"query": query, "variables": variables})["data"]["user"]["contributionsCollection"]
        for semana in datos["contributionCalendar"]["weeks"]:
            for dia in semana["contributionDays"]:
                fecha = date.fromisoformat(dia["date"])
                if inicio.date() <= fecha <= fin.date():
                    dias[fecha] = dia["contributionCount"]
        if anio == ahora.year:
            commits = datos["totalCommitContributions"]
            solicitudes = datos["totalPullRequestContributions"]
            incidencias = datos["totalIssueContributions"]
    return dias, commits, solicitudes, incidencias


def tarjeta_lenguajes(lenguajes):
    principales = lenguajes.most_common(6)
    total = sum(lenguajes.values())
    contenido = texto(26, 40, "Lenguajes más utilizados", "azul valor", 19)
    colores = ["#0969da", "#8250df", "#bf3989", "#1a7f37", "#bc4c00", "#6574a5"]
    x = 26
    for indice, (nombre, cantidad) in enumerate(principales):
        ancho = cantidad / total * 430
        contenido += f'<rect x="{x:.2f}" y="70" width="{ancho:.2f}" height="11" fill="{colores[indice]}"/>'
        x += ancho
        y = 118 + (indice // 2) * 39
        columna = 26 + (indice % 2) * 230
        contenido += f'<circle cx="{columna + 5}" cy="{y - 4}" r="5" fill="{colores[indice]}"/>'
        contenido += texto(columna + 18, y, f"{nombre} {cantidad / total * 100:.1f}%", tamano=13)
    resto = total - sum(cantidad for _, cantidad in principales)
    if resto:
        contenido += f'<rect x="{x:.2f}" y="70" width="{resto / total * 430:.2f}" height="11" fill="#afb8c1"/>'
        contenido += texto(26, 235, f"Otros {resto / total * 100:.1f}%", "suave", 12)
    if not principales:
        contenido += texto(26, 115, "Sin datos de lenguajes disponibles", "suave")
    contenido += texto(26, 273, "Código en repositorios públicos propios", "suave", 11)
    contenido += texto(26, 291, "Por bytes · forks excluidos", "suave", 11)
    return lienzo(495, 320, "Lenguajes más utilizados", contenido)


def actualizar(raiz=None, ahora=None):
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    ahora = ahora or datetime.now(timezone.utc)
    perfil = consultar("users/" + USUARIO)
    repositorios = []
    pagina = 1
    while True:
        lote = consultar(f"users/{USUARIO}/repos?type=owner&per_page=100&page={pagina}")
        repositorios.extend(lote)
        if len(lote) < 100:
            break
        pagina += 1
    estrellas = sum(repo["stargazers_count"] for repo in repositorios)
    lenguajes = Counter()
    for repo in repositorios:
        if not repo["fork"]:
            lenguajes.update(consultar(f"repos/{USUARIO}/{repo['name']}/languages"))
    dias, commits, solicitudes, incidencias = contribuciones(perfil, ahora)
    actual, maxima = rachas(dias, ahora.date())
    fecha = ahora.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y")
    metricas = [
        ("Estrellas recibidas", estrellas),
        ("Seguidores", perfil["followers"]),
        ("Repositorios públicos", perfil["public_repos"]),
        (f"Commits · {ahora.year}", commits),
        (f"Pull requests · {ahora.year}", solicitudes),
        (f"Incidencias · {ahora.year}", incidencias),
        (f"Contribuciones · {ahora.year}", sum(n for d, n in dias.items() if d.year == ahora.year)),
        ("Racha actual", f"{actual} días"),
        ("Racha más larga", f"{maxima} días"),
    ]
    grafico = texto(26, 40, "GitHub", "azul valor", 19)
    for indice, (nombre, valor) in enumerate(metricas):
        y = 75 + indice * 23
        grafico += texto(26, y, nombre) + texto(464, y, valor, "valor", 13, "end")
    grafico += texto(26, 302, "Actualizado " + fecha + " · GitHub API", "suave", 11)
    racha = '<path d="M265 32V185M525 32V185" stroke="#d1d9e0"/>'
    for x, valor, nombre in [(135, sum(dias.values()), "Contribuciones totales"), (395, actual, "Racha actual"), (655, maxima, "Racha más larga")]:
        racha += texto(x, 101, valor, "azul valor", 36, "middle") + texto(x, 140, nombre, tamano=15, ancla="middle")
    racha += texto(395, 207, "Desde " + perfil["created_at"][:10] + " · Calendario de GitHub · " + fecha, "suave", 11, "middle")
    archivos = {
        "seguidores.svg": indicador("Seguidores", perfil["followers"]),
        "estrellas.svg": indicador("Estrellas", estrellas),
        "github.svg": lienzo(495, 320, "Estadísticas de GitHub", grafico),
        "lenguajes.svg": tarjeta_lenguajes(lenguajes),
        "racha.svg": lienzo(790, 230, "Contribuciones y rachas", racha),
    }
    readme = raiz / "README.md"
    contenido = readme.read_text(encoding="utf-8")
    for archivo, svg in archivos.items():
        patron = r"\./assets/" + re.escape(archivo) + r"(?:\?v=[a-f0-9]+)?"
        if len(re.findall(patron, contenido)) != 1:
            raise ValueError("Referencia única ausente en README " + archivo)
        version = hashlib.sha256(svg.encode()).hexdigest()[:12]
        contenido = re.sub(patron, f"./assets/{archivo}?v={version}", contenido)
    for archivo, svg in archivos.items():
        destino = raiz / "assets" / archivo
        temporal = destino.with_suffix(".tmp")
        temporal.write_text(svg, encoding="utf-8")
        temporal.replace(destino)
    readme.write_text(contenido, encoding="utf-8")
    print(json.dumps({"seguidores": perfil["followers"], "estrellas": estrellas, "lenguajes": len(lenguajes), "contribuciones": sum(dias.values()), "racha": actual}))


if __name__ == "__main__":
    actualizar()

