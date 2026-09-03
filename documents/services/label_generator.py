"""
Генератор маленькой печатной "бирки" для наклейки на оборудование:
инвентарный номер, наименование, ответственный + QR-код с инвентарным
номером (чтобы можно было быстро найти оборудование через поиск в реестре).
"""
import io
import os

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

# Шрифты DejaVu Sans зарегистрированы явно (а не взяты из системных), чтобы
# кириллица корректно отображалась в PDF независимо от того, какие шрифты
# установлены на сервере/в Docker-образе — DejaVu Sans лежит прямо в проекте.
_FONTS_REGISTERED = False


def _ensure_fonts_registered():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
    _FONTS_REGISTERED = True


LABEL_WIDTH = 90 * mm
LABEL_HEIGHT = 50 * mm


def _make_qr_image(data: str) -> ImageReader:
    qr = qrcode.QRCode(border=1, box_size=6)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_label(c, equipment, x0, y0, width, height, border=True):
    """Рисует одну бирку с левым нижним углом в точке (x0, y0) заданного размера."""
    margin = 4 * mm
    qr_size = height - 2 * margin

    qr_image = _make_qr_image(equipment.inventory_number)
    c.drawImage(
        qr_image, x0 + margin, y0 + margin, width=qr_size, height=qr_size,
        preserveAspectRatio=True, mask="auto",
    )

    text_x = x0 + margin + qr_size + 4 * mm

    c.setFont("DejaVuSans-Bold", 13)
    c.drawString(text_x, y0 + height - margin - 12, equipment.inventory_number)

    c.setFont("DejaVuSans", 9)
    name_line = equipment.name
    if len(name_line) > 20:
        name_line = name_line[:19] + "…"
    c.drawString(text_x, y0 + height - margin - 24, name_line)

    if equipment.model:
        model_line = equipment.model
        if len(model_line) > 22:
            model_line = model_line[:21] + "…"
        c.setFont("DejaVuSans", 8)
        c.drawString(text_x, y0 + height - margin - 34, model_line)

    c.setFont("DejaVuSans", 8)
    responsible = str(equipment.responsible_employee) if equipment.responsible_employee else "—"
    responsible_line = f"Отв.: {responsible}"
    if len(responsible_line) > 22:
        responsible_line = responsible_line[:21] + "…"
    c.drawString(text_x, y0 + margin + 2, responsible_line)

    if border:
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.setLineWidth(0.5)
        c.rect(x0 + 1 * mm, y0 + 1 * mm, width - 2 * mm, height - 2 * mm)


def generate_equipment_label(equipment) -> io.BytesIO:
    """Возвращает BytesIO с готовым PDF-файлом одной бирки (90x50 мм) — отдельная страница нужного размера."""
    _ensure_fonts_registered()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    _draw_label(c, equipment, 0, 0, LABEL_WIDTH, LABEL_HEIGHT)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_label_sheet(equipment_list) -> io.BytesIO:
    """
    Возвращает BytesIO с PDF-листом(-ами) формата A4: несколько бирок
    (сетка 2x5 = 10 штук на странице) для печати на обычном принтере и
    последующей разрезки, либо на самоклеящейся бумаге для этикеток А4.
    Если единиц больше 10 — автоматически добавляются следующие страницы.
    """
    _ensure_fonts_registered()

    PAGE_WIDTH, PAGE_HEIGHT = A4
    cols, rows = 2, 5
    h_gap = 4 * mm
    v_gap = 4 * mm

    grid_width = cols * LABEL_WIDTH + (cols - 1) * h_gap
    grid_height = rows * LABEL_HEIGHT + (rows - 1) * v_gap
    margin_x = (PAGE_WIDTH - grid_width) / 2
    margin_y = (PAGE_HEIGHT - grid_height) / 2

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    per_page = cols * rows
    equipment_list = list(equipment_list)

    for page_start in range(0, len(equipment_list), per_page):
        page_items = equipment_list[page_start:page_start + per_page]
        for idx, equipment in enumerate(page_items):
            col = idx % cols
            row = idx // cols
            x0 = margin_x + col * (LABEL_WIDTH + h_gap)
            # Считаем сверху вниз: первая строка сетки — самая верхняя.
            y0 = PAGE_HEIGHT - margin_y - (row + 1) * LABEL_HEIGHT - row * v_gap
            _draw_label(c, equipment, x0, y0, LABEL_WIDTH, LABEL_HEIGHT)
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer
