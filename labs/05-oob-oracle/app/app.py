import re
import subprocess
import threading
import uuid

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

PING_COMMAND = "ping -c 1 -W 1 {host}"

# Filtro de entrada. El desarrollador penso en sustitucion de comandos y en
# inyeccion de argumentos, y se olvido de los separadores.
BLOCKED_CHARS = ("$", "`", "<", ">")
FLAG_LIKE_TOKEN = re.compile(r"(?:^|\s)-")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
MAX_HOST_LENGTH = 256

# Entorno reducido del subproceso: /usr/local/bin queda fuera, asi que el
# interprete de python del contenedor no es alcanzable por PATH.
SAFE_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/home/noc", "LANG": "C"}
JOB_TIMEOUT_SECONDS = 8

PANEL_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>NOC Diagnostics</title>
<style>
body { font-family: system-ui, sans-serif; background: #10161c; color: #dfe7ee;
       margin: 0; padding: 2rem; }
main { max-width: 42rem; margin: 0 auto; }
h1 { font-size: 1.4rem; letter-spacing: .04em; }
form { background: #18222c; padding: 1.2rem; border: 1px solid #263340; }
input { width: 70%; padding: .5rem; background: #0c1116; color: #dfe7ee;
        border: 1px solid #2d3d4d; }
button { padding: .5rem 1rem; background: #1d6fa5; color: #fff; border: 0;
         cursor: pointer; }
pre { background: #0c1116; padding: 1rem; border: 1px solid #263340;
      white-space: pre-wrap; }
small { color: #8fa3b5; }
</style>
</head>
<body>
<main>
<h1>NOC Diagnostics :: verificacion de enlace</h1>
<p>Encola una prueba ICMP contra un host del backbone. El resultado se entrega al
sistema de tickets, no a esta pantalla.</p>
<form id="diag">
  <input id="host" name="host" value="10.20.0.1" autocomplete="off">
  <button type="submit">Encolar diagnostico</button>
</form>
<pre id="out">esperando...</pre>
<small>Los resultados de ICMP se archivan en el ticket. Esta vista solo confirma
el encolado.</small>
</main>
<script>
document.getElementById('diag').addEventListener('submit', async (e) => {
  e.preventDefault();
  const res = await fetch('/api/diagnose', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({host: document.getElementById('host').value})
  });
  document.getElementById('out').textContent =
    res.status + ' ' + JSON.stringify(await res.json());
});
</script>
</body>
</html>
"""


def validate_host(host):
    if not isinstance(host, str) or not host.strip():
        return 400, "el campo host es obligatorio"
    if len(host) > MAX_HOST_LENGTH:
        return 400, "el campo host excede la longitud permitida"
    if CONTROL_CHARS.search(host):
        return 403, "caracter de control no permitido en el campo host"
    for blocked in BLOCKED_CHARS:
        if blocked in host:
            return 403, "caracter no permitido en el campo host"
    if FLAG_LIKE_TOKEN.search(host):
        return 403, "no se aceptan argumentos en el campo host"
    return None


def run_diagnostic(command):
    try:
        subprocess.run(
            command,
            shell=True,
            env=SAFE_ENV,
            capture_output=True,
            timeout=JOB_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        pass


def queue_diagnostic(host):
    job_id = uuid.uuid4().hex
    command = PING_COMMAND.format(host=host)
    worker = threading.Thread(target=run_diagnostic, args=(command,), daemon=True)
    worker.start()
    return job_id


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/")
def panel():
    return Response(PANEL_HTML, mimetype="text/html")


@app.post("/api/diagnose")
def diagnose():
    payload = request.get_json(silent=True) or {}
    host = payload.get("host")
    rejection = validate_host(host)
    if rejection is not None:
        status, message = rejection
        return jsonify({"error": message}), status
    return jsonify({"job_id": queue_diagnostic(host), "queued": True}), 202
