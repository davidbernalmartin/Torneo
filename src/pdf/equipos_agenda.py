"""
PDF de equipos participantes en la agenda filtrada.
Tarjetas en rejilla de 4 columnas: barra-campos (arriba) · escudo · nombre · barra-torneo (abajo).
Solo se incluyen equipos que tengan URL de escudo propia.
"""
import io
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img, draw_shield_centered, torneo_pdf_color, RFFM_LOGO_URL

PAGE_W, PAGE_H = A4
MARGIN    = 20
HDR_H     = 32
COLS      = 4
GAP       = 6
CARD_W    = (PAGE_W - 2 * MARGIN - (COLS - 1) * GAP) / COLS
CARD_H    = 98
CORNER    = 5
SHIELD_S  = 24
NAME_SZ   = 7.0
NAME_LEAD = 8.0
BAR_H     = 11    # altura de ambas barras (torneo arriba, campos abajo)
FIELD_H   = 16    # altura de los huecos de escritura
FIELD_R   = 2     # radio de esquina de los huecos

DARK  = HexColor("#1A1A1A")
MUTED = HexColor("#888888")
RED   = HexColor("#CC0000")

_CAMPO_COLORS = [
    HexColor("#1D4ED8"),
    HexColor("#B91C1C"),
    HexColor("#00B944"),
    HexColor("#E45502"),
    HexColor("#886EB3"),
    HexColor("#FF1D99")
]


def _trunc(c, text: str, font: str, size: float, max_w: float) -> str:
    while text and c.stringWidth(text, font, size) > max_w:
        text = text[:-1]
    return text


def _draw_page_header(c, titulo: str):
    hx, hy = MARGIN, PAGE_H - MARGIN - HDR_H
    hw = PAGE_W - 2 * MARGIN
    c.setFillColor(RED)
    c.roundRect(hx, hy, hw, HDR_H, 5, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    t = titulo.upper()
    while t and c.stringWidth(t, "Helvetica-Bold", 12) > hw - 180:
        t = t[:-1]
    c.drawString(hx + 12, hy + 11, t)
    c.setFont("Helvetica", 8)
    c.drawRightString(hx + hw - 12, hy + 11, "EQUIPOS PARTICIPANTES")


def _draw_card(c, x, y, equipo: dict, img_cache: dict, rffm_logo, campo_color_map: dict):
    bg, border = equipo["colors"]
    campos     = equipo["campos"]

    # ── 1. Fondo de la tarjeta ───────────────────────────────────────────────
    c.setFillColor(bg)
    c.setStrokeColor(border)
    c.setLineWidth(0.8)
    c.roundRect(x, y, CARD_W, CARD_H, CORNER, fill=1, stroke=0)

    top_y = y + CARD_H - BAR_H

    # ── 2. Barra superior: torneo (color sólido, texto blanco) ───────────────
    c.setFillColor(border)
    c.rect(x + CORNER, top_y, CARD_W - 2 * CORNER, BAR_H, fill=1, stroke=0)
    c.roundRect(x, top_y, CARD_W, BAR_H, CORNER, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 5.5)
    torneo_label = _trunc(c, equipo["torneo"].upper(), "Helvetica-Bold", 5.5, CARD_W - 8)
    c.drawCentredString(x + CARD_W / 2, top_y + 3.5, torneo_label)

    # ── 3. Barra inferior: campos (segmentada, cada uno en su color) ─────────
    if campos:
        n     = len(campos)
        seg_w = CARD_W / n
        for i, campo in enumerate(campos):
            sx    = x + i * seg_w
            color = campo_color_map.get(campo, MUTED)
            c.setFillColor(color)
            c.rect(sx, y, seg_w, BAR_H, fill=1, stroke=0)

        # Texto blanco en cada segmento
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 5.5)
        for i, campo in enumerate(campos):
            sx    = x + i * seg_w
            label = _trunc(c, campo.upper(), "Helvetica-Bold", 5.5, seg_w - 4)
            c.drawCentredString(sx + seg_w / 2, y + 3.5, label)

        # Enmascarar esquinas inferiores con el fondo de página (blanco)
        c.setFillColor(white)
        c.rect(x,                    y, CORNER, CORNER, fill=1, stroke=0)
        c.rect(x + CARD_W - CORNER, y, CORNER, CORNER, fill=1, stroke=0)
    else:
        c.setFillColor(border)
        c.rect(x + CORNER, y, CARD_W - 2 * CORNER, BAR_H, fill=1, stroke=0)
        c.roundRect(x, y, CARD_W, BAR_H, CORNER, fill=1, stroke=0)

    # ── 4. Borde exterior (encima de todo) ───────────────────────────────────
    c.setStrokeColor(border)
    c.setLineWidth(0.8)
    c.roundRect(x, y, CARD_W, CARD_H, CORNER, fill=0, stroke=1)

    # ── 5. Área de contenido central ─────────────────────────────────────────
    content_bot = y + BAR_H
    inner_w     = CARD_W - 10
    cx_mid      = x + CARD_W / 2
    PAD         = 5   # margen lateral interno

    # ── Escudo anclado bajo la barra del torneo ───────────────────────────────
    shield_cy = top_y - SHIELD_S / 2 - 6
    img = fetch_img(equipo["escudo"], img_cache)
    draw_shield_centered(c, img, rffm_logo, cx_mid, shield_cy, SHIELD_S)

    # ── Nombre — hasta 2 líneas, justo bajo el escudo ────────────────────────
    name_y1 = shield_cy - SHIELD_S / 2 - 10   # baseline de la primera línea
    c.setFont("Helvetica-Bold", NAME_SZ)
    nombre = equipo["nombre"]

    if c.stringWidth(nombre, "Helvetica-Bold", NAME_SZ) <= inner_w:
        lines = [nombre]
    else:
        words = nombre.split()
        line1 = line2 = ""
        for i in range(len(words), 0, -1):
            candidate = " ".join(words[:i])
            if c.stringWidth(candidate, "Helvetica-Bold", NAME_SZ) <= inner_w:
                line1 = candidate
                line2 = _trunc(c, " ".join(words[i:]), "Helvetica-Bold", NAME_SZ, inner_w)
                break
        lines = [line1, line2] if line2 else [_trunc(c, nombre, "Helvetica-Bold", NAME_SZ, inner_w)]

    c.setFillColor(DARK)
    for i, line in enumerate(lines):
        c.drawCentredString(cx_mid, name_y1 - i * NAME_LEAD, line)

    # ── Huecos de escritura anclados en la base del contenido ─────────────────
    MED_W = 22
    GAP_F = 3
    TEL_W = inner_w - MED_W - GAP_F
    tel_x = x + PAD
    med_x = x + PAD + TEL_W + GAP_F

    field_y = content_bot + 3
    lbl_y   = field_y + FIELD_H + 1.5

    c.setFont("Helvetica", 4.5)
    c.setFillColor(MUTED)
    c.drawString(tel_x, lbl_y, "TEL.")
    c.drawString(med_x, lbl_y, "MED")

    c.setFillColor(white)
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.5)
    c.roundRect(tel_x, field_y, TEL_W, FIELD_H, FIELD_R, fill=1, stroke=1)
    c.roundRect(med_x, field_y, MED_W, FIELD_H, FIELD_R, fill=1, stroke=1)


