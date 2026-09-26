import random

SEED = 20260926
TOTAL_ARTICLES = 420
ID_MIN = 1
ID_MAX = 900
PAGE_SIZE = 8
RELATED_PER_ARTICLE = 3
DRAFT_POSITION = 73

FLAG = "H&B{n3wsp4p3r_1d0r_p4g1n4c10n}"

SECTIONS = [
    "Politica",
    "Economia",
    "Cultura",
    "Deportes",
    "Ciencia",
    "Policiaca",
]

SUBJECTS = [
    "El cabildo",
    "La cooperativa de transportistas",
    "El observatorio municipal",
    "La fiscalia estatal",
    "El sindicato de panaderos",
    "La orquesta de la plaza",
    "El comite vecinal",
    "La aduana del puerto",
    "El hospital de la colonia",
    "La biblioteca nocturna",
]

VERBS = [
    "aprueba",
    "cuestiona",
    "documenta",
    "suspende",
    "financia",
    "audita",
    "celebra",
    "reactiva",
]

OBJECTS = [
    "el censo de bicicletas",
    "la remodelacion del mercado",
    "un padron de proveedores",
    "el alumbrado de la avenida",
    "la ruta nueva del tranvia",
    "un archivo de fotografias",
    "el torneo de ajedrez",
    "la red de pozos de agua",
    "un inventario de semillas",
    "el programa de becas",
]

PLACES = [
    "San Ildefonso",
    "Barrio Alto",
    "La Candelaria",
    "Puerto Viejo",
    "Colonia Aurora",
    "Valle Sombrio",
    "Las Animas",
]

SENTENCES = [
    "Los vecinos de {place} describieron la maniobra como inesperada pero ordenada.",
    "La oficina de {section} confirmo que el expediente permanece abierto.",
    "El acuerdo se firmo a las dos de la manana, sin prensa en la sala.",
    "Tres proveedores presentaron la misma cotizacion con distinto membrete.",
    "La auditoria interna pidio los recibos originales y recibio copias.",
    "El presupuesto asignado no aparece en el informe trimestral.",
    "Un funcionario acepto que el plano circulaba desde hace meses.",
    "La sesion se transmitio con dieciocho minutos de retraso.",
    "El acta menciona un anexo que nadie del comite pudo localizar.",
    "Los trabajos comenzaran cuando termine la temporada de lluvias.",
    "La ciudadania puede consultar el expediente en la ventanilla tres.",
    "El contrato incluye una clausula de confidencialidad de cinco anos.",
]

AUTHORS = [
    "Renata Olvera",
    "Camilo Estrada",
    "Ileana Prado",
    "Bruno Ferreiro",
    "Marisol Aguirre",
    "Teodoro Lanz",
]


def _make_title(rng):
    return "{0} {1} {2} en {3}".format(
        rng.choice(SUBJECTS),
        rng.choice(VERBS),
        rng.choice(OBJECTS),
        rng.choice(PLACES),
    )


def _make_body(rng, section, paragraphs=3, per_paragraph=3):
    place = rng.choice(PLACES)
    picked = rng.sample(SENTENCES, paragraphs * per_paragraph)
    body = []
    for index in range(paragraphs):
        chunk = picked[index * per_paragraph:(index + 1) * per_paragraph]
        body.append(" ".join(line.format(place=place, section=section) for line in chunk))
    return body


def _build_catalog():
    rng = random.Random(SEED)
    ids = sorted(rng.sample(range(ID_MIN, ID_MAX + 1), TOTAL_ARTICLES))
    draft_id = ids[DRAFT_POSITION]

    catalog = {}
    for article_id in ids:
        local = random.Random(SEED + article_id)
        section = local.choice(SECTIONS)
        catalog[article_id] = {
            "id": article_id,
            "section": section,
            "title": _make_title(local),
            "author": local.choice(AUTHORS),
            "status": "draft" if article_id == draft_id else "published",
            "body": _make_body(local, section),
            "related": [],
        }

    # El borrador lleva el flag en el cuerpo. Es el unico articulo que lo tiene.
    catalog[draft_id]["title"] = "Nota sin publicar sobre el tablero de la redaccion"
    catalog[draft_id]["body"] = [
        "Este texto todavia no pasa por edicion y no debe salir en la portada.",
        "Recordatorio para la mesa de redaccion: la clave del tablero interno es "
        + FLAG
        + ".",
        "Pendiente: confirmar las dos fuentes antes de mover el estado a publicado.",
    ]

    # Los enlaces de "relacionados" solo apuntan a articulos publicados. Ningun
    # enlace del sitio apunta al borrador: rastrear enlaces nunca lo encuentra.
    published_ids = [i for i in ids if i != draft_id]
    for article_id in published_ids:
        local = random.Random(SEED * 2 + article_id)
        pool = [i for i in published_ids if i != article_id]
        catalog[article_id]["related"] = sorted(local.sample(pool, RELATED_PER_ARTICLE))

    return catalog, ids, draft_id


CATALOG, ALL_IDS, DRAFT_ID = _build_catalog()
PUBLISHED_IDS = [i for i in ALL_IDS if i != DRAFT_ID]
TOTAL_PAGES = (len(PUBLISHED_IDS) + PAGE_SIZE - 1) // PAGE_SIZE


def get_article(article_id):
    """Devuelve el articulo por ID sin mirar su estado: aqui vive el IDOR."""
    return CATALOG.get(article_id)


def page_slice(page):
    """Devuelve los articulos publicados de una pagina del indice."""
    start = (page - 1) * PAGE_SIZE
    return [CATALOG[i] for i in PUBLISHED_IDS[start:start + PAGE_SIZE]]
