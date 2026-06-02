"""
PDF de agenda de partidos organizado por campo y día.
"""
import io
from datetime import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img as _fetch_img, draw_shield_centered as _draw_shield_centered, RFFM_LOGO_URL as _RFFM_LOGO, LIGHT_BG, BORDER, torneo_pdf_color

# ── Paleta ────────────────────────────────────────────────────────────────────
RED      = HexColor("#CC0000")
DARK     = HexColor("#1A1A1A")
MUTED    = HexColor("#888888")
WHITE    = white
FIELD_BG = HexColor("#1A3A5F")
DAY_BG   = HexColor("#CC0000")

# ── Dimensiones ───────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN   = 30
CARD_W   = PAGE_W - 2 * MARGIN
HDR_H    = 38
CARD_H   = 74
SHIELD_S = 36
PAD_X    = 14
VS_W     = 132      # ancho reservado para hora central + cajitas de resultado
INFO_H   = 16
BAR_TOP  = 16
CORNER   = 8
STRIP_W  = 5
CARD_GAP = 6
DAY_H    = 28
FIELD_H  = 22
GRP_GAP  = 10


# ── Utilidades ────────────────────────────────────────────────────────────────

def _draw_shield(c, img, fallback_img, cx, cy, size):
    _draw_shield_centered(c, img, fallback_img, cx, cy, size)


def _fit_name(c, text, font, max_size, max_w):
    sz = max_size
    while sz >= 6 and c.stringWidth(text, font, sz) > max_w:
        sz -= 0.5
    if c.stringWidth(text, font, sz) > max_w:
        t = text
        while t and c.stringWidth(t + "…", font, sz) > max_w:
            t = t[:-1]
        text = t + "…"
    return text, sz


# ── Tarjeta de partido ────────────────────────────────────────────────────────

