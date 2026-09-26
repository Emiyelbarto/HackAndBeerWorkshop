# Directorio LDAP real (slapd de OpenLDAP). Solo vive en la red interna del compose.
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    { \
      echo "slapd slapd/no_configuration boolean false"; \
      echo "slapd slapd/domain string hackandbeer.local"; \
      echo "slapd shared/organization string HackAndBeer Corp"; \
      echo "slapd slapd/password1 password directorio123"; \
      echo "slapd slapd/password2 password directorio123"; \
      echo "slapd slapd/backend select MDB"; \
      echo "slapd slapd/purge_database boolean true"; \
      echo "slapd slapd/move_old_database boolean true"; \
      echo "slapd slapd/allow_ldap_v2 boolean false"; \
    } | debconf-set-selections; \
    apt-get update; \
    apt-get install -y --no-install-recommends slapd ldap-utils; \
    rm -rf /var/lib/apt/lists/*

COPY seed.ldif /seed.ldif

# Carga offline con slapadd: el arbol queda dentro de la imagen, sin volumenes
# y sin esperar a que el demonio arranque en el primer boot.
RUN set -eux; \
    slapadd -q -F /etc/ldap/slapd.d -b dc=hackandbeer,dc=local -l /seed.ldif; \
    chown -R openldap:openldap /var/lib/ldap /etc/ldap/slapd.d

EXPOSE 389

# slapd necesita root para hacer setuid a openldap; luego suelta privilegios.
# -d 0 lo deja en primer plano, que es lo que Docker espera del PID 1.
CMD ["slapd", "-h", "ldap://0.0.0.0:389/", "-u", "openldap", "-g", "openldap", "-d", "0"]
