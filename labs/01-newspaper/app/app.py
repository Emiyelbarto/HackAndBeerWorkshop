"""El Heraldo Nocturno: sitio de periodico con IDOR en /article/<id>.

La vulnerabilidad es doble y esa es la leccion:
  1. /article/<id> sirve cualquier articulo del catalogo sin verificar autenticación.
  2. El indice paginado solo enlaza los articulos publicados.
El resultado es un articulo alcanzable que no esta enlazado en ninguna parte.
"""

from html import escape

from flask import Flask, jsonify, request

import articles

app = Flask(__name__)

SITE_NAME = "El Nacido de la Bruma"

# El estado se guarda en ingles (identificador) y se muestra en espanol (mensaje).
STATUS_LABELS = {"published": "publicado", "draft": "borrador"}

PAGE_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 52rem; margin: 2rem auto; color: #1b1b1b; }}
h1 {{ border-bottom: 3px double #1b1b1b; padding-bottom: .4rem; }}
.section {{ font-variant: small-caps; color: #7a2727; }}
.meta {{ color: #555; font-size: .9rem; }}
.article-list {{ line-height: 1.9; }}
.pager a {{ margin-right: 1rem; }}
.draft-banner {{ background: #f6e6a5; padding: .6rem; border: 1px solid #b09b40; }}
</style>
</head>
<body>
{content}
</body>
</html>
"""


def render(title, content):
    return PAGE_TEMPLATE.format(title=escape(title), content=content)


def article_line(article):
    return (
        '<li><span class="section">{section}</span> '
        '<a class="article-link" href="/article/{id}">{title}</a></li>'
    ).format(
        section=escape(article["section"]),
        id=article["id"],
        title=escape(article["title"]),
    )


def pager(page):
    links = []
    if page > 1:
        links.append('<a class="prev-page" href="/?page={0}">Anterior</a>'.format(page - 1))
    if page < articles.TOTAL_PAGES:
        links.append('<a class="next-page" href="/?page={0}">Siguiente</a>'.format(page + 1))
    return '<nav class="pager">\n{0}\n</nav>'.format("\n".join(links))


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    raw_page = request.args.get("page", "1")
    page = int(raw_page) if raw_page.isdigit() and int(raw_page) >= 1 else 1
    if page > articles.TOTAL_PAGES:
        page = articles.TOTAL_PAGES

    rows = "\n".join(article_line(a) for a in articles.page_slice(page))
    content = (
        "<h1>{site}</h1>\n"
        '<p class="meta">Edicion digital. Pagina <span id="page-number">{page}</span> '
        'de <span id="page-total">{total}</span>. '
        "{count} articulos publicados.</p>\n"
        '<ul class="article-list">\n{rows}\n</ul>\n'
        "{pager}"
    ).format(
        site=escape(SITE_NAME),
        page=page,
        total=articles.TOTAL_PAGES,
        count=len(articles.PUBLISHED_IDS),
        rows=rows,
        pager=pager(page),
    )
    return render(SITE_NAME, content)


@app.route("/article/<int:article_id>")
def article_detail(article_id):
    article = articles.get_article(article_id)
    if article is None:
        return not_found(None)

    banner = ""
    if article["status"] == "draft":
        banner = '<p class="draft-banner">Borrador sin publicar. Uso interno.</p>\n'

    related = ""
    if article["related"]:
        links = "\n".join(
            '<a class="article-link" href="/article/{0}">{1}</a>'.format(
                rid, escape(articles.CATALOG[rid]["title"])
            )
            for rid in article["related"]
        )
        related = (
            '<h2>Tambien en esta seccion</h2>\n<nav class="related">\n{0}\n</nav>\n'
        ).format(links)

    body = "\n".join("<p>{0}</p>".format(escape(p)) for p in article["body"])
    content = (
        "{banner}"
        "<article>\n"
        "<h1>{title}</h1>\n"
        '<p class="meta"><span class="section">{section}</span> | Por {author} | '
        "ID {id} | Estado: {status}</p>\n"
        '<div class="body">\n{body}\n</div>\n'
        "</article>\n"
        "{related}"
        '<p><a class="home-link" href="/">Volver al indice</a></p>'
    ).format(
        banner=banner,
        title=escape(article["title"]),
        section=escape(article["section"]),
        author=escape(article["author"]),
        id=article["id"],
        status=escape(STATUS_LABELS[article["status"]]),
        body=body,
        related=related,
    )
    return render(article["title"], content)


@app.errorhandler(404)
def not_found(_error):
    content = (
        '<h1 class="error-title">404: Article not found</h1>\n'
        '<p><a class="home-link" href="/">Go back.</a></p>'
    )
    return render("404: Not Found", content), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
