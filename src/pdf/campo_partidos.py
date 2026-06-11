"""
PDF A3 vertical: terreno de fútbol con porterías arriba/abajo.
Cada mitad (superior/inferior) contiene un grid 2×2 → 8 celdas de campo en total.
"""
import io
import math
from datetime import datetime

from reportlab.lib.pagesizes import A3, landscape  # noqa: F401 – landscape no se usa aquí
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img, draw_shield_centered, RFFM_LOGO_URL

# ── Página A3 vertical ─────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A3          # 841.89 × 1190.55 pt

# ── Campo ──────────────────────────────────────────────────────────────────────
MARGIN  = 16
FX, FY  = MARGIN, MARGIN
FW      = PAGE_W - 2 * MARGIN   # ≈ 810 pt  (68 m horizontal)
FH      = PAGE_H - 2 * MARGIN   # ≈ 1158 pt (105 m vertical)
SX      = FW / 68.0              # px/m horizontal
SY      = FH / 105.0             # px/m vertical
CX      = FX + FW / 2            # centro vertical del campo
CY      = FY + FH / 2            # línea de centro (horizontal)
FL      = 1.2

GL = HexColor("#3B8A29")
GD = HexColor("#327322")
W  = white

# ── Tarjetas ───────────────────────────────────────────────────────────────────
INNER_PAD  = 12    # margen campo → celda
CELL_GAP   = 6     # hueco entre celdas adyacentes
TITLE_H    = 16    # tira de nombre de campo por celda
TITLE_GAP  = 4
CARD_H      = 58   # altura tarjeta (nombres hasta 2 líneas)
CARD_COLS   = 1    # una tarjeta por fila → ocupa todo el ancho de la celda
CARD_GAP    = 5
CARD_CORNER = 3
HDR_H       = 12   # tira de hora
SHIELD_S    = 20   # tamaño del escudo
VS_ZONE     = 26   # ancho reservado para "vs" / marcador en el centro

DARK      = HexColor("#111111")
MUTED     = HexColor("#666666")
HDR_CLR   = HexColor("#1B4D1B")
SCORE_CLR = HexColor("#CC0000")


def _trunc(c, text: str, font: str, size: float, max_w: float) -> str:
    while text and c.stringWidth(text, font, size) > max_w:
        text = text[:-1]
    return text


def _wrap_name(c, text: str, font: str, size: float, max_w: float) -> list[str]:
    """Devuelve 1 o 2 líneas ajustadas a max_w."""
    if not text:
        return ["—"]
    if c.stringWidth(text, font, size) <= max_w:
        return [text]
    words = text.split()
    for split in range(len(words) - 1, 0, -1):
        line1 = " ".join(words[:split])
        if c.stringWidth(line1, font, size) <= max_w:
            line2 = _trunc(c, " ".join(words[split:]), font, size, max_w)
            return [line1, line2]
    return [_trunc(c, text, font, size, max_w)]


# ── Dibujo del terreno (vertical: porterías arriba y abajo) ───────────────────

