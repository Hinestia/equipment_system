#!/bin/sh
set -e

# На случай, если том ещё не создан (или DJANGO_DATA_DIR указывает на путь
# без примонтированного тома) — создаём папку данных заранее, иначе SQLite
# не сможет открыть файл базы.
if [ -n "$DJANGO_DATA_DIR" ]; then
    mkdir -p "$DJANGO_DATA_DIR"
fi

echo "== Применяю миграции =="
python manage.py migrate --noinput

echo "== Собираю статические файлы =="
python manage.py collectstatic --noinput

# Автоматическое создание администратора для /admin/ при первом запуске,
# если заданы переменные окружения DJANGO_SUPERUSER_USERNAME и
# DJANGO_SUPERUSER_PASSWORD (см. docker-compose.yml). Если пользователь
# с таким именем уже есть — ничего не делает, ошибок не будет.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "== Проверяю/создаю администратора =="
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '$DJANGO_SUPERUSER_USERNAME'
password = '$DJANGO_SUPERUSER_PASSWORD'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email='', password=password)
    print(f'Администратор {username} создан.')
else:
    print(f'Администратор {username} уже существует, пропускаю.')
"
fi

echo "== Запускаю сервер =="
# 1 процесс (--workers 1) — исключает конкурентную запись в SQLite из разных
# процессов (основной источник редких "database is locked" / Internal Server
# Error). Внутри этого процесса используется несколько ПОТОКОВ (--threads) —
# это не создаёт риска блокировки SQLite (WAL-режим и увеличенный busy_timeout
# в settings.py всё равно страхуют), зато решает две вещи разом:
#   1) медленная передача файла одному пользователю не блокирует остальных;
#   2) воркер типа gthread сообщает о своей работоспособности независимо от
#      длительности конкретного запроса, поэтому долгая (по локальной сети)
#      передача файла больше не выглядит для gunicorn как "зависший" воркер,
#      которого нужно убить на середине — именно это раньше проявлялось как
#      "Загрузка прервана" при скачивании документов.
exec gunicorn equipment_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-1}" \
    --worker-class gthread \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
