FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app
# Sin las dependencias de desarrollo: esta imagen es la que corre en el hosting.
RUN pip install --no-cache-dir .

EXPOSE 8000
# Migraciones al arrancar: el plan inicial de Render no tiene paso previo al despliegue.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
