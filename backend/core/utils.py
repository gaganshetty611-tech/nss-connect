import math
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres. Returns None if any coordinate is missing."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def frontend_base_url(request=None):
    """Public URL of the SPA, used for links in QR codes and emails."""
    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL
    if request is not None:
        origin = request.headers.get("Origin")
        if origin and origin != "null":
            return origin.rstrip("/")
        return request.build_absolute_uri("/").rstrip("/")
    return "http://localhost:5173"


def event_window(event):
    """Aware (start, end) datetimes for an event; end rolls to next day if it is before start."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(event.date, event.start_time), tz)
    end = timezone.make_aware(datetime.combine(event.date, event.end_time), tz)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def extract_exif_gps(uploaded_file):
    """
    Read GPS coordinates out of a photo's EXIF metadata, if present, as a
    fallback for when the browser's Geolocation API wasn't available or the
    photo was uploaded from a file picker instead of taken live. Returns
    (latitude, longitude) as floats, or (None, None) if there's no GPS tag,
    the file isn't a JPEG/TIFF with EXIF, or anything about it can't be read —
    this must never raise, since a missing geotag is not an upload error.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        exif = image.getexif()
        uploaded_file.seek(0)
        if not exif:
            return None, None

        gps_info = {}
        for tag_id, value in exif.get_ifd(0x8825).items():  # 0x8825 = GPSInfo IFD
            gps_info[GPSTAGS.get(tag_id, tag_id)] = value

        def to_degrees(dms, ref):
            degrees = float(dms[0]) + float(dms[1]) / 60 + float(dms[2]) / 3600
            if ref in ("S", "W"):
                degrees = -degrees
            return degrees

        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = to_degrees(gps_info["GPSLatitude"], gps_info.get("GPSLatitudeRef", "N"))
            lon = to_degrees(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))
            return round(lat, 6), round(lon, 6)
    except Exception:
        pass
    return None, None
