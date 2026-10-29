FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Cliente de Postgres 16 para las copias y la prueba de restauración (E00-07). El de Debian
# es otra versión: el de PGDG coincide con la base de Render.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-common \
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app
# Sin las dependencias de desarrollo: esta imagen es la que corre en el hosting.
RUN pip install --no-cache-dir .

EXPOSE 8000
# Migraciones al arrancar: el plan inicial de Render no tiene paso previo al despliegue.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
