# Gateway TCP del Directorio RH. Es la app vulnerable del lab.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gateway.py /app/gateway.py
COPY healthcheck.py /app/healthcheck.py

RUN useradd --create-home --shell /usr/sbin/nologin gateway
USER gateway

EXPOSE 1389

CMD ["python3", "-u", "/app/gateway.py"]
