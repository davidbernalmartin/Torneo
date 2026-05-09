"""Genera un PDF con tarjetas de equipo para sorteo físico, 12 por página (3 × 4)."""
import io
import unicodedata
import urllib.request

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ── Dimensiones de página y cuadrícula ───────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595.28 × 841.89 pt
MARGIN   = 12 * mm
COLS, ROWS = 3, 4
GUTTER_X = 5 * mm
GUTTER_Y = 5 * mm

CARD_W = (PAGE_W - 2 * MARGIN - (COLS - 1) * GUTTER_X) / COLS
CARD_H = (PAGE_H - 2 * MARGIN - (ROWS - 1) * GUTTER_Y) / ROWS

PAD         = 4 * mm
PAD_BOT     = 4 * mm
NAME_ZONE_H = 13 * mm   # zona fija para el nombre (aguanta hasta 2 líneas)
AZUL  = colors.HexColor("#1F4E78")
GRIS  = colors.HexColor("#888888")
NEGRO = colors.HexColor("#1A1A2E")
FONDO = colors.white
ROJO  = colors.HexColor("#CC0000")

RFFM_URL  = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"
RFFM_SIZE = 10 * mm


def _fetch_image(url: str):
    """Descarga una imagen desde URL y devuelve ImageReader, o None si falla."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GestorTorneo/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read()
        return ImageReader(io.BytesIO(data))
    except Exception:
        return None


def _es_campeon(nombre: str) -> bool:
    def _norm(s):
        s = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "campeon" in _norm(nombre)


def _split_words(c, words: list, n_lines: int, font: str, fs: float):
    """Divide words en n_lines partes minimizando el ancho máximo de línea."""
    if n_lines == 1:
        return [" ".join(words)]
    if len(words) <= n_lines:
        # Una palabra por línea si hay pocas palabras
        return [w for w in words] + [""] * (n_lines - len(words))

    best, best_max = None, float("inf")
    # Para 2 líneas: un punto de corte; para 3: dos puntos
    if n_lines == 2:
        for i in range(1, len(words)):
            l1, l2 = " ".join(words[:i]), " ".join(words[i:])
            wmax = max(c.stringWidth(l1, font, fs), c.stringWidth(l2, font, fs))
            if wmax < best_max:
                best_max, best = wmax, [l1, l2]
    else:  # 3 líneas
        for i in range(1, len(words) - 1):
            for j in range(i + 1, len(words)):
                l1 = " ".join(words[:i])
                l2 = " ".join(words[i:j])
                l3 = " ".join(words[j:])
                wmax = max(c.stringWidth(l, font, fs) for l in [l1, l2, l3])
                if wmax < best_max:
                    best_max, best = wmax, [l1, l2, l3]
    return best or [" ".join(words)]


def _fit_nombre(c, nombre: str, max_w: float, fs_start: float, fs_min: float = 8.0):
    """Devuelve (líneas, font_size) que caben en max_w con hasta 3 líneas."""
    font  = "Helvetica-Bold"
    words = nombre.split()
    for n_lines in range(1, 3):
        fs = fs_start
        while fs >= fs_min:
            lines = _split_words(c, words, n_lines, font, fs)
            if all(c.stringWidth(l, font, fs) <= max_w for l in lines if l):
                return [l for l in lines if l], fs
            fs -= 0.4
    # Último recurso: 2 líneas al mínimo
    lines = _split_words(c, words, 2, font, fs_min)
    return [l for l in lines if l], fs_min


def _draw_card(c: canvas.Canvas, x, y, equipo: dict, img_equipo, img_rffm, nombre_torneo: str):
    w, h = CARD_W, CARD_H
    nombre      = (equipo.get("nombre")      or "—").upper()
    competicion = (equipo.get("competicion") or "").strip()
    grupo       = (equipo.get("grupo")       or "").strip()
    campeon     = _es_campeon(nombre)

    # ── Fondo ─────────────────────────────────────────────────────────────────
    c.setFillColor(FONDO)
    c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=0)

    # ── Borde de corte discontinuo ────────────────────────────────────────────
    c.setDash(3, 3)
    c.setStrokeColor(colors.HexColor("#BBBBBB"))
    c.setLineWidth(0.4)
    c.roundRect(x, y, w, h, 3 * mm, fill=0, stroke=1)
    c.setDash()

    # ── CABECERA: logo RFFM izquierda + competición/grupo derecha ─────────────
    if campeon:
        header_bottom = y + h - PAD
    else:
        rffm_y = y + h - PAD - RFFM_SIZE

        if img_rffm:
            try:
                c.drawImage(img_rffm, x + PAD, rffm_y, RFFM_SIZE, RFFM_SIZE,
                            preserveAspectRatio=True, anchor='c', mask="auto")
            except Exception:
                pass

        txt_x     = x + PAD + RFFM_SIZE + 2 * mm
        txt_max_w = w - PAD - RFFM_SIZE - 2 * mm - PAD
        txt_cx    = txt_x + txt_max_w / 2

        lineas = [l for l in [competicion, grupo] if l]
        if lineas:
            fs_red = 6.5
            for linea in lineas:
                while c.stringWidth(linea, "Helvetica-Bold", fs_red) > txt_max_w and fs_red > 3.8:
                    fs_red -= 0.3

            line_h    = fs_red * 1.35
            total_h   = len(lineas) * line_h
            txt_start = rffm_y + (RFFM_SIZE + total_h) / 2 - line_h * 0.85

            c.setFont("Helvetica-Bold", fs_red)
            c.setFillColor(ROJO)
            for i, linea in enumerate(lineas):
                c.drawCentredString(txt_cx, txt_start - i * line_h, linea)

        header_bottom = rffm_y - 1 * mm

    # ── SEPARADOR ─────────────────────────────────────────────────────────────
    torneo_h = 3 * mm if nombre_torneo else 0
    sep_y    = y + PAD_BOT + torneo_h + NAME_ZONE_H

    # ── ESCUDO DEL EQUIPO ─────────────────────────────────────────────────────
    shield_gap = 4 * mm
    shield_h   = header_bottom - sep_y - 2 * shield_gap
    img_max    = max(min(shield_h, w - 2 * PAD), 0)
    img_x      = x + (w - img_max) / 2
    img_y      = sep_y + shield_gap + (shield_h - img_max) / 2

    if img_equipo and img_max > 0:
        try:
            c.drawImage(img_equipo, img_x, img_y, img_max, img_max,
                        preserveAspectRatio=True, anchor='c', mask="auto")
        except Exception:
            img_equipo = None

    if not img_equipo and img_max > 0:
        r = img_max * 0.38
        c.setFillColor(colors.HexColor("#D0DCF0"))
        c.setStrokeColor(colors.HexColor("#A0B8D8"))
        c.setLineWidth(0.5)
        c.circle(x + w / 2, img_y + img_max / 2, r, fill=1, stroke=1)

    # ── Línea separadora ──────────────────────────────────────────────────────
    c.setStrokeColor(AZUL)
    c.setLineWidth(0.8)
    c.line(x + PAD, sep_y, x + w - PAD, sep_y)

    # ── Nombre del equipo (multilínea) ───────────────────────────────────────
    max_w      = w - 2 * PAD
    fs_inicio  = 12.0 if campeon else 10.5
    lines, fs  = _fit_nombre(c, nombre, max_w, fs_inicio)

    line_h     = fs * 1.35
    total_name = len(lines) * line_h
    name_zone_bot = y + PAD_BOT + torneo_h
    name_mid      = (name_zone_bot + sep_y) / 2
    # baseline de la primera línea centrada en la zona
    y_line0 = name_mid + total_name / 2 - line_h * 0.75

    c.setFont("Helvetica-Bold", fs)
    c.setFillColor(NEGRO)
    for i, line in enumerate(lines):
        c.drawCentredString(x + w / 2, y_line0 - i * line_h, line)

    # ── Nombre del torneo (pie) ───────────────────────────────────────────────
    if nombre_torneo:
        c.setFont("Helvetica", 5)
        c.setFillColor(GRIS)
        c.drawCentredString(x + w / 2, y + 1 * mm, nombre_torneo)


def generar_pdf_tarjetas(equipos: list, nombre_torneo: str = "") -> bytes:
    """
    Genera el PDF de tarjetas de sorteo físico.

    Args:
        equipos: lista de dicts con claves 'nombre', 'escudo_url', 'competicion', 'grupo'
        nombre_torneo: nombre del torneo (se imprime al pie de cada tarjeta)

    Returns:
        Bytes del PDF listo para descargar.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Tarjetas sorteo — {nombre_torneo}")

    img_rffm = _fetch_image(RFFM_URL)

    imgs: dict = {}
    for eq in equipos:
        url = eq.get("escudo_url") or ""
        if url and url not in imgs:
            imgs[url] = _fetch_image(url)

    for i, equipo in enumerate(equipos):
        pos = i % (COLS * ROWS)
        if pos == 0 and i > 0:
            c.showPage()

        col = pos % COLS
        row = pos // COLS
        x   = MARGIN + col * (CARD_W + GUTTER_X)
        y   = PAGE_H - MARGIN - (row + 1) * CARD_H - row * GUTTER_Y

        _draw_card(c, x, y, equipo,
                   imgs.get(equipo.get("escudo_url") or ""),
                   img_rffm,
                   nombre_torneo)

    c.save()
    buf.seek(0)
    return buf.read()
