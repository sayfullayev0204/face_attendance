# courses/utils.py — 100% ISHLAYDI (Windows + O‘zbekcha + Bold)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.core.files import File
from django.urls import reverse
from django.conf import settings
import qrcode
from io import BytesIO
import os

# Yo‘lni aniq ko‘rsatamiz
FONT_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')

# Shriftlarni ro‘yxatdan o‘tkazamiz (xato bo‘lsa ham ishlaydi)
try:
    pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVu-Oblique', os.path.join(FONT_DIR, 'DejaVuSans-Oblique.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVu-BoldOblique', os.path.join(FONT_DIR, 'DejaVuSans-BoldOblique.ttf')))
    print("Barcha DejaVu shriftlari muvaffaqiyatli yuklandi!")
except Exception as e:
    print(f"Shrift yuklashda xato: {e}")
    # Agar xato bo‘lsa ham — ishlaydi (fallback bilan)

def generate_certificate_pdf(certificate):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Fon va ramka
    c.setFillColor(HexColor("#f8f9fa"))
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#d4af37"))
    c.setLineWidth(15)
    c.rect(30, 30, width-60, height-60, stroke=1, fill=0)

    # Sarlavha
    c.setFillColor(HexColor("#b8860b"))
    try:
        c.setFont("DejaVu-Bold", 72)
    except:
        c.setFont("Helvetica-Bold", 72)
    c.drawCentredString(width/2, height - 140, "SERTIFIKAT")

    # Izoh matni
    c.setFillColor(HexColor("#333333"))
    try:
        c.setFont("DejaVu", 32)
    except:
        c.setFont("Helvetica", 32)
    c.drawCentredString(width/2, height - 200, "Muvaffaqiyatli yakunlaganligi uchun beriladi")

    # Talaba ismi — ENG MUHIM QISM
    student_name = (
        certificate.student.profile.full_name or
        certificate.student.get_full_name() or
        certificate.student.username
    ).strip()

    c.setFillColor(HexColor("#000080"))
    try:
        c.setFont("DejaVu-Bold", 56)   # Bu yerda xato bo‘lsa ham ishlaydi
        c.drawCentredString(width/2, height - 300, student_name.upper())
    except:
        # Agar DejaVu-Bold ishlamasa — Helvetica bilan yozamiz
        c.setFont("Helvetica-Bold", 56)
        c.drawCentredString(width/2, height - 300, student_name.upper())

    # Kurs nomi
    c.setFillColor(HexColor("#333333"))
    try:
        c.setFont("DejaVu-Bold", 40)
    except:
        c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(width/2, height - 370, f'"{certificate.course.title}" kursi')

    # Baho va sana
    try:
        c.setFont("DejaVu", 30)
    except:
        c.setFont("Helvetica", 30)
    c.setFillColor(HexColor("#006400"))
    c.drawCentredString(width/2, height - 430, f"O'rtacha baho: {certificate.test_score}%")
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(width/2, height - 480, f"Berilgan sana: {certificate.issued_at.strftime('%d.%m.%Y')}")

    # ID
    try:
        c.setFont("DejaVu", 16)
    except:
        c.setFont("Helvetica", 16)
    c.setFillColor(HexColor("#555555"))
    c.drawString(80, 70, f"ID: {str(certificate.certificate_id)[:8].upper()}")

    # QR kod
    verify_url = f"https://phoenix-rapid-factually.ngrok-free.app/verify/{certificate.certificate_id}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), width - 220, 40, width=140, height=140)

    # PDF ni saqlash
    c.showPage()
    c.save()
    buffer.seek(0)
    certificate.pdf_file.save(f"sertifikat_{certificate.certificate_id}.pdf", File(buffer), save=True)
    buffer.close()