# Развёртывание на сервере компании

Этот файл — только про то, как поднять систему на постоянно работающем
сервере (Linux или Windows), чтобы к ней можно было ходить по сети, а не
только с одного компьютера. Если вам достаточно локального запуска на
своей машине — смотрите `README.md`, этот файл не нужен.

## Важно понять перед разворачиванием

Система требует вход по логину и паролю на всех страницах (кроме, собственно,
самой страницы входа). Тем не менее, при развёртывании на сервере всё равно
стоит соблюдать базовую гигиену:
- Разворачивайте систему **только во внутренней сети компании** (не
  пробрасывайте порт наружу в интернет, не открывайте на публичном IP) —
  это защищает не только от подбора пароля, но и вообще снижает площадь атаки.
- Смените пароль администратора, заданный по умолчанию при разворачивании
  (через `createsuperuser` или переменные окружения `DJANGO_SUPERUSER_*`),
  сразу после первого входа.
- Выдавайте флаг «Staff status» (доступ в `/admin/`) только тем, кому
  реально нужно управлять справочниками — остальным сотрудникам достаточно
  обычной учётной записи без этого флага.

## Что нужно на сервере

- **Для варианта с Docker (рекомендуется, проще всего):** только Docker и
  Docker Compose — сам Python и зависимости ставить не нужно, всё внутри
  контейнера.
- **Для варианта без Docker:** Python 3.10+. СУБД отдельно поднимать не
  нужно в любом случае — база данных — это файл SQLite.

---

## Вариант Docker (рекомендуется) — проще и переносимее всего

Если на сервере уже есть Docker — это самый быстрый и надёжный способ:
не нужно вручную ставить Python, настраивать systemd или Nginx, обновление
сводится к одной команде. Всё уже настроено в проекте (`Dockerfile`,
`docker-compose.yml`).

### 1. Скопируйте проект на сервер

Перенесите всю папку проекта (архив с кодом) на сервер, например в
`/opt/equipment_system`, и перейдите в неё:

```bash
cd /opt/equipment_system
```

### 2. Настройте `docker-compose.yml`

Откройте `docker-compose.yml` и замените три значения:

```yaml
DJANGO_SECRET_KEY: "замените-меня-на-случайную-строку"
DJANGO_ALLOWED_HOSTS: "192.168.1.50,equipment.internal"   # ваш IP/имя сервера
DJANGO_SUPERUSER_PASSWORD: "замените-меня"                 # пароль для входа в /admin/
```

Сгенерировать случайный секретный ключ можно так (нужен Python, но можно
сделать и на своём компьютере, не обязательно на сервере):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Запустите

```bash
docker compose up -d --build
```

Всё — при первом запуске контейнер сам применит миграции базы данных,
соберёт статику и создаст администратора с логином/паролем из
`docker-compose.yml`. Через пару минут откройте
`http://<адрес-сервера>:8000/` — система попросит войти: используйте
`DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`, указанные в
`docker-compose.yml`. Остальным сотрудникам заведите учётные записи через
`/admin/` → «Users» → «Add user» (флаг «Staff status» не обязателен, если
доступ в саму админку им не нужен).

Проверить, что контейнер работает и посмотреть логи:

```bash
docker compose ps
docker compose logs -f
```

### 4. Где хранятся данные

Вся база данных, сгенерированные документы и резервные копии лежат в папке
`./data` рядом с `docker-compose.yml` (на самом сервере, не внутри
контейнера) — она создаётся автоматически при первом запуске. **Обязательно
бэкапьте именно эту папку** — при пересборке или обновлении образа
(`docker compose up -d --build`) она не удаляется и не затрагивается.

### 5. Резервное копирование

```bash
docker compose exec web python manage.py backup_db
```

Бэкап появится в `./data/backups/` на сервере. Поставьте эту команду на
расписание через `cron`:

```
0 2 * * * cd /opt/equipment_system && docker compose exec -T web python manage.py backup_db >> /var/log/equipment_backup.log 2>&1
```

### 6. Обновление системы в будущем

