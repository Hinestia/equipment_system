# Образ для системы учёта оборудования.
# Собранный образ не хранит данные (базу/документы) — они живут в томе,
# который монтируется через docker-compose.yml (см. DJANGO_DATA_DIR).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