def _draw_card(c, x, y, partido, cache, rffm_logo):
    w, h = CARD_W, CARD_H

    has_local   = bool(partido.get("equipo_local_id"))
    has_visit   = bool(partido.get("equipo_visitante_id"))
    grupo_nombre = (partido.get("nombre_grupo") or "").upper()

    card_bg, card_border = torneo_pdf_color(partido.get("torneo_id"))

    # Fondo de color del torneo + borde redondeado
    c.setFillColor(card_bg)
    c.setStrokeColor(card_border)
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, CORNER, fill=1, stroke=1)

    # ── Barra inferior con el nombre del torneo ───────────────────────────────
    c.setFillColor(card_border)
    c.rect(x + CORNER, y, w - 2 * CORNER, INFO_H, fill=1, stroke=0)
    c.roundRect(x, y, w, INFO_H, CORNER, fill=1, stroke=0)
    c.setStrokeColor(card_border)
    c.setLineWidth(0.4)
    c.line(x + CORNER, y + INFO_H, x + w - CORNER, y + INFO_H)

    torneo = partido.get("nombre_torneo", "")
    c.setFillColor(WHITE)
    if torneo:
        c.setFont("Helvetica-Bold", 7)
        max_t = w - STRIP_W - PAD_X * 2
        t_label = torneo
        while t_label and c.stringWidth(t_label, "Helvetica-Bold", 7) > max_t:
            t_label = t_label[:-1]
        c.drawCentredString(x + w / 2, y + 4.5, t_label)
    else:
        c.setFont("Helvetica-Oblique", 6.5)
        c.setFillColor(MUTED)
        c.drawCentredString(x + w / 2, y + 4.5, "Torneo sin nombre")

    # ── Zona de contenido ─────────────────────────────────────────────────────
    content_bot = y + INFO_H
    content_top = y + h
    center_y    = (content_bot + content_top) / 2
    vs_cx       = x + w / 2

    left_x1  = x + PAD_X
    left_x2  = vs_cx - VS_W / 2 - 6
    right_x1 = vs_cx + VS_W / 2 + 6
    right_x2 = x + w - PAD_X

    # ── LOCAL ─────────────────────────────────────────────────────────────────
    if has_local:
        img_l = _fetch_img(partido.get("escudo_local"), cache)
        local_name = partido.get("nombre_local", "—")
        shield_cx_l = left_x1 + SHIELD_S / 2
        _draw_shield(c, img_l, rffm_logo, shield_cx_l, center_y, SHIELD_S)
        name_x_l = left_x1 + SHIELD_S + 8
        name_l, sz_l = _fit_name(c, local_name, "Helvetica-Bold", 10.5, left_x2 - name_x_l)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", sz_l)
        c.drawString(name_x_l, center_y - sz_l / 2, name_l)
        c.setFont("Helvetica", 5.5)
        c.setFillColor(MUTED)
        c.drawString(name_x_l, center_y + sz_l / 2 + 2, "LOCAL")
    else:
        # Línea en blanco para escribir el nombre a mano
        line_y = center_y - 2
        c.setStrokeColor(HexColor("#BBBBBB"))
        c.setLineWidth(0.8)
        c.line(left_x1 + 4, line_y, left_x2 - 4, line_y)
        c.setFont("Helvetica", 5.5)
        c.setFillColor(MUTED)
        c.drawString(left_x1 + 4, line_y + 4, "LOCAL")

    # ── VISITANTE ─────────────────────────────────────────────────────────────
    if has_visit:
        img_v = _fetch_img(partido.get("escudo_visitante"), cache)
        visit_name = partido.get("nombre_visitante", "—")
        shield_cx_v = right_x2 - SHIELD_S / 2
        _draw_shield(c, img_v, rffm_logo, shield_cx_v, center_y, SHIELD_S)
        name_x2_v = right_x2 - SHIELD_S - 8
        name_v, sz_v = _fit_name(c, visit_name, "Helvetica-Bold", 10.5, name_x2_v - right_x1)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", sz_v)
        c.drawRightString(name_x2_v, center_y - sz_v / 2, name_v)
        c.setFont("Helvetica", 5.5)
        c.setFillColor(MUTED)
        c.drawRightString(name_x2_v, center_y + sz_v / 2 + 2, "VISITANTE")
    else:
        line_y = center_y - 2
        c.setStrokeColor(HexColor("#BBBBBB"))
        c.setLineWidth(0.8)
        c.line(right_x1 + 4, line_y, right_x2 - 4, line_y)
        c.setFont("Helvetica", 5.5)
        c.setFillColor(MUTED)
        c.drawRightString(right_x2 - 4, line_y + 4, "VISITANTE")

    # ── Cajitas de resultado a cada lado de la hora ───────────────────────────
    BOX_W, BOX_H = 36, 28
    box_y = center_y - BOX_H / 2

    # Nombre del grupo encima de las cajitas
    if grupo_nombre:
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(MUTED)
        grp_label = grupo_nombre
        max_grp = VS_W - 8
        while grp_label and c.stringWidth(grp_label, "Helvetica-Bold", 6) > max_grp:
            grp_label = grp_label[:-1]
        c.drawCentredString(vs_cx, box_y + BOX_H + 4, grp_label)

    c.setFillColor(HexColor("#FAFAFA"))
    c.setStrokeColor(HexColor("#BBBBBB"))
    c.setLineWidth(0.8)
    # Cajita local (izquierda de la hora)
    c.roundRect(vs_cx - VS_W / 2 + 4, box_y, BOX_W, BOX_H, 3, fill=1, stroke=1)
    # Cajita visitante (derecha de la hora)
    c.roundRect(vs_cx + VS_W / 2 - 4 - BOX_W, box_y, BOX_W, BOX_H, 3, fill=1, stroke=1)

    # HORA central
    hora = partido.get("hora")
    hora_str = str(hora)[:5] if hora else "—:——"
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(vs_cx, center_y - 5, hora_str)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(MUTED)
    c.drawCentredString(vs_cx, center_y + 8, "HORA")


# ── Cabeceras ─────────────────────────────────────────────────────────────────