def _draw_pitch(c) -> None:
    # Franjas de césped (horizontales para campo vertical)
    n, sh = 14, FH / 14
    for i in range(n):
        c.setFillColor(GL if i % 2 == 0 else GD)
        c.rect(FX, FY + i * sh, FW, sh + 0.5, fill=1, stroke=0)

    c.setStrokeColor(W)
    c.setFillColor(W)
    c.setLineWidth(FL)

    # Contorno exterior
    c.rect(FX, FY, FW, FH, fill=0, stroke=1)

    # Línea de centro (horizontal)
    c.line(FX, CY, FX + FW, CY)

    # Círculo central
    rx, ry = 9.15 * SX, 9.15 * SY
    c.ellipse(CX - rx, CY - ry, CX + rx, CY + ry, fill=0, stroke=1)
    c.circle(CX, CY, 2.5, fill=1, stroke=0)

    # Áreas de penalti (40.32 m ancho · 16.5 m profundidad)
    pa_hw, pa_d = 20.16 * SX, 16.5 * SY
    # Inferior
    c.rect(CX - pa_hw, FY, 2 * pa_hw, pa_d, fill=0, stroke=1)
    # Superior
    c.rect(CX - pa_hw, FY + FH - pa_d, 2 * pa_hw, pa_d, fill=0, stroke=1)

    # Áreas de portería (18.32 m ancho · 5.5 m profundidad)
    ga_hw, ga_d = 9.16 * SX, 5.5 * SY
    c.rect(CX - ga_hw, FY, 2 * ga_hw, ga_d, fill=0, stroke=1)
    c.rect(CX - ga_hw, FY + FH - ga_d, 2 * ga_hw, ga_d, fill=0, stroke=1)

    # Porterías (7.32 m ancho · ~2.44 m profundidad exterior)
    g_hw, g_d = 3.66 * SX, 3.5 * SY
    c.rect(CX - g_hw, FY - g_d, 2 * g_hw, g_d, fill=0, stroke=1)
    c.rect(CX - g_hw, FY + FH, 2 * g_hw, g_d, fill=0, stroke=1)

    # Puntos de penalti (11 m desde la línea de fondo)
    for ps_y in [FY + 11 * SY, FY + FH - 11 * SY]:
        c.circle(CX, ps_y, 2, fill=1, stroke=0)

    # Arcos del área (D) — solo la parte fuera del área
    sin_t = 5.5 / 9.15
    if sin_t <= 1:
        theta  = math.degrees(math.asin(sin_t))   # ≈ 37°
        rx_d, ry_d = 9.15 * SX, 9.15 * SY
        # D inferior: arco por encima del área (parte superior del círculo)
        ps_bot = FY + 11 * SY
        c.arc(CX - rx_d, ps_bot - ry_d, CX + rx_d, ps_bot + ry_d,
              startAng=theta, extent=180 - 2 * theta)
        # D superior: arco por debajo del área (parte inferior del círculo)
        ps_top = FY + FH - 11 * SY
        c.arc(CX - rx_d, ps_top - ry_d, CX + rx_d, ps_top + ry_d,
              startAng=180 + theta, extent=180 - 2 * theta)

    # Arcos de córner (r = 1 m)
    cr_x, cr_y = SX, SY
    for cx_c, cy_c, sa, ext in [
        (FX,       FY,       0,   90),
        (FX + FW,  FY,       90,  90),
        (FX + FW,  FY + FH,  180, 90),
        (FX,       FY + FH,  270, 90),
    ]:
        c.arc(cx_c - cr_x, cy_c - cr_y, cx_c + cr_x, cy_c + cr_y,
              startAng=sa, extent=ext)


# ── Geometría de las 8 celdas ─────────────────────────────────────────────────

def _cell_rect(cell_idx: int) -> tuple[float, float, float, float]:
    """
    Devuelve (x, y_bottom, cell_w, cell_h) para la celda cell_idx (0-7).

    Numeración visual (top → bottom, left → right):
        0 1   ← mitad superior, fila superior
        2 3   ← mitad superior, fila inferior
        ─── centro ───
        4 5   ← mitad inferior, fila superior
        6 7   ← mitad inferior, fila inferior
    """
    col = cell_idx % 2
    row = cell_idx // 2   # 0 = visual top

    cell_w = (FW - 2 * INNER_PAD - CELL_GAP) / 2
    half_h = FH / 2 - 2 * INNER_PAD
    cell_h = (half_h - CELL_GAP) / 2

    x = FX + INNER_PAD + col * (cell_w + CELL_GAP)

    # row 0,1 → top half (rows sorted top-to-bottom, y decreases visually)
    if row <= 1:
        # top half: y from CY + INNER_PAD up
        # row 0 = upper row of top half → highest y
        row_in_half = row          # 0=upper, 1=lower within top half
        y_bottom = CY + INNER_PAD + (1 - row_in_half) * (cell_h + CELL_GAP)
    else:
        # bottom half: y from FY + INNER_PAD
        row_in_half = row - 2      # 0=upper, 1=lower within bottom half
        y_bottom = FY + INNER_PAD + (1 - row_in_half) * (cell_h + CELL_GAP)

    return x, y_bottom, cell_w, cell_h