```bash
cd /opt/equipment_system
docker compose exec web python manage.py backup_db   # бэкап на всякий случай
# замените файлы кода на новую версию (папка ./data не трогайте)
docker compose up -d --build                          # пересоберёт и перезапустит
```

### 7. Порт и файрвол

По умолчанию система слушает порт 8000 на сервере (это настраивается в
`docker-compose.yml`, секция `ports`). Как и с любым вариантом
развёртывания — не пробрасывайте этот порт в интернет, ограничьте доступ
внутренней сетью компании (см. предупреждение выше).

---

## Вариант без Docker

Если Docker на сервере недоступен (или им не пользуются в компании) —
ниже два классических варианта: Linux (gunicorn + systemd + Nginx) и
Windows (waitress + NSSM).

## Вариант A: Linux-сервер без Docker — gunicorn + systemd + Nginx

Это стандартный надёжный способ: `gunicorn` — сервер приложений, `systemd`
следит, чтобы он не падал и поднимался при перезагрузке сервера, `Nginx` —
принимает запросы из сети и раздаёт статику/файлы эффективнее, чем Python.

### 1. Скопируйте проект на сервер и установите зависимости

```bash
# Например, в /opt/equipment_system
sudo mkdir -p /opt/equipment_system
sudo chown $USER:$USER /opt/equipment_system
# скопируйте туда содержимое архива проекта, затем:
cd /opt/equipment_system

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройте переменные окружения

Создайте файл `/opt/equipment_system/.env` (не помещайте его в архивы,
которые кому-то передаёте — там будет секретный ключ):

```bash
DJANGO_SECRET_KEY=замените-на-длинную-случайную-строку
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=192.168.1.50,equipment.internal
```

Сгенерировать случайный секретный ключ можно так:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`DJANGO_ALLOWED_HOSTS` — перечислите через запятую IP-адрес и/или доменное
имя, по которому сотрудники будут заходить на систему.

### 3. Примените миграции, соберите статику, создайте администратора

```bash
source venv/bin/activate
set -a; source .env; set +a   # подгружает переменные из .env в текущую сессию

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 4. Настройте systemd, чтобы приложение работало постоянно

Создайте `/etc/systemd/system/equipment-system.service`:

```ini
[Unit]
Description=Equipment System (Django + gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/equipment_system
EnvironmentFile=/opt/equipment_system/.env
ExecStart=/opt/equipment_system/venv/bin/gunicorn \
    equipment_system.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Замените `www-data` на пользователя, под которым должно работать
приложение (главное — у него должны быть права на запись в папку проекта,
так как туда пишутся `db.sqlite3` и `media/`).

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now equipment-system
sudo systemctl status equipment-system   # проверить, что запустилось
```

### 5. Настройте Nginx как обратный прокси

Установите Nginx (`sudo apt install nginx`) и создайте
`/etc/nginx/sites-available/equipment-system`:

```nginx
server {
    listen 80;
    server_name 192.168.1.50 equipment.internal;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/equipment-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Теперь сотрудники открывают в браузере `http://192.168.1.50/` (или
`http://equipment.internal/`, если настроено внутреннее DNS-имя).

> Примечание: статика (`/static/`) и сгенерированные документы (`/media/`)
> в этом проекте уже раздаются самим Django-приложением через встроенный
> `whitenoise` — отдельно настраивать их в Nginx не обязательно. Если
> нагрузка вырастет, для эффективности можно добавить в конфиг Nginx блоки
> `location /static/ { alias /opt/equipment_system/staticfiles/; }` и
> аналогично для `/media/`.

### Более простой Linux-вариант (без Nginx)

Если сервер используется только этой системой и Nginx ставить не хочется,
можно сразу забиндить gunicorn на порт 80 (потребует `sudo` или
`setcap`) — тогда шаг с Nginx можно пропустить, но вы теряете некоторые
удобства (например, HTTPS в будущем). Для внутреннего инструмента отдела
из 1–5 человек это нормальный компромисс.

---

## Вариант B: Windows-сервер

