FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /usr/bin/xargs

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./

# El flag vive en el sistema de archivos y lo puede leer el usuario de la app.
RUN printf 'H&B{00b_0r4cl3_c4llb4ck}\n' > /flag.txt \
    && chmod 644 /flag.txt \
    && useradd --create-home --uid 10005 noc

USER noc
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "8", \
     "--access-logfile", "-", "app:app"]
