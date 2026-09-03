"""
Генератор маленькой печатной "бирки" для наклейки на оборудование:
инвентарный номер, наименование, ответственный + QR-код с инвентарным
номером (чтобы можно было быстро найти оборудование через поиск в реестре).
"""
import io
import os

import qrcode
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


def generate_equipment_label(equipment) -> io.BytesIO:
    """Возвращает BytesIO с готовым PDF-файлом одной бирки (90x50 мм)."""
    _ensure_fonts_registered()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    margin = 4 * mm
    qr_size = LABEL_HEIGHT - 2 * margin

    qr_image = _make_qr_image(equipment.inventory_number)
    c.drawImage(
        qr_image, margin, margin, width=qr_size, height=qr_size,
        preserveAspectRatio=True, mask="auto",
    )

    text_x = margin + qr_size + 4 * mm
    text_width = LABEL_WIDTH - text_x - margin

    c.setFont("DejaVuSans-Bold", 13)
    c.drawString(text_x, LABEL_HEIGHT - margin - 12, equipment.inventory_number)

    c.setFont("DejaVuSans", 9)
    name_line = equipment.name
    if len(name_line) > 20:
        name_line = name_line[:19] + "…"
    c.drawString(text_x, LABEL_HEIGHT - margin - 24, name_line)

    if equipment.model:
        model_line = equipment.model
        if len(model_line) > 22:
            model_line = model_line[:21] + "…"
        c.setFont("DejaVuSans", 8)
        c.drawString(text_x, LABEL_HEIGHT - margin - 34, model_line)

    c.setFont("DejaVuSans", 8)
    responsible = str(equipment.responsible_employee) if equipment.responsible_employee else "—"
    responsible_line = f"Отв.: {responsible}"
    if len(responsible_line) > 22:
        responsible_line = responsible_line[:21] + "…"
    c.drawString(text_x, margin + 2, responsible_line)

    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.setLineWidth(0.5)
    c.rect(1 * mm, 1 * mm, LABEL_WIDTH - 2 * mm, LABEL_HEIGHT - 2 * mm)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