Если сервер компании — Windows, используйте `waitress` вместо `gunicorn`
(gunicorn не поддерживает Windows) и `NSSM` (Non-Sucking Service Manager),
чтобы приложение работало как служба Windows и поднималось при перезагрузке.

### 1. Установите Python и зависимости

Установите Python 3.10+ с python.org (отметьте галочку «Add to PATH» при
установке), затем в PowerShell:

```powershell
cd C:\equipment_system
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install waitress
```

### 2. Задайте переменные окружения и подготовьте базу

```powershell
$env:DJANGO_SECRET_KEY = "замените-на-длинную-случайную-строку"
$env:DJANGO_DEBUG = "False"
$env:DJANGO_ALLOWED_HOSTS = "192.168.1.50,equipment.internal"

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Чтобы эти переменные сохранялись между перезапусками, задайте их как
постоянные переменные окружения Windows (Панель управления → Система →
Дополнительные параметры системы → Переменные среды), а не только в текущей
сессии PowerShell.

### 3. Создайте скрипт запуска `run_server.py`

```python
from waitress import serve
from equipment_system.wsgi import application

if __name__ == "__main__":
    serve(application, host="0.0.0.0", port=80)
```

Проверьте вручную: `python run_server.py`, затем откройте
`http://localhost/` с другого компьютера в сети по IP сервера.

### 4. Установите как службу Windows через NSSM

Скачайте [NSSM](https://nssm.cc/download), затем в PowerShell (от имени
администратора):

```powershell
nssm install EquipmentSystem "C:\equipment_system\venv\Scripts\python.exe" "C:\equipment_system\run_server.py"
nssm set EquipmentSystem AppDirectory "C:\equipment_system"
nssm start EquipmentSystem
```

Теперь система будет автоматически запускаться вместе с сервером и
перезапускаться при сбое.

---

## После разворачивания без Docker (варианты A и B)

1. Зайдите на `http://<адрес-сервера>/admin/`, войдите под учёткой,
   созданной через `createsuperuser`, и заполните справочники
   (подразделения, кабинеты, сотрудников, категории, статусы).
2. Там же, в «Users» → «Add user», заведите учётные записи для остальных
   сотрудников (флаг «Staff status» им, как правило, не нужен — он даёт
   доступ в `/admin/`, а не в основной интерфейс).
3. Дайте сотрудникам ссылку на `http://<адрес-сервера>/` — при заходе
   система попросит войти по логину и паролю.
4. Настройте регулярный бэкап (см. ниже) — на сервере это особенно важно.

## Резервное копирование без Docker

В проекте есть готовая команда:

```bash
python manage.py backup_db
```

Она копирует `db.sqlite3` в папку `backups/` с меткой даты и времени и
сама удаляет копии старше 30 последних (можно поменять: `--keep 60`).

**Поставьте её на расписание:**

- **Linux (cron):** `crontab -e` и добавьте строку (бэкап каждый день в 2 ночи):
  ```
  0 2 * * * cd /opt/equipment_system && venv/bin/python manage.py backup_db >> /var/log/equipment_backup.log 2>&1
  ```
- **Windows (Планировщик заданий):** создайте задачу с триггером «Ежедневно»,
  действие — запуск программы `C:\equipment_system\venv\Scripts\python.exe`
  с аргументами `manage.py backup_db` и рабочей папкой `C:\equipment_system`.

Дополнительно периодически копируйте папку `backups/` (и саму базу) на
отдельный носитель или в облако — локальные копии на том же диске не
защищают от отказа самого сервера.

## Обновление системы без Docker в будущем

Если понадобится обновить код (новые функции, исправления):

```bash
# остановите службу
sudo systemctl stop equipment-system      # Linux
# или nssm stop EquipmentSystem            # Windows

# сделайте бэкап на всякий случай
python manage.py backup_db

# замените файлы кода (кроме db.sqlite3, media/, .env — их не трогайте)
# затем:
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# запустите службу обратно
sudo systemctl start equipment-system     # Linux
# или nssm start EquipmentSystem           # Windows
```
