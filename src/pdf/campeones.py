"""
PDF de campeones y subcampeones por torneo.
Una tarjeta por torneo con el color del torneo: título, 🥇 campeón, 🥈 subcampeón.
"""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img, draw_shield_centered, torneo_pdf_color, RFFM_LOGO_URL

PAGE_W, PAGE_H = A4
MARGIN   = 24
HDR_H    = 36
COLS     = 2
GAP      = 14
CARD_W   = (PAGE_W - 2 * MARGIN - (COLS - 1) * GAP) / COLS
CARD_H   = 148
CORNER   = 8
SHIELD_S = 40
NAME_SZ  = 9.5
ROW_H    = CARD_H / 2   # mitad para campeón, mitad para subcampeón

DARK     = HexColor("#1A1A1A")
MUTED    = HexColor("#888888")
RED      = HexColor("#CC0000")
GOLD     = HexColor("#D97706")
SILVER   = HexColor("#6B7280")


def _trunc(c, text: str, font: str, size: float, max_w: float) -> str:
    while text and c.stringWidth(text, font, size) > max_w:
        text = text[:-1]
    return text


def _draw_page_header(c, titulo: str):
    hx = MARGIN
    hy = PAGE_H - MARGIN - HDR_H
    hw = PAGE_W - 2 * MARGIN
    c.setFillColor(RED)
    c.roundRect(hx, hy, hw, HDR_H, 6, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W / 2, hy + 12, titulo.upper())


def _draw_card(c, x: float, y: float, datos: dict, img_cache: dict, rffm_logo):
    bg, border = torneo_pdf_color(datos["torneo_id"])
    nombre_torneo = datos["torneo_nombre"]
    campeon    = datos.get("campeon")
    subcampeon = datos.get("subcampeon")

    # ── Fondo ──────────────────────────────────────────────────────────────────
    c.setFillColor(bg)
    c.setStrokeColor(border)
    c.setLineWidth(1.0)
    c.roundRect(x, y, CARD_W, CARD_H, CORNER, fill=1, stroke=0)

    # ── Barra superior con nombre del torneo ───────────────────────────────────
    BAR_H = 18
    top_y = y + CARD_H - BAR_H
    c.setFillColor(border)
    c.rect(x + CORNER, top_y, CARD_W - 2 * CORNER, BAR_H, fill=1, stroke=0)
    c.roundRect(x, top_y, CARD_W, BAR_H, CORNER, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7.5)
    label = _trunc(c, nombre_torneo.upper(), "Helvetica-Bold", 7.5, CARD_W - 12)
    c.drawCentredString(x + CARD_W / 2, top_y + 5.5, label)

    # ── Borde exterior ─────────────────────────────────────────────────────────
    c.setStrokeColor(border)
    c.setLineWidth(1.0)
    c.roundRect(x, y, CARD_W, CARD_H, CORNER, fill=0, stroke=1)

    content_top = top_y         # base de la barra del torneo
    content_bot = y + 6          # margen inferior
    content_h   = content_top - content_bot

    row_h = content_h / 2

    for idx, (eq, medal_color, medal_text, rank_label) in enumerate([
        (campeon,    GOLD,   "1°", "CAMPEÓN"),
        (subcampeon, SILVER, "2°", "SUBCAMPEÓN"),
    ]):
        row_y = content_bot + (1 - idx) * row_h  # 1-idx: campeón arriba

        # Separador entre filas
        if idx == 1:
            c.setStrokeColor(border)
            c.setLineWidth(0.4)
            c.line(x + 10, row_y + row_h, x + CARD_W - 10, row_y + row_h)

        cx_mid = x + CARD_W / 2
        cy_mid = row_y + row_h / 2

        if eq:
            # Escudo centrado verticalmente en la mitad izquierda
            shield_x = x + 14 + SHIELD_S / 2
            img = fetch_img(eq.get("escudo_url"), img_cache)
            draw_shield_centered(c, img, rffm_logo, shield_x, cy_mid, SHIELD_S)

            # Nombre
            nombre = eq.get("nombre", "")
            max_w  = CARD_W - (14 + SHIELD_S + 8 + 8)  # espacio derecha del escudo
            text_x = x + 14 + SHIELD_S + 8

            c.setFont("Helvetica-Bold", NAME_SZ)
            words  = nombre.split()
            line1  = line2 = ""
            for i in range(len(words), 0, -1):
                candidate = " ".join(words[:i])
                if c.stringWidth(candidate, "Helvetica-Bold", NAME_SZ) <= max_w:
                    line1 = candidate
                    rest  = " ".join(words[i:])
                    line2 = _trunc(c, rest, "Helvetica-Bold", NAME_SZ, max_w) if rest else ""
                    break
            if not line1:
                line1 = _trunc(c, nombre, "Helvetica-Bold", NAME_SZ, max_w)

            lines = [l for l in [line1, line2] if l]
            total_text_h = len(lines) * 11 + 10  # líneas + etiqueta
            text_base_y  = cy_mid + total_text_h / 2 - 11

            c.setFillColor(medal_color)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawString(text_x, text_base_y + 12, rank_label)

            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", NAME_SZ)
            for li, line in enumerate(lines):
                c.drawString(text_x, text_base_y - li * 11, line)

        else:
            # Sin datos: placeholder centrado
            c.setFillColor(medal_color)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawCentredString(cx_mid, cy_mid + 6, rank_label)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(cx_mid, cy_mid - 4, "Sin determinar")


def generar_pdf_campeones(datos: list[dict], titulo: str = "Campeones y Subcampeones") -> bytes:
    """
    datos: lista de dicts con keys torneo_id, torneo_nombre, campeon, subcampeon.
    campeon/subcampeon son dicts {nombre, escudo_url} o None.
    """
    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(titulo)
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}
    rffm_logo = fetch_img(RFFM_LOGO_URL, img_cache)

    _draw_page_header(c, titulo)
    grid_top = PAGE_H - MARGIN - HDR_H - 10
    col_i, row_y = 0, grid_top

    for datos_torneo in datos:
        cx = MARGIN + col_i * (CARD_W + GAP)
        cy = row_y - CARD_H

        if cy < MARGIN:
            c.showPage()
            _draw_page_header(c, titulo)
            row_y = PAGE_H - MARGIN - HDR_H - 10
            col_i = 0
            cx    = MARGIN
            cy    = row_y - CARD_H

        _draw_card(c, cx, cy, datos_torneo, img_cache, rffm_logo)

        col_i += 1
        if col_i >= COLS:
            col_i  = 0
            row_y -= CARD_H + GAP

    c.save()
    return buf.getvalue()