def generar_pdf_equipos_agenda(partidos: list, titulo: str) -> bytes:
    """Genera el PDF de equipos participantes (solo los que tienen escudo propio)."""

    seen:   set  = set()
    equipos: list[dict] = []
    campos_por_equipo: dict[str, list] = defaultdict(list)

    for p in partidos:
        campo = (p.get("campo") or "").strip()
        for nombre_key, escudo_key in [("nombre_local",     "escudo_local"),
                                        ("nombre_visitante", "escudo_visitante")]:
            nombre = (p.get(nombre_key) or "").strip()
            escudo = (p.get(escudo_key) or "").strip()
            if not nombre or not escudo:          # sin escudo → ignorar
                continue
            if campo and campo not in campos_por_equipo[nombre]:
                campos_por_equipo[nombre].append(campo)
            if nombre not in seen:
                seen.add(nombre)
                equipos.append({
                    "nombre": nombre,
                    "escudo": escudo,
                    "torneo": p.get("nombre_torneo") or "",
                    "colors": torneo_pdf_color(p.get("torneo_id")),
                })

    for eq in equipos:
        eq["campos"] = campos_por_equipo.get(eq["nombre"], [])

    # Mapa global campo → color (orden de primera aparición)
    all_campos: list[str] = []
    seen_c: set = set()
    for eq in equipos:
        for campo in eq["campos"]:
            if campo not in seen_c:
                seen_c.add(campo)
                all_campos.append(campo)
    campo_color_map = {
        campo: _CAMPO_COLORS[i % len(_CAMPO_COLORS)]
        for i, campo in enumerate(all_campos)
    }

    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(titulo)
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}
    rffm_logo = fetch_img(RFFM_LOGO_URL, img_cache)

    _draw_page_header(c, titulo)
    grid_top = PAGE_H - MARGIN - HDR_H - 8
    col_i, row_y = 0, grid_top

    for eq in equipos:
        cx = MARGIN + col_i * (CARD_W + GAP)
        cy = row_y - CARD_H

        if cy < MARGIN:
            c.showPage()
            _draw_page_header(c, titulo)
            row_y = PAGE_H - MARGIN - HDR_H - 8
            col_i = 0
            cx    = MARGIN
            cy    = row_y - CARD_H

        _draw_card(c, cx, cy, eq, img_cache, rffm_logo, campo_color_map)

        col_i += 1
        if col_i >= COLS:
            col_i  = 0
            row_y -= CARD_H + GAP

    c.save()
    return buf.getvalue()
