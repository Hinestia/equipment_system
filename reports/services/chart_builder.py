"""
Строит данные для мини-графика "Движение оборудования" на дашборде:
количество событий истории по месяцам за последние N месяцев, в виде
SVG-пути (area+line), без JS-библиотек графиков — просто заранее
посчитанная геометрия, встраиваемая в шаблон.
"""
import calendar
from datetime import date

MONTH_LABELS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

CHART_WIDTH = 460
CHART_HEIGHT = 160
CHART_TOP_PADDING = 20


def _add_months(d: date, delta: int) -> date:
    month = d.month - 1 + delta
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def build_movement_chart(monthly_counts, months_count=9):
    """
    monthly_counts: список последних months_count элементов вида
    {"label": "ноя", "count": 12}, в хронологическом порядке (старые -> новые).
    Возвращает dict с готовым SVG path для линии, path для area-заливки,
    координатами пиковой точки и подписями месяцев.
    """
    counts = [m["count"] for m in monthly_counts]
    max_count = max(counts) if counts and max(counts) > 0 else 1
    n = len(monthly_counts)

    step_x = CHART_WIDTH / (n - 1) if n > 1 else CHART_WIDTH

    points = []
    for i, count in enumerate(counts):
        x = round(i * step_x, 1)
        # инвертируем ось Y (0 наверху в SVG) и оставляем отступ сверху под подсказку
        y = round(CHART_HEIGHT - (count / max_count) * (CHART_HEIGHT - CHART_TOP_PADDING), 1)
        points.append((x, y))

    if not points:
        return {
            "line_path": "", "area_path": "", "peak": None, "labels": [], "has_data": False,
        }

    line_path = "M" + " L".join(f"{x} {y}" for x, y in points)
    area_path = line_path + f" L{points[-1][0]} {CHART_HEIGHT} L0 {CHART_HEIGHT} Z"

    peak_index = max(range(n), key=lambda i: counts[i])
    peak_point = points[peak_index]
    peak_count = counts[peak_index]

    return {
        "line_path": line_path,
        "area_path": area_path,
        "peak": {"x": peak_point[0], "y": peak_point[1], "count": peak_count, "label": monthly_counts[peak_index]["label"]},
        "labels": [m["label"] for m in monthly_counts],
        "has_data": any(c > 0 for c in counts),
        "width": CHART_WIDTH,
        "height": CHART_HEIGHT,
    }


def last_n_months_labels(n=9, today=None):
    """Возвращает список последних n месяцев (от старых к новым) в виде (год, месяц, подпись)."""
    today = today or date.today()
    first_of_this_month = date(today.year, today.month, 1)
    months = []
    for i in range(n - 1, -1, -1):
        d = _add_months(first_of_this_month, -i)
        months.append((d.year, d.month, MONTH_LABELS_RU[d.month - 1]))
    return months


def gauge_arc_endpoint(pct, cx=75, cy=78, r=63):
    """
    Точка на полукруглой дуге индикатора (0% — крайняя левая точка дуги,
    100% — крайняя правая), для отрисовки прогресса SVG-дугой A r r 0 0 1 x y.
    """
    import math
    pct = max(0, min(100, pct))
    theta_deg = 180 - (pct / 100) * 180
    theta_rad = math.radians(theta_deg)
    x = round(cx + r * math.cos(theta_rad), 1)
    y = round(cy - r * math.sin(theta_rad), 1)
    return x, y
