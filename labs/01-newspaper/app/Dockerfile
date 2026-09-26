FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY articles.py app.py ./
RUN useradd --create-home --shell /usr/sbin/nologin heraldo
USER heraldo

EXPOSE 8000

# Varios workers para que el lab aguante el pool de hilos de solve.py.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "4", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
