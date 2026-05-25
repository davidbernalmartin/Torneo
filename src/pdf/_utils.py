"""Shared utilities for all PDF generation modules."""
import io
import hashlib
import urllib.request

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

RFFM_LOGO_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"

LIGHT_BG = HexColor("#F7F7F7")
BORDER   = HexColor("#E0E0E0")

# Misma paleta que components.py pero como objetos HexColor para reportlab — 32 colores
_PDF_TORNEO_COLORS: list[tuple[HexColor, HexColor]] = [
    # ── Rojo → Carmesí ───────────────────────────────────────────────────────
    (HexColor("#FEE2E2"), HexColor("#DC2626")),  #  1 rojo
    (HexColor("#FFF0E8"), HexColor("#C2410C")),  #  2 bermellón
    (HexColor("#FECDD3"), HexColor("#9F1239")),  #  3 carmesí
    (HexColor("#FFE4E6"), HexColor("#E11D48")),  #  4 rosa-rojo
    # ── Rosa → Fucsia ────────────────────────────────────────────────────────
    (HexColor("#FCE7F3"), HexColor("#DB2777")),  #  5 rosa
    (HexColor("#FDF4FF"), HexColor("#D946EF")),  #  6 fucsia
    (HexColor("#FAE8FF"), HexColor("#A855F8")),  #  7 morado claro
    (HexColor("#F3E8FF"), HexColor("#7C3AED")),  #  8 violeta
    # ── Índigo → Azul ────────────────────────────────────────────────────────
    (HexColor("#E9D5FF"), HexColor("#5B21B6")),  #  9 violeta oscuro
    (HexColor("#E0E7FF"), HexColor("#4F46E5")),  # 10 índigo
    (HexColor("#C7D2FE"), HexColor("#3730A3")),  # 11 índigo oscuro
    (HexColor("#DBEAFE"), HexColor("#2563EB")),  # 12 azul
    # ── Azul → Cielo ─────────────────────────────────────────────────────────
    (HexColor("#BFDBFE"), HexColor("#1E40AF")),  # 13 azul oscuro
    (HexColor("#E0F2FE"), HexColor("#0284C7")),  # 14 cielo
    (HexColor("#BAE6FD"), HexColor("#075985")),  # 15 cielo oscuro
    (HexColor("#CFFAFE"), HexColor("#0891B2")),  # 16 ciano
    # ── Ciano → Verde ────────────────────────────────────────────────────────
    (HexColor("#CCFBF1"), HexColor("#0D9488")),  # 17 verde-azulado
    (HexColor("#99F6E4"), HexColor("#0F766E")),  # 18 verde-azulado oscuro
    (HexColor("#D1FAE5"), HexColor("#059669")),  # 19 esmeralda
    (HexColor("#DCFCE7"), HexColor("#16A34A")),  # 20 verde
    # ── Verde → Lima ─────────────────────────────────────────────────────────
    (HexColor("#BBF7D0"), HexColor("#14532D")),  # 21 verde oscuro
    (HexColor("#ECFCCB"), HexColor("#65A30D")),  # 22 lima
    (HexColor("#FEF9C3"), HexColor("#A16207")),  # 23 amarillo
    (HexColor("#FEF3C7"), HexColor("#D97706")),  # 24 ámbar
    # ── Ámbar → Naranja ──────────────────────────────────────────────────────
    (HexColor("#FDE68A"), HexColor("#92400E")),  # 25 ámbar oscuro
    (HexColor("#FFEDD5"), HexColor("#EA580C")),  # 26 naranja
    (HexColor("#FED7AA"), HexColor("#9A3412")),  # 27 naranja oscuro
    (HexColor("#FFEBE6"), HexColor("#E05A38")),  # 28 coral
    # ── Especiales ───────────────────────────────────────────────────────────
    (HexColor("#FFE0D8"), HexColor("#B43A22")),  # 29 coral oscuro
    (HexColor("#F1F5F9"), HexColor("#334155")),  # 30 pizarra
    (HexColor("#FFF7ED"), HexColor("#78350F")),  # 31 marrón cálido
    (HexColor("#F0FDF4"), HexColor("#166534")),  # 32 verde bosque
]


def torneo_pdf_color(torneo_id: str | None) -> tuple[HexColor, HexColor]:
    """Devuelve (bg, border) HexColor únicos y consistentes para un torneo."""
    if not torneo_id:
        from reportlab.lib.colors import white
        return white, BORDER
    h = int(hashlib.md5(torneo_id.encode()).hexdigest(), 16)
    return _PDF_TORNEO_COLORS[h % len(_PDF_TORNEO_COLORS)]


def fetch_img(url: str | None, cache: dict) -> ImageReader | None:
    if not url:
        return None
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read()
        img = ImageReader(io.BytesIO(data))
        cache[url] = img
        return img
    except Exception:
        cache[url] = None
        return None


def draw_shield_centered(c, img, fallback, cx: float, cy: float, size: float):
    """Draw a shield image centered at (cx, cy). Falls back to a grey placeholder."""
    x, y = cx - size / 2, cy - size / 2
    target = img or fallback
    if target:
        try:
            c.drawImage(target, x, y, size, size, preserveAspectRatio=True, mask="auto")
            return
        except Exception:
            pass
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(x, y, size, size, 4, fill=1, stroke=1)
