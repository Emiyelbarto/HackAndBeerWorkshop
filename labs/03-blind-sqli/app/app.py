import math
import os
import re
import threading
import time
from collections import defaultdict, deque

import pymysql
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

WAREHOUSE = "Almacen Central"

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "lab03_db"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "inventory"),
    "password": os.environ.get("DB_PASSWORD", "inventory_pass"),
    "database": os.environ.get("DB_NAME", "warehouse"),
    "connect_timeout": 5,
    "read_timeout": 5,
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

# ---------------------------------------------------------------------------
# Control defensivo A: WAF de lista negra por regex sobre el valor crudo.
# Bloquea lo obvio de los libros de texto y devuelve 403 con cuerpo distinguible.
# NO bloquea: espacios, parentesis, SELECT suelto, SUBSTRING, ASCII, comparaciones.
# Ese es el hueco por el que pasa el bypass del lab.
# ---------------------------------------------------------------------------
WAF_PATTERN = re.compile(
    r"'|\"|\bunion\b|information_schema|sleep\s*\(|benchmark|--|/\*|#",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Control defensivo B: rate limit por IP con ventana deslizante.
# RATE_LIMIT requests permitidas por cada RATE_WINDOW segundos.
# Las requests bloqueadas tambien entran en la ventana: esa es la penalizacion
# temporal. Quien insiste a 50 hilos empuja su propia ventana y no avanza.
# Nunca hay ban permanente: al callarse RATE_WINDOW segundos la ventana se vacia.
# ---------------------------------------------------------------------------
RATE_WINDOW = 10.0
RATE_LIMIT = 15
RATE_EXEMPT_PATHS = {"/health"}

_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def client_key():
    return request.remote_addr or "unknown"


def rate_limit_check(key):
    now = time.monotonic()
    with _hits_lock:
        window = _hits[key]
        while window and now - window[0] > RATE_WINDOW:
            window.popleft()
        window.append(now)
        if len(window) > RATE_LIMIT:
            return max(1, math.ceil(RATE_WINDOW - (now - window[0])))
    return None


@app.before_request
def enforce_rate_limit():
    if request.path in RATE_EXEMPT_PATHS:
        return None
    retry_after = rate_limit_check(client_key())
    if retry_after is None:
        return None
    body = jsonify(
        {
            "error": "rate_limited",
            "message": "Demasiadas requests. Baja el ritmo y respeta Retry-After.",
            "limit": RATE_LIMIT,
            "window_seconds": int(RATE_WINDOW),
            "retry_after": retry_after,
        }
    )
    response = app.make_response((body, 429))
    response.headers["Retry-After"] = str(retry_after)
    return response


def db_connect():
    return pymysql.connect(**DB_CONFIG)


def db_query(sql):
    connection = db_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        connection.close()


HOME_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Almacen Central - Inventario</title>
</head>
<body>
  <h1>Almacen Central</h1>
  <p>Consulta de inventario para sucursales.</p>
  <ul>
    <li><a href="/api/products">GET /api/products</a> catalogo publico</li>
    <li><a href="/api/stock?sku=1001">GET /api/stock?sku=1001</a> disponibilidad por SKU</li>
    <li><a href="/health">GET /health</a> estado del servicio</li>
  </ul>
  <p>Version 2.4.1 - entorno de pruebas internas.</p>
  <!-- TODO ALM-412: quitar el blueprint de debug /api/debug/schema antes de pasar a produccion -->
</body>
</html>
"""


@app.get("/")
def home():
    """Portada del inventario."""
    return Response(HOME_HTML, mimetype="text/html")


@app.get("/robots.txt")
def robots():
    """robots.txt del sitio."""
    return Response(
        "User-agent: *\nDisallow: /api/debug/\n",
        mimetype="text/plain",
    )


@app.get("/health")
def health():
    """Estado del servicio, incluida la conectividad con MySQL."""
    try:
        db_query("SELECT 1 AS ok")
    except pymysql.MySQLError as exc:
        return jsonify({"status": "degraded", "detail": str(exc)}), 503
    return jsonify({"status": "ok"}), 200


@app.get("/api/products")
def products():
    """Catalogo publico de productos, sin datos sensibles."""
    rows = db_query("SELECT sku, name, category FROM products ORDER BY sku")
    return jsonify({"warehouse": WAREHOUSE, "count": len(rows), "products": rows})


@app.get("/api/stock")
def stock():
    """Disponibilidad por SKU. Vulnerable: concatena el parametro en un WHERE numerico."""
    raw = request.args.get("sku")
    if raw is None or raw == "":
        return jsonify({"error": "missing_parameter", "parameter": "sku"}), 400

    if WAF_PATTERN.search(raw):
        return (
            jsonify(
                {
                    "error": "blocked_by_waf",
                    "rule": "sku_denylist",
                    "message": "Patron sospechoso en el parametro sku.",
                }
            ),
            403,
        )

    query = f"SELECT sku, name, stock FROM products WHERE sku = {raw} LIMIT 1"
    try:
        rows = db_query(query)
    except pymysql.MySQLError as exc:
        # Modo debug olvidado en el entorno de pruebas: devuelve la consulta.
        return (
            jsonify({"error": "sql_error", "query": query, "detail": str(exc)}),
            400,
        )

    # Respuesta de dos estados: ni datos ni errores, solo el booleano.
    return jsonify({"warehouse": WAREHOUSE, "in_stock": bool(rows)})


@app.get("/api/debug/schema")
def debug_schema():
    rows = db_query(
        "SELECT table_name AS tname, column_name AS cname, data_type AS dtype "
        "FROM information_schema.columns "
        f"WHERE table_schema = '{DB_CONFIG['database']}' "
        "ORDER BY tname, ordinal_position"
    )
    schema = defaultdict(list)
    for row in rows:
        schema[row["tname"]].append({"column": row["cname"], "type": row["dtype"]})
    return jsonify(
        {
            "note": "Solo metadatos. El volcado de filas se deshabilito en ALM-390.",
            "database": DB_CONFIG["database"],
            "tables": schema,
        }
    )