# ── Tarjeta de partido ─────────────────────────────────────────────────────────

MAX_CARDS  = 6      # máximo de partidos por celda
CARD_H_REF = 58.0   # altura de referencia (para escalar proporciones)

def _draw_card(c, x: float, y: float, card_w: float, card_h: float,
               partido: dict, img_cache: dict, rffm_logo) -> None:
    """Dibuja una tarjeta escalando todos los tamaños según card_h."""
    r        = card_h / CARD_H_REF          # factor de escala
    hdr_h    = max(8.0,  HDR_H   * r)
    shield_s = max(7.0,  SHIELD_S * r)
    vs_zone  = max(14.0, VS_ZONE  * r)
    name_sz  = max(5.0,  9.0     * r)
    hdr_sz   = max(4.5,  6.5     * r)
    line_gap = max(7.0,  10.5    * r)

    # Fondo
    c.saveState()
    c.setFillAlpha(0.90)
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#AAAAAA"))
    c.setLineWidth(0.4)
    c.roundRect(x, y, card_w, card_h, CARD_CORNER, fill=1, stroke=1)
    c.restoreState()

    # Tira de hora
    hdr_y = y + card_h - hdr_h - 1
    c.setFillColor(HDR_CLR)
    c.roundRect(x + 2, hdr_y, card_w - 4, hdr_h, 2, fill=1, stroke=0)

    hora  = str(partido.get("hora") or "")[:5] or "—"
    fecha = str(partido.get("fecha") or "")[:10]
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", hdr_sz)
    c.drawString(x + 5, hdr_y + hdr_h * 0.28, hora)
    if fecha:
        try:
            d = datetime.strptime(fecha, "%Y-%m-%d")
            fecha_str = f"{d.day}/{d.month:02d}"
        except Exception:
            fecha_str = fecha[5:]
        c.setFont("Helvetica", max(4.0, hdr_sz - 0.5))
        c.drawRightString(x + card_w - 5, hdr_y + hdr_h * 0.28, fecha_str)

    # Centro del área de contenido
    content_h = card_h - hdr_h - 2
    cy        = y + content_h / 2
    mid_x     = x + card_w / 2
    PAD       = max(2.0, 3.0 * r)
    name_w    = (card_w - vs_zone - 2 * shield_s - 4 * PAD) / 2

    # Escudo local
    shield_l_cx = x + PAD + shield_s / 2
    img_l = fetch_img(partido.get("escudo_local"), img_cache)
    draw_shield_centered(c, img_l, rffm_logo, shield_l_cx, cy, shield_s)

    # Nombre local
    txt_x_l = shield_l_cx + shield_s / 2 + PAD
    lines_l  = _wrap_name(c, partido.get("nombre_local") or "—", "Helvetica-Bold", name_sz, name_w)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", name_sz)
    if len(lines_l) == 1:
        c.drawString(txt_x_l, cy - name_sz * 0.35, lines_l[0])
    else:
        c.drawString(txt_x_l, cy + line_gap / 2 - name_sz * 0.35, lines_l[0])
        c.drawString(txt_x_l, cy - line_gap / 2 - name_sz * 0.35, lines_l[1])

    # vs / marcador
    gl = partido.get("goles_local")
    gv = partido.get("goles_visitante")
    vs_sz = max(5.0, name_sz + 0.5)
    if gl is not None and gv is not None:
        c.setFillColor(SCORE_CLR)
        c.setFont("Helvetica-Bold", vs_sz)
        c.drawCentredString(mid_x, cy - vs_sz * 0.35, f"{gl}–{gv}")
    else:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", name_sz)
        c.drawCentredString(mid_x, cy - name_sz * 0.35, "vs")

    # Escudo visitante
    shield_v_cx = x + card_w - PAD - shield_s / 2
    img_v = fetch_img(partido.get("escudo_visitante"), img_cache)
    draw_shield_centered(c, img_v, rffm_logo, shield_v_cx, cy, shield_s)

    # Nombre visitante
    txt_x_v = shield_v_cx - shield_s / 2 - PAD
    lines_v  = _wrap_name(c, partido.get("nombre_visitante") or "—", "Helvetica", name_sz, name_w)
    c.setFillColor(DARK)
    c.setFont("Helvetica", name_sz)
    if len(lines_v) == 1:
        c.drawRightString(txt_x_v, cy - name_sz * 0.35, lines_v[0])
    else:
        c.drawRightString(txt_x_v, cy + line_gap / 2 - name_sz * 0.35, lines_v[0])
        c.drawRightString(txt_x_v, cy - line_gap / 2 - name_sz * 0.35, lines_v[1])


