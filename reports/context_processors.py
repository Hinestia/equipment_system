"""
Отдаёт информацию о последней резервной копии базы во ВСЕ шаблоны —
нужна для виджета в сайдбаре, который показывается на каждой странице,
а не только на дашборде.
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings


def backup_status(request):
    backup_dir = Path(settings.DATA_DIR) / "backups"
    if not backup_dir.exists():
        return {"last_backup": None, "backup_freshness_pct": 0}

    backups = sorted(backup_dir.glob("db_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return {"last_backup": None, "backup_freshness_pct": 0}

    latest = backups[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age_days = (datetime.now() - mtime).total_seconds() / 86400
    # "Свежесть" — 100%, если бэкап сегодня, линейно падает до 0% за 7 дней без бэкапа.
    freshness_pct = max(0, round(100 - (age_days / 7) * 100))

    return {"last_backup": mtime, "backup_freshness_pct": freshness_pct}
