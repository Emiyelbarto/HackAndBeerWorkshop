import os
import socket
import socketserver
import sys

from ldap3 import Connection, Server
from ldap3.core.exceptions import LDAPException, LDAPInvalidFilterError

LISTEN_HOST = os.environ.get("GATEWAY_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("GATEWAY_PORT", "1389"))

DIRECTORY_HOST = os.environ.get("DIRECTORY_HOST", "lab04_directory")
DIRECTORY_PORT = int(os.environ.get("DIRECTORY_PORT", "389"))
BIND_DN = "cn=admin,dc=hackandbeer,dc=local"
BIND_PASSWORD = "directorio123"
BASE_DN = "ou=employees,dc=hackandbeer,dc=local"

# Departamento que el directorio publico no muestra: ahi viven las cuentas de
# servicio. El filtro base las excluye con un NOT.
HIDDEN_DEPARTMENT = "Internal"

# Atributos que el gateway formatea. "description" NO esta en la lista, asi que
# nunca sale por el socket: solo se puede preguntar por el con comodines.
SHOWN_ATTRIBUTES = ("uid", "cn", "mail", "title", "departmentNumber")

# Atributos que el directorio si permite consultar en el filtro.
SEARCHABLE_ATTRIBUTES = ("uid", "cn", "mail", "title", "departmentNumber", "description")

BANNER = (
    "DIRECTORIO RH v1.4 (HackAndBeer Corp)",
    "Protocolo de texto por lineas. Cada respuesta termina con la linea END.",
    "Escribe HELP para ver los comandos.",
)

HELP_LINES = (
    "COMANDOS",
    "  HELP              muestra esta ayuda",
    "  LIST              lista el directorio publico completo",
    "  SEARCH <uid>      busca empleados por uid (acepta el comodin *)",
    "  HEALTH            sonda de salud del servicio",
    "  QUIT              cierra la sesion",
    "",
    "ATRIBUTOS CONSULTABLES EN EL FILTRO",
    "  " + ", ".join(SEARCHABLE_ATTRIBUTES),
    "",
    "ATRIBUTOS QUE ESTE GATEWAY IMPRIME",
    "  " + ", ".join(SHOWN_ATTRIBUTES),
    "",
    "NOTA: description es consultable pero por politica interna no se imprime.",
)

END_MARKER = "END"
MAX_LINE = 8192
# Una sesion interactiva ociosa se cierra sola para no dejar hilos colgados.
IDLE_TIMEOUT = float(os.environ.get("GATEWAY_IDLE_TIMEOUT", "120"))


def build_search_filter(user_input):
    """Arma el filtro LDAP concatenando la entrada del usuario sin sanitizar.

    Aqui esta la vulnerabilidad: el valor entra tal cual entre "(uid=" y ")".
    """
    return "(&(uid=" + user_input + ")(objectClass=inetOrgPerson))"


def build_list_filter():
    """Filtro fijo del listado publico: no recibe entrada del usuario."""
    return "(&(objectClass=inetOrgPerson)(!(departmentNumber=" + HIDDEN_DEPARTMENT + ")))"


def format_entry(entry):
    """Convierte una entrada LDAP en lineas de texto, omitiendo description."""
    values = entry.get("attributes", {})
    lines = ["ENTRY uid=" + first_value(values, "uid")]
    for name in SHOWN_ATTRIBUTES:
        if name == "uid":
            continue
        value = first_value(values, name)
        if value:
            lines.append("  " + name + ": " + value)
    return lines


def first_value(values, name):
    """Devuelve el primer valor de un atributo LDAP como texto plano."""
    raw = values.get(name)
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    return str(raw) if raw else ""


class DirectorySession:
    """Conexion LDAP propia de cada sesion TCP del cliente."""

    def __init__(self):
        server = Server(DIRECTORY_HOST, port=DIRECTORY_PORT, get_info=None, connect_timeout=5)
        self.conn = Connection(
            server, user=BIND_DN, password=BIND_PASSWORD, auto_bind=True, raise_exceptions=False
        )

    def search(self, ldap_filter):
        """Ejecuta la busqueda y devuelve la lista de entradas encontradas."""
        self.conn.search(BASE_DN, ldap_filter, attributes=list(SHOWN_ATTRIBUTES))
        return [e for e in self.conn.response if e.get("type") == "searchResEntry"]

    def close(self):
        """Suelta la conexion con el directorio."""
        self.conn.unbind()


class GatewayHandler(socketserver.StreamRequestHandler):
    """Atiende una sesion TCP: lee lineas, responde bloques terminados en END."""

    timeout = IDLE_TIMEOUT

    def handle(self):
        try:
            session = DirectorySession()
        except LDAPException as exc:
            self.send_block(["ERROR: el directorio no responde (" + type(exc).__name__ + ")"])
            return
        self.send_block(list(BANNER))
        try:
            self.command_loop(session)
        except (TimeoutError, ConnectionError):
            # Sesion ociosa o cliente que se fue: se cierra sin ensuciar el log.
            pass
        finally:
            session.close()

    def command_loop(self, session):
        """Bucle principal de comandos hasta QUIT o cierre del cliente."""
        while True:
            raw = self.rfile.readline(MAX_LINE)
            if not raw:
                return
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            verb, _, argument = line.partition(" ")
            verb = verb.upper()
            argument = argument.strip()
            if verb == "QUIT":
                self.send_block(["BYE"])
                return
            if verb == "HEALTH":
                self.send_block(["HEALTH"])
            elif verb == "HELP":
                self.send_block(list(HELP_LINES))
            elif verb == "LIST":
                self.run_query(session, build_list_filter())
            elif verb == "SEARCH":
                if not argument:
                    self.send_block(["ERROR: SEARCH requiere un valor. Ejemplo: SEARCH mrivera"])
                else:
                    self.run_query(session, build_search_filter(argument))
            else:
                self.send_block(["ERROR: comando desconocido. Usa HELP."])

    def run_query(self, session, ldap_filter):
        """Lanza el filtro contra el directorio y formatea la respuesta."""
        try:
            entries = session.search(ldap_filter)
        except LDAPInvalidFilterError:
            self.send_block(["ERROR: filtro LDAP invalido"])
            return
        except LDAPException as exc:
            self.send_block(["ERROR: fallo la consulta al directorio (" + type(exc).__name__ + ")"])
            return
        body = ["MATCHES: " + str(len(entries))]
        for entry in entries:
            body.extend(format_entry(entry))
        self.send_block(body)

    def send_block(self, lines):
        """Escribe un bloque de respuesta y lo cierra con el delimitador END."""
        payload = "\n".join(lines + [END_MARKER]) + "\n"
        self.wfile.write(payload.encode("utf-8"))
        self.wfile.flush()


class ThreadedGateway(socketserver.ThreadingTCPServer):
    """Servidor TCP con un hilo por cliente."""

    allow_reuse_address = True
    daemon_threads = True
    address_family = socket.AF_INET


def main():
    """Arranca el gateway en el puerto configurado."""
    server = ThreadedGateway((LISTEN_HOST, LISTEN_PORT), GatewayHandler)
    print("gateway escuchando en " + LISTEN_HOST + ":" + str(LISTEN_PORT), flush=True)
    print("directorio interno en " + DIRECTORY_HOST + ":" + str(DIRECTORY_PORT), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