# ── Celda con nombre de campo y tarjetas ──────────────────────────────────────

def _draw_cell(c, cell_idx: int, nombre: str, partidos: list,
               img_cache: dict, rffm_logo) -> None:
    x, y_bot, cell_w, cell_h = _cell_rect(cell_idx)
    area_mid = x + cell_w / 2

    # Título semitransparente
    title_y = y_bot + cell_h - TITLE_H
    c.saveState()
    c.setFillAlpha(0.78)
    c.setFillColor(HexColor("#061006"))
    c.roundRect(x, title_y, cell_w, TITLE_H, 3, fill=1, stroke=0)
    c.restoreState()
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    label = _trunc(c, nombre.upper(), "Helvetica-Bold", 8, cell_w - 8)
    c.drawCentredString(area_mid, title_y + 4.5, label)

    if not partidos:
        c.setFillColor(HexColor("#BBBBBB"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(area_mid, y_bot + cell_h / 2, "Sin partidos")
        return

    partidos  = partidos[:MAX_CARDS]
    n         = len(partidos)
    card_w    = (cell_w - CARD_GAP) / CARD_COLS
    y_top     = title_y - TITLE_GAP   # tope superior de las tarjetas
    available = y_top - y_bot - 4     # espacio vertical para todas las tarjetas
    card_h    = min(CARD_H, (available - (n - 1) * CARD_GAP) / n) if n > 0 else CARD_H

    for i, p in enumerate(partidos):
        col    = i % CARD_COLS
        row    = i // CARD_COLS
        card_x = x + col * (card_w + CARD_GAP)
        card_y = y_top - (row + 1) * card_h - row * CARD_GAP

        _draw_card(c, card_x, card_y, card_w, card_h, p, img_cache, rffm_logo)


# ── Función pública ────────────────────────────────────────────────────────────

def generar_pdf_campo_partidos(cells: list[dict]) -> bytes:
    """
    Genera PDF A3 vertical con terreno de fútbol y 8 celdas de partidos.

    cells: lista de 8 dicts [{nombre: str, partidos: list}, ...]
    Orden visual: 0=sup-izq, 1=sup-der, 2=mediosup-izq, 3=mediosup-der,
                  4=medioinf-izq, 5=medioinf-der, 6=inf-izq, 7=inf-der
    """
    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A3)
    c.setTitle("Terreno de juego – Partidos")
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}
    rffm_logo = fetch_img(RFFM_LOGO_URL, img_cache)

    _draw_pitch(c)

    for idx, cell in enumerate(cells[:8]):
        _draw_cell(c, idx, cell.get("nombre", ""), cell.get("partidos", []),
                   img_cache, rffm_logo)

    c.save()
    return buf.getvalue()