def _draw_day_header(c, x, y, fecha_str):
    w = CARD_W
    c.setFillColor(DAY_BG)
    c.roundRect(x, y, w, DAY_H, 5, fill=1, stroke=0)
    # tira izquierda más oscura
    c.setFillColor(HexColor("#990000"))
    c.roundRect(x, y, STRIP_W + 4, DAY_H, 5, fill=1, stroke=0)
    c.rect(x + 3, y, STRIP_W + 1, DAY_H, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + STRIP_W + 10, y + 9, fecha_str.upper())


def _draw_field_header(c, x, y, campo, n_partidos):
    w = CARD_W
    c.setFillColor(FIELD_BG)
    c.roundRect(x, y, w, FIELD_H, 4, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    label = (campo or "CAMPO SIN NOMBRE").upper()
    max_l = w - 120
    while label and c.stringWidth(label, "Helvetica-Bold", 9) > max_l:
        label = label[:-1]
    c.drawString(x + 10, y + 6.5, label)
    n_str = f"{n_partidos} partido{'s' if n_partidos != 1 else ''}"
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#AACCEE"))
    c.drawRightString(x + w - 10, y + 6.5, n_str)


# ── Función principal ─────────────────────────────────────────────────────────

def generar_pdf_agenda(partidos: list, titulo: str) -> bytes:
    """Genera el PDF de agenda: una página por campo+día, cabecera con campo y fecha."""
    agenda: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for p in partidos:
        fecha = str(p.get("fecha") or "")[:10]
        campo = p.get("campo") or "Sin campo asignado"
        agenda[campo][fecha].append(p)

    campos_ordenados = sorted(agenda.keys())

    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(titulo)
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}
    rffm_logo = _fetch_img(_RFFM_LOGO, img_cache)

    dia_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    mes_nombres = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                   "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    def _fecha_label(fecha_iso):
        try:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
            return f"{dia_nombres[dt.weekday()]}, {dt.day} de {mes_nombres[dt.month-1]} de {dt.year}"
        except Exception:
            return fecha_iso

    def draw_page_header(campo_nombre: str, fecha_label: str):
        hx, hy, hw = MARGIN, PAGE_H - MARGIN - HDR_H, CARD_W
        c.setFillColor(RED)
        c.roundRect(hx, hy, hw, HDR_H, 6, fill=1, stroke=0)
        # Tira izquierda más oscura
        c.setFillColor(HexColor("#990000"))
        c.roundRect(hx, hy, STRIP_W + 4, HDR_H, 6, fill=1, stroke=0)
        c.rect(hx + 3, hy, STRIP_W + 1, HDR_H, fill=1, stroke=0)
        c.setFillColor(WHITE)
        # Campo (línea superior, grande)
        campo_t = campo_nombre.upper()
        max_w = hw - 28
        while campo_t and c.stringWidth(campo_t, "Helvetica-Bold", 13) > max_w:
            campo_t = campo_t[:-1]
        c.setFont("Helvetica-Bold", 13)
        c.drawString(hx + STRIP_W + 12, hy + 20, campo_t)
        # Fecha (línea inferior, más pequeña)
        fecha_t = fecha_label.upper()
        while fecha_t and c.stringWidth(fecha_t, "Helvetica", 8.5) > max_w:
            fecha_t = fecha_t[:-1]
        c.setFont("Helvetica", 8.5)
        c.setFillColor(HexColor("#FFCCCC"))
        c.drawString(hx + STRIP_W + 12, hy + 7, fecha_t)

    first_page = True

    for campo in campos_ordenados:
        dias_campo = agenda[campo]

        for fecha_iso in sorted(dias_campo.keys()):
            ps = dias_campo[fecha_iso]
            fecha_label = _fecha_label(fecha_iso)

            if not first_page:
                c.showPage()
            first_page = False

            draw_page_header(campo, fecha_label)
            y = PAGE_H - MARGIN - HDR_H - 10

            for partido in sorted(ps, key=lambda p: str(p.get("hora") or "")):
                if y - CARD_H < MARGIN:
                    c.showPage()
                    draw_page_header(campo, fecha_label)
                    y = PAGE_H - MARGIN - HDR_H - 10
                _draw_card(c, MARGIN, y - CARD_H, partido, img_cache, rffm_logo)
                y -= CARD_H + CARD_GAP

    c.save()
    return buf.getvalue()
