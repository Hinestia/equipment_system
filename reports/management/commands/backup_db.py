"""
Простая команда резервного копирования: копирует db.sqlite3 в папку backups/
с меткой даты и времени в имени файла. Запуск вручную:
    python manage.py backup_db
Можно поставить в планировщик задач (cron / Планировщик заданий Windows),
чтобы бэкап делался автоматически, например, каждый день ночью.
"""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Создаёт резервную копию базы данных SQLite в папке backups/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", type=int, default=30,
            help="Сколько последних резервных копий хранить (старые удаляются). По умолчанию 30.",
        )

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES["default"]["NAME"])
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Файл базы данных не найден: {db_path}"))
            return

        backup_dir = Path(settings.DATA_DIR) / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = backup_dir / f"db_{timestamp}.sqlite3"
        shutil.copy2(db_path, backup_path)
        self.stdout.write(self.style.SUCCESS(f"Резервная копия создана: {backup_path}"))

        keep = options["keep"]
        backups = sorted(backup_dir.glob("db_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_backup in backups[keep:]:
            old_backup.unlink()
            self.stdout.write(f"Удалена старая резервная копия: {old_backup.name}")
