"""Upload validation: extension, size, declared MIME type and real file signature."""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
PIL_FORMATS = {"JPEG", "PNG", "WEBP"}

DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
DOCUMENT_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}

# Extensions that must never be accepted, even if renamed.
BLOCKED_SIGNATURES = (b"MZ", b"\x7fELF", b"#!", b"PK\x03\x04")


def _ext(name):
    return os.path.splitext(name or "")[1].lower()


def _head(f, n=16):
    pos = f.tell() if hasattr(f, "tell") else 0
    f.seek(0)
    data = f.read(n)
    f.seek(pos)
    return data


def _declared_mime(f):
    return getattr(f, "content_type", None)


def validate_image_file(f):
    ext = _ext(f.name)
    if ext not in IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported image extension '{ext}'. Allowed: {', '.join(sorted(IMAGE_EXTENSIONS))}.")
    if f.size > settings.MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError(f"Image too large (max {settings.MAX_IMAGE_UPLOAD_SIZE // (1024 * 1024)} MB).")
    mime = _declared_mime(f)
    if mime and mime not in IMAGE_MIME_TYPES:
        raise ValidationError(f"Unsupported image type '{mime}'.")
    try:
        pos = f.tell()
        f.seek(0)
        img = Image.open(f)
        fmt = img.format
        img.verify()  # detects truncated / non-image payloads
        f.seek(pos)
    except Exception:
        raise ValidationError("Uploaded file is not a valid image.")
    if fmt not in PIL_FORMATS:
        raise ValidationError(f"Unsupported image format '{fmt}'.")


def validate_document_file(f):
    ext = _ext(f.name)
    if ext not in DOCUMENT_EXTENSIONS:
        raise ValidationError(f"Unsupported document extension '{ext}'. Allowed: PDF, JPG, PNG.")
    if f.size > settings.MAX_DOCUMENT_UPLOAD_SIZE:
        raise ValidationError(f"Document too large (max {settings.MAX_DOCUMENT_UPLOAD_SIZE // (1024 * 1024)} MB).")
    mime = _declared_mime(f)
    if mime and mime not in DOCUMENT_MIME_TYPES:
        raise ValidationError(f"Unsupported document type '{mime}'.")
    head = _head(f)
    if any(head.startswith(sig) for sig in BLOCKED_SIGNATURES):
        raise ValidationError("Executable or archive content is not allowed.")
    if ext == ".pdf":
        if not head.startswith(b"%PDF-"):
            raise ValidationError("File content is not a PDF.")
    else:
        if not (head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8\xff")):
            raise ValidationError("File content does not match an image type.")
        try:
            pos = f.tell()
            f.seek(0)
            Image.open(f).verify()
            f.seek(pos)
        except Exception:
            raise ValidationError("Uploaded file is not a valid image.")


@deconstructible
class SafeUploadTo:
    """Generate random, non-guessable file names: <folder>/<uuid><ext>."""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = _ext(filename)
        if not ext or len(ext) > 6 or not ext[1:].isalnum():
            ext = ""
        return f"{self.folder}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, SafeUploadTo) and other.folder == self.folder
