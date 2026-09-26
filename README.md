# Scripting Workshop — Hack&Beer

From zero to hero en python y burpsuite!

## La idea del workshop

Burp es excelente para entender una request pero en ocasiones se queda corto cuando el ataque necesita memoria, correlacion, ritmo, un protocolo que no es HTTP, o un canal fuera de banda. Cada lab de aqui esta construido para que topes con ese muro y lo cruces escribiendo codigo con tus propias manitas.

El recorrido de cada lab es siempre el mismo:

1. Navegas la app y ves la request en el Proxy de Burp.
2. La repites en Repeater y encuentras la vulnerabilidad que cambia en la respuesta cuando cambias la entrada.
3. Traduces la request de Repeater a Python y automatizas el ataque completo.

## Requisitos

| Herramienta | Version minima | Como comprobar |
|-------------|----------------|----------------|
| Docker Desktop (o Docker Engine) | 24 | `docker --version` |
| Docker Compose | v2.20 (por `include:`) | `docker compose version` |
| Python | 3.10 | `python3 --version` |
| Burp Suite Community | 2024.x | abrelo |
| nc (netcat) | el del sistema | `which nc` |

## Instalar las dependencias del lado atacante una sola vez:

```bash
cd scripting-workshop-labs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Levantar todo de una vez

```bash
cd scripting-workshop-labs
docker compose up -d --build
docker compose ps
```

Comprobacion rapida de que los cinco estan arriba:

```bash
for p in 8001 8002 8003 8005; do
  printf "puerto %s: " "$p"
  curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:$p/health"
done
printf "puerto 1389: "
printf 'HEALTH\nQUIT\n' | nc 127.0.0.1 1389 | grep -c '^HEALTH$'
```

Bajar todo y borrar volumenes:

```bash
docker compose down -v
```

Tambien puedes levantar un solo lab entrando a su carpeta y corriendo ahi `docker compose up -d --build`. Es lo recomendado durante el workshop ya que ocupa menos recursos, aunque probablemente no tengas tema con un equipo relativamente nuevo con al menos 8GB de RAM.

## Los cinco labs

| Lab | Tema | Vulnerabilidad | Puerto | Lo que aprendes a programar |
|-----|------|----------------|--------|-----------------------------|
| [[labs/01-newspaper/]] | El Nacido de la Bruma | IDOR mas paginacion incompleta | 8001 | Loops, parsing con regex, diferencia de conjuntos, hilos |
| [[labs/02-street-finder/]] | Callejero Municipal | Inyeccion XPath sobre backend XML | 8002 | Oraculo booleano, descubrimiento de estructura, busqueda binaria |
| [[labs/03-blind-sqli/]] | Almacen Central | Blind SQLi en MySQL con WAF y rate limit | 8003 | Bypass de lista negra, pacing adaptativo, reintento sobre 429 |
| [[labs/04-ldap-employees/]] | Directorio RH | Inyeccion de filtro LDAP | 1389 | Sockets crudos, protocolo que no es HTTP |
| [[labs/05-oob-oracle/]] | NOC Diagnostics | Inyeccion de comandos ciega fuera de banda | 8005 | Listener propio, hilos, correlacion con nonces |

## Puertos y flags

Los cinco labs residen en `127.0.0.1` unicamente. Las bases de datos y el directorio LDAP viven en la red interna de Docker y no se exponen al host y lo más importante: Todos los flags tienen el formato `H&B{...}`. 

Los labs son deliberadamente vulnerables. Escuchan solo en loopback y no hablan con internet pero tampoco los expongas en una red compartida, no los subas a un VPS y sobre todo, no reutilices este codigo en produccion. Lo que aprendes aqui se aplica unicamente sobre sistemas para los que tengas autorizacion escrita y legal.
