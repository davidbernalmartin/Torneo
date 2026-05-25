"""
PDF de detalle de grupos: lista de equipos + calendario de partidos.
Estilo coherente con el resto de PDFs de la aplicación.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img as _fetch, draw_shield_centered as _shield_centered, RFFM_LOGO_URL, LIGHT_BG, BORDER

# ── Paleta ─────────────────────────────────────────────────────────────────────
RED      = HexColor("#CC0000")
RED_DARK = HexColor("#990000")
DARK     = HexColor("#1A1A1A")
MUTED    = HexColor("#888888")
WHITE    = white

# ── Dimensiones ────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN  = 30
CARD_W  = PAGE_W - 2 * MARGIN

HDR_H   = 36
GRP_H   = 24
TEAM_H  = 26
TSHIELD = 18
CORNER  = 6
STRIP_W = 5
IGAP    = 5
GGAP    = 14


def _shield(c, img, fallback, cx, cy, size):
    _shield_centered(c, img, fallback, cx, cy, size)


def _fit(c, text, font, max_sz, max_w):
    sz = max_sz
    while sz >= 6 and c.stringWidth(text, font, sz) > max_w:
        sz -= 0.5
    if c.stringWidth(text, font, sz) > max_w:
        t = text
        while t and c.stringWidth(t + "…", font, sz) > max_w:
            t = t[:-1]
        text = t + "…"
    return text, sz


def _draw_page_header(c, titulo):
    hx, hy = MARGIN, PAGE_H - MARGIN - HDR_H
    c.setFillColor(RED)
    c.roundRect(hx, hy, CARD_W, HDR_H, 6, fill=1, stroke=0)
    c.setFillColor(RED_DARK)
    c.roundRect(hx, hy, STRIP_W + 4, HDR_H, 6, fill=1, stroke=0)
    c.rect(hx + 3, hy, STRIP_W + 1, HDR_H, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    t = titulo.upper()
    max_w = CARD_W - 180
    while t and c.stringWidth(t, "Helvetica-Bold", 13) > max_w:
        t = t[:-1]
    c.drawString(hx + STRIP_W + 10, hy + 12, t)
    c.setFont("Helvetica", 8)
    c.drawRightString(hx + CARD_W - 12, hy + 12, "DETALLE DE GRUPOS")


def _draw_group_header(c, x, y, nombre, n_equipos):
    c.setFillColor(RED)
    c.roundRect(x, y, CARD_W, GRP_H, CORNER, fill=1, stroke=0)
    c.setFillColor(RED_DARK)
    c.roundRect(x, y, STRIP_W + 4, GRP_H, CORNER, fill=1, stroke=0)
    c.rect(x + 3, y, STRIP_W + 1, GRP_H, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + STRIP_W + 10, y + 7.5, nombre.upper())
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#FFAAAA"))
    lbl = f"{n_equipos} equipo{'s' if n_equipos != 1 else ''}"
    c.drawRightString(x + CARD_W - 10, y + 7.5, lbl)


def _draw_team_list(c, x, y, equipos, cache, rffm):
    card_h = len(equipos) * TEAM_H + 8
    c.setFillColor(WHITE)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.6)
    c.roundRect(x, y - card_h, CARD_W, card_h, CORNER, fill=1, stroke=1)

    cy = y - 4
    for eq in equipos:
        cy -= TEAM_H
        mid_y = cy + TEAM_H / 2

        if eq != equipos[0]:
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.4)
            c.line(x + 10, cy + TEAM_H, x + CARD_W - 10, cy + TEAM_H)

        img = _fetch(eq.get("escudo_url"), cache)
        _shield(c, img, rffm, x + 24, mid_y, TSHIELD)

        nom = eq.get("nombre") or "Plaza vacía"
        nom, sz = _fit(c, nom, "Helvetica-Bold", 10.5, CARD_W - 50)
        c.setFillColor(DARK if eq.get("nombre") else MUTED)
        c.setFont("Helvetica-Bold" if eq.get("nombre") else "Helvetica-Oblique", sz)
        c.drawString(x + 38, mid_y - sz / 2, nom)

    return card_h


def generar_pdf_grupos(fases_data: list, titulo: str) -> bytes:
    """
    fases_data: lista de dicts {fase_nombre, fase_orden, grupos: [{nombre, tipo_grupo, equipos, partidos}]}
    """
    import io
    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(titulo)
    c.setAuthor("Gestor Torneos RFFM")

    cache = {}
    rffm  = _fetch(RFFM_LOGO_URL, cache)

    def new_page():
        c.showPage()
        _draw_page_header(c, titulo)
        return PAGE_H - MARGIN - HDR_H - 10

    _draw_page_header(c, titulo)
    y = PAGE_H - MARGIN - HDR_H - 10

    for fase in fases_data:
        for gi, grupo in enumerate(fase["grupos"]):
            if gi > 0:
                y -= GGAP

            n_eq = grupo["tipo_grupo"] or len(grupo["equipos"])
            team_card_h = len(grupo["equipos"]) * TEAM_H + 8

            needed = GRP_H + IGAP + team_card_h
            if y - needed < MARGIN:
                y = new_page()

            _draw_group_header(c, MARGIN, y - GRP_H, grupo["nombre"], n_eq)
            y -= GRP_H + IGAP

            th = _draw_team_list(c, MARGIN, y, grupo["equipos"], cache, rffm)
            y -= th

    c.save()
    return buf.getvalue()
