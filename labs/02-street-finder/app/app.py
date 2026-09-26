import html
import os

from flask import Flask, Response, request
from lxml import etree

XML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "streets.xml")

app = Flask(__name__)
TREE = etree.parse(XML_PATH)

# VULNERABLE A PROPOSITO: la expresion XPath se arma concatenando la entrada
# del usuario. No hay escapado de comillas ni lista blanca de caracteres.
QUERY_TEMPLATE = "//street[contains(name, '{q}')]"

PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Callejero Municipal</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; max-width: 60rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: .35rem .6rem; text-align: left; }}
th {{ background: #eee; }}
.count {{ font-weight: bold; }}
.empty {{ color: #a00; }}
</style>
</head>
<body>
<h1>Callejero Municipal</h1>
<p>Consulta el padron de vias publicas por nombre. La busqueda es por subcadena y distingue mayusculas.</p>
<form method="get" action="/search">
<input type="text" name="q" value="{value}" size="40" placeholder="Reforma">
<button type="submit">Buscar</button>
</form>
{results}
</body>
</html>
"""

ROW = ("<tr class=\"hit\"><td>{name}</td><td>{neighborhood}</td>"
       "<td>{postal_code}</td><td>{road_type}</td></tr>")

TABLE = ("<table><thead><tr><th>Via</th><th>Colonia</th><th>Codigo postal</th>"
         "<th>Tipo de via</th></tr></thead><tbody>{rows}</tbody></table>")


def render(value, results_html):
    return PAGE.format(value=html.escape(value, quote=True), results=results_html)


def search(term):
    expression = QUERY_TEMPLATE.format(q=term)
    nodes = TREE.xpath(expression)
    # La app SOLO renderiza nodos street: ninguna otra rama del documento se
    # devuelve nunca al cliente, por eso el oraculo es estrictamente booleano.
    return [n for n in nodes if getattr(n, "tag", None) == "street"]


def results_block(streets):
    block = '<p class="count">Resultados: {n}</p>'.format(n=len(streets))
    if not streets:
        return block + '<p class="empty">Sin resultados</p>'
    rows = "".join(
        ROW.format(
            name=html.escape(s.findtext("name", "")),
            neighborhood=html.escape(s.findtext("neighborhood", "")),
            postal_code=html.escape(s.findtext("postal_code", "")),
            road_type=html.escape(s.findtext("road_type", "")),
        )
        for s in streets
    )
    return block + TABLE.format(rows=rows)


@app.get("/")
def index():
    """Formulario de busqueda."""
    return Response(render("", ""), mimetype="text/html")


@app.get("/search")
def search_view():
    term = request.args.get("q", "")
    try:
        streets = search(term)
    except etree.XPathEvalError as exc:
        body = render(term, '<p class="empty">Consulta invalida: {e}</p>'.format(
            e=html.escape(str(exc))))
        return Response(body, status=400, mimetype="text/html")
    return Response(render(term, results_block(streets)), mimetype="text/html")


@app.get("/health")
def health():
    return {"status": "ok"}
