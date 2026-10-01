"""Certificate PDF generation (ReportLab) with an embedded verification QR code."""
import io

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from core.utils import frontend_base_url

from .models import Certificate

NAVY = colors.HexColor("#1e1b4b")
PURPLE = colors.HexColor("#6d28d9")
BLUE = colors.HexColor("#2563eb")
MUTED = colors.HexColor("#64748b")


def _qr_image(data):
    qr = qrcode.QRCode(box_size=8, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def render_certificate_pdf(cert):
    event = cert.event
    volunteer = cert.volunteer
    buf = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(f"NSS Connect Certificate {cert.certificate_id}")
    c.setAuthor("NSS Connect")

    # Frame
    c.setStrokeColor(PURPLE)
    c.setLineWidth(4)
    c.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm)
    c.setStrokeColor(BLUE)
    c.setLineWidth(1)
    c.rect(16 * mm, 16 * mm, width - 32 * mm, height - 32 * mm)

    # Header band
    c.setFillColor(PURPLE)
    c.rect(16 * mm, height - 48 * mm, width - 32 * mm, 32 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height - 32 * mm, "NSS Connect")
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 41 * mm, "Volunteer–NGO Matching & Verified ABP Tracking")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 66 * mm, "Certificate of Volunteer Participation")

    c.setFont("Helvetica", 13)
    c.setFillColor(MUTED)
    c.drawCentredString(width / 2, height - 80 * mm, "This is to certify that")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 95 * mm, volunteer.display_name)

    c.setFont("Helvetica", 13)
    c.setFillColor(MUTED)
    c.drawCentredString(width / 2, height - 108 * mm, "has successfully completed verified volunteering at")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 17)
    title = event.title if len(event.title) <= 70 else event.title[:67] + "..."
    c.drawCentredString(width / 2, height - 120 * mm, title)

    c.setFont("Helvetica", 12)
    c.setFillColor(NAVY)
    details = [
        ("Organizer", event.organizer_display),
        ("Date", event.date.strftime("%d %B %Y")),
        ("Category", event.get_category_display()),
        ("Volunteer Hours", f"{cert.hours:.2f}"),
    ]
    x0 = width / 2 - 95 * mm
    for i, (label, value) in enumerate(details):
        x = x0 + i * 50 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + 20 * mm, height - 138 * mm, label.upper())
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        val = value if len(value) <= 28 else value[:26] + "…"
        c.drawCentredString(x + 20 * mm, height - 145 * mm, val)

    # Footer: certificate id + QR
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(24 * mm, 30 * mm, f"Certificate ID: {cert.certificate_id}")
    c.drawString(24 * mm, 25 * mm, f"Issued: {cert.issued_at:%d %b %Y}")
    c.drawString(24 * mm, 20 * mm, "Attendance verified by QR check-in/out and post-event feedback.")
    c.drawImage(_qr_image(cert.verify_url), width - 58 * mm, 20 * mm, 34 * mm, 34 * mm)
    c.drawRightString(width - 24 * mm, 17 * mm, "Scan to verify")

    c.showPage()
    c.save()
    return buf.getvalue()


@transaction.atomic
def generate_certificate(volunteer, event, hours, request=None):
    """Create (or return existing) certificate and its PDF. Idempotent per (volunteer, event)."""
    cert, created = Certificate.objects.get_or_create(volunteer=volunteer, event=event, defaults={"hours": hours})
    if not created and cert.pdf_file:
        return cert, False
    cert.hours = hours
    cert.verify_url = f"{frontend_base_url(request)}/certificate/{cert.certificate_id}/verify"
    cert.save()
    cert.refresh_from_db()  # populate issued_at
    pdf = render_certificate_pdf(cert)
    cert.pdf_file.save(f"{cert.certificate_id}.pdf", ContentFile(pdf), save=True)
    return cert, created
