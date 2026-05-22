"""
Generación de PDF con tarjetas de partidos, organizadas por grupo.
Tarjetas horizontales a ancho completo: escudo · nombre  VS  nombre · escudo
"""
import io
import urllib.request
from datetime import datetime

import qrcode
from PIL import Image as PilImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader

# ── Paleta ────────────────────────────────────────────────────────────────────
RED       = HexColor("#CC0000")
RED_LIGHT = HexColor("#F5DADA")
DARK      = HexColor("#1A1A1A")
MUTED     = HexColor("#888888")
LIGHT_BG  = HexColor("#F7F7F7")
BORDER    = HexColor("#E0E0E0")
VS_COLOR  = HexColor("#CC0000")
WHITE     = white

# ── Dimensiones ───────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595 × 842 pt
MARGIN    = 30               # margen exterior
CARD_W    = PAGE_W - 2 * MARGIN   # ≈ 535 pt — ancho completo

CARD_H    = 68    # altura total de la tarjeta
SHIELD_S  = 38    # tamaño del cuadrado del escudo
PAD_X     = 14    # padding horizontal interior
VS_W      = 52    # anchura de la zona central VS
INFO_H    = 16    # altura de la barra inferior de metadatos
CORNER    = 8     # radio de esquinas redondeadas
STRIP_W   = 5     # tira de acento izquierda


# ── Utilidades de imagen ───────────────────────────────────────────────────────

def _fetch_img(url: str | None, cache: dict) -> ImageReader | None:
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


def _draw_shield(c, img, cx: float, cy: float, size: float):
    """Dibuja un escudo centrado en (cx, cy)."""
    x = cx - size / 2
    y = cy - size / 2
    if img:
        try:
            c.drawImage(img, x, y, size, size, preserveAspectRatio=True, mask="auto")
            return
        except Exception:
            pass
    # placeholder
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(x, y, size, size, 4, fill=1, stroke=1)


def _fit_name(c, text: str, font: str, max_size: float, max_w: float) -> tuple[str, float]:
    """Reduce el tamaño de fuente hasta que el texto entre en max_w. Devuelve (texto_truncado, size)."""
    sz = max_size
    while sz >= 6 and c.stringWidth(text, font, sz) > max_w:
        sz -= 0.5
    if c.stringWidth(text, font, sz) > max_w:
        # truncar con ellipsis
        t = text
        while t and c.stringWidth(t + "…", font, sz) > max_w:
            t = t[:-1]
        text = t + "…"
    return text, sz


# ── Dibujo de una tarjeta ──────────────────────────────────────────────────────

def _draw_card(c, x: float, y: float, partido: dict, grupo_nombre: str, jornada_label: str, cache: dict):
    """
    Dibuja la tarjeta horizontal con esquina inferior-izquierda en (x, y).
    """
    w, h = CARD_W, CARD_H

    # ── Fondo blanco + borde ──────────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, CORNER, fill=1, stroke=1)

    # ── Barra inferior de metadatos ───────────────────────────────────────────
    meta_parts = []
    fecha = partido.get("fecha")
    if fecha:
        try:
            dt = datetime.strptime(str(fecha)[:10], "%Y-%m-%d")
            meta_parts.append(dt.strftime("%d/%m/%Y"))
        except Exception:
            meta_parts.append(str(fecha)[:10])
    hora = partido.get("hora")
    if hora:
        meta_parts.append(str(hora)[:5])
    campo = partido.get("campo")
    if campo:
        meta_parts.append(campo)

    # barra inferior
    bar_h = INFO_H
    c.setFillColor(LIGHT_BG)
    # fondo de la barra — recortado a la parte de abajo con esquinas solo inferiores
    c.rect(x + CORNER, y, w - 2 * CORNER, bar_h, fill=1, stroke=0)
    c.roundRect(x, y, w, bar_h, CORNER, fill=1, stroke=0)
    # línea separadora
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.4)
    c.line(x + CORNER, y + bar_h, x + w - CORNER, y + bar_h)

    if meta_parts:
        meta_str = "   ·   ".join(meta_parts)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(MUTED)
        # pequeños iconos de texto antes de cada dato
        c.drawCentredString(x + w / 2, y + 4.5, meta_str)
    else:
        c.setFont("Helvetica-Oblique", 6.5)
        c.setFillColor(MUTED)
        c.drawCentredString(x + w / 2, y + 4.5, "Fecha · hora · campo pendientes")

    # ── Zona de contenido (sobre la barra) ───────────────────────────────────
    content_y   = y + bar_h         # base del área de contenido
    content_h   = h - bar_h         # ≈ 52 pt
    center_y    = content_y + content_h / 2   # centro vertical del contenido

    # ── VS central ───────────────────────────────────────────────────────────
    vs_cx = x + w / 2
    c.setFillColor(VS_COLOR)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(vs_cx, center_y - 5, "VS")

    # ── Zonas de equipo ───────────────────────────────────────────────────────
    # Local: desde x + PAD_X hasta vs_cx - VS_W/2
    # Visitante: desde vs_cx + VS_W/2 hasta x + w - PAD_X

    left_x1  = x + PAD_X
    left_x2  = vs_cx - VS_W / 2 - 6
    right_x1 = vs_cx + VS_W / 2 + 6
    right_x2 = x + w - PAD_X

    local_name = partido.get("nombre_local", "—")
    visit_name = partido.get("nombre_visitante", "—")
    img_l = _fetch_img(partido.get("escudo_local"), cache)
    img_v = _fetch_img(partido.get("escudo_visitante"), cache)

    # --- LOCAL (izquierda): escudo a la izquierda, nombre a su derecha ---
    shield_cx_l = left_x1 + SHIELD_S / 2
    _draw_shield(c, img_l, shield_cx_l, center_y, SHIELD_S)

    name_x_l  = left_x1 + SHIELD_S + 10   # texto empieza tras el escudo
    name_mw_l = left_x2 - name_x_l
    name_l, sz_l = _fit_name(c, local_name, "Helvetica-Bold", 11, name_mw_l)

    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", sz_l)
    # centrar verticalmente el bloque escudo+nombre
    c.drawString(name_x_l, center_y - sz_l / 2, name_l)

    # etiqueta LOCAL
    c.setFont("Helvetica", 5.5)
    c.setFillColor(MUTED)
    c.drawString(name_x_l, center_y + sz_l / 2 + 2, "LOCAL")

    # --- VISITANTE (derecha): nombre a la izquierda, escudo a la derecha ---
    shield_cx_v = right_x2 - SHIELD_S / 2
    _draw_shield(c, img_v, shield_cx_v, center_y, SHIELD_S)

    name_x2_v  = right_x2 - SHIELD_S - 10   # borde derecho del texto
    name_mw_v  = name_x2_v - right_x1
    name_v, sz_v = _fit_name(c, visit_name, "Helvetica-Bold", 11, name_mw_v)

    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", sz_v)
    c.drawRightString(name_x2_v, center_y - sz_v / 2, name_v)

    c.setFont("Helvetica", 5.5)
    c.setFillColor(MUTED)
    c.drawRightString(name_x2_v, center_y + sz_v / 2 + 2, "VISITANTE")

    # ── Jornada chip (esquina superior derecha) ───────────────────────────────
    if jornada_label:
        c.setFont("Helvetica", 6)
        c.setFillColor(MUTED)
        c.drawCentredString(x + w / 2, y + h - 7, jornada_label)


# ── Cabecera de grupo ──────────────────────────────────────────────────────────

GH = 22   # altura de la cabecera de grupo

def _draw_group_header(c, x: float, y: float, nombre: str, n_partidos: int):
    w = CARD_W
    c.setFillColor(DARK)
    c.roundRect(x, y, w, GH, 5, fill=1, stroke=0)

    # tira roja izquierda
    c.setFillColor(RED)
    c.roundRect(x, y, STRIP_W + 4, GH, 5, fill=1, stroke=0)
    c.rect(x + 3, y, STRIP_W + 1, GH, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + STRIP_W + 10, y + 7, nombre.upper())

    n_str = f"{n_partidos} partido{'s' if n_partidos != 1 else ''}"
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#AAAAAA"))
    c.drawRightString(x + w - 10, y + 7, n_str)


_LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"


def _generar_qr_pil(url: str) -> io.BytesIO:
    """Genera el QR con el escudo RFFM centrado, igual que en app.py."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="white").convert("RGBA")

    try:
        req = urllib.request.Request(_LOGO_RFFM_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            logo = PilImage.open(io.BytesIO(resp.read())).convert("RGBA")
        qr_w, qr_h = img.size
        logo_size = qr_w // 4
        logo = logo.resize((logo_size, logo_size), PilImage.LANCZOS)
        pad = 6
        bg = PilImage.new("RGBA", (logo_size + pad * 2, logo_size + pad * 2), (255, 255, 255, 255))
        img.paste(bg, ((qr_w - bg.width) // 2, (qr_h - bg.height) // 2))
        img.paste(logo, ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2), logo)
    except Exception:
        pass  # QR sigue siendo válido sin el logo

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Página QR ─────────────────────────────────────────────────────────────────

def _draw_qr_page(c, url: str, torneo_nombre: str):
    """Dibuja una página centrada con el QR del bracket público."""
    c.showPage()

    # cabecera roja
    hx = MARGIN
    hy = PAGE_H - MARGIN - HDR_H
    hw = CARD_W
    c.setFillColor(RED)
    c.roundRect(hx, hy, hw, HDR_H, 6, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    title = torneo_nombre.upper()
    max_t = hw - 180
    while title and c.stringWidth(title, "Helvetica-Bold", 13) > max_t:
        title = title[:-1]
    c.drawString(hx + 14, hy + 13, title)
    c.setFont("Helvetica", 8)
    c.drawRightString(hx + hw - 14, hy + 13, "CUADRO DEL TORNEO")

    # generar QR con logo
    qr_buf = _generar_qr_pil(url)
    qr_reader = ImageReader(qr_buf)

    cx = PAGE_W / 2

    # distribuir el espacio disponible en 4 zonas verticales:
    #   [cabecera] — espacio — [título+subtítulo] — espacio — [QR] — espacio — [URL] — margen
    content_top = hy - 20          # punto de inicio bajo la cabecera
    content_bot = MARGIN + 20      # punto de fin sobre el margen inferior
    available   = content_top - content_bot   # ≈ 710 pt

    qr_size     = 260
    title_block = 44   # alto del bloque título+subtítulo (2 líneas)
    url_block   = 20
    gap         = (available - qr_size - title_block - url_block) / 3   # 3 huecos iguales

    url_y       = content_bot
    qr_y        = url_y + url_block + gap
    title_y     = qr_y + qr_size + gap   # base del bloque de texto

    # borde suave alrededor del QR
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(BORDER)
    c.setLineWidth(1)
    c.roundRect(cx - qr_size / 2 - 16, qr_y - 16, qr_size + 32, qr_size + 32, 14, fill=1, stroke=1)

    c.drawImage(qr_reader, cx - qr_size / 2, qr_y, qr_size, qr_size, mask="auto")

    # texto encima del QR
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(DARK)
    c.drawCentredString(cx, title_y + 22, "ESCANEA PARA VER EL CUADRO DEL TORNEO")
    c.setFont("Helvetica", 10.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, title_y + 4, "Consulta resultados y clasificación en tiempo real")

    # URL debajo del QR
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    url_text = url
    max_url_w = CARD_W - 40
    while url_text and c.stringWidth(url_text, "Helvetica", 7.5) > max_url_w:
        url_text = url_text[:-1]
    c.drawCentredString(cx, url_y + 6, url_text)


# ── Bloque "siguiente ronda" ───────────────────────────────────────────────────

NEXT_STRIP   = HexColor("#005BAB")   # azul RFFM para diferenciar del rojo de grupo
NEXT_BG      = HexColor("#EFF6FF")
NEXT_BORDER  = HexColor("#BFDBFE")
NEXT_DARK    = HexColor("#1E3A5F")
NEXT_MUTED   = HexColor("#6B8EAD")

NXT_HDR_H = 18   # altura de la cabecera del bloque siguiente ronda
NXT_CARD_H = 56  # tarjeta más compacta para la siguiente ronda


def _draw_next_round_card(c, x: float, y: float, partido: dict, cache: dict):
    """Tarjeta compacta para el partido de siguiente ronda (estilo diferenciado)."""
    w, h = CARD_W, NXT_CARD_H

    # fondo azul muy suave + borde
    c.setFillColor(NEXT_BG)
    c.setStrokeColor(NEXT_BORDER)
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, CORNER, fill=1, stroke=1)

    # barra inferior de metadatos
    bar_h = INFO_H
    c.setFillColor(HexColor("#DBEAFE"))
    c.rect(x + CORNER, y, w - 2 * CORNER, bar_h, fill=1, stroke=0)
    c.roundRect(x, y, w, bar_h, CORNER, fill=1, stroke=0)
    c.setStrokeColor(NEXT_BORDER)
    c.setLineWidth(0.4)
    c.line(x + CORNER, y + bar_h, x + w - CORNER, y + bar_h)

    meta_parts = []
    fecha = partido.get("fecha")
    if fecha:
        try:
            dt = datetime.strptime(str(fecha)[:10], "%Y-%m-%d")
            meta_parts.append(dt.strftime("%d/%m/%Y"))
        except Exception:
            meta_parts.append(str(fecha)[:10])
    hora = partido.get("hora")
    if hora:
        meta_parts.append(str(hora)[:5])
    campo = partido.get("campo")
    if campo:
        meta_parts.append(campo)

    if meta_parts:
        c.setFont("Helvetica", 6.5)
        c.setFillColor(NEXT_MUTED)
        c.drawCentredString(x + w / 2, y + 4.5, "   ·   ".join(meta_parts))
    else:
        c.setFont("Helvetica-Oblique", 6.5)
        c.setFillColor(NEXT_MUTED)
        c.drawCentredString(x + w / 2, y + 4.5, "Fecha · hora · campo pendientes")

    # zona de contenido
    content_y = y + bar_h
    content_h = h - bar_h
    center_y  = content_y + content_h / 2

    shield_s  = 28   # escudo más pequeño
    vs_cx     = x + w / 2

    # VS central
    c.setFillColor(NEXT_STRIP)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(vs_cx, center_y - 4, "VS")

    # zonas de equipo
    left_x1  = x + PAD_X
    left_x2  = vs_cx - VS_W / 2 - 6
    right_x1 = vs_cx + VS_W / 2 + 6
    right_x2 = x + w - PAD_X

    img_l = _fetch_img(partido.get("escudo_local"), cache)
    img_v = _fetch_img(partido.get("escudo_visitante"), cache)
    local_name = partido.get("nombre_local", "—")
    visit_name = partido.get("nombre_visitante", "—")

    # LOCAL
    shield_cx_l = left_x1 + shield_s / 2
    _draw_shield(c, img_l, shield_cx_l, center_y, shield_s)
    name_x_l  = left_x1 + shield_s + 8
    name_mw_l = left_x2 - name_x_l
    name_l, sz_l = _fit_name(c, local_name, "Helvetica-Bold", 10, name_mw_l)
    c.setFillColor(NEXT_DARK)
    c.setFont("Helvetica-Bold", sz_l)
    c.drawString(name_x_l, center_y - sz_l / 2, name_l)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(NEXT_MUTED)
    c.drawString(name_x_l, center_y + sz_l / 2 + 2, "LOCAL")

    # VISITANTE
    shield_cx_v = right_x2 - shield_s / 2
    _draw_shield(c, img_v, shield_cx_v, center_y, shield_s)
    name_x2_v  = right_x2 - shield_s - 8
    name_mw_v  = name_x2_v - right_x1
    name_v, sz_v = _fit_name(c, visit_name, "Helvetica-Bold", 10, name_mw_v)
    c.setFillColor(NEXT_DARK)
    c.setFont("Helvetica-Bold", sz_v)
    c.drawRightString(name_x2_v, center_y - sz_v / 2, name_v)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(NEXT_MUTED)
    c.drawRightString(name_x2_v, center_y + sz_v / 2 + 2, "VISITANTE")


def _draw_next_round_header(c, x: float, y: float, label: str):
    """Cabecera delgada azul para el bloque de siguiente ronda."""
    w = CARD_W
    c.setFillColor(NEXT_BG)
    c.setStrokeColor(NEXT_BORDER)
    c.setLineWidth(0.6)
    c.roundRect(x, y, w, NXT_HDR_H, 4, fill=1, stroke=1)

    c.setFillColor(NEXT_DARK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 10, y + 5.5, "SIGUIENTE RONDA — " + label.upper())

    c.setFont("Helvetica-Oblique", 6.5)
    c.setFillColor(NEXT_MUTED)
    c.drawRightString(x + w - 10, y + 5.5, "En caso de clasificarse")


# ── Función principal ──────────────────────────────────────────────────────────

CARD_GAP = 6     # espacio vertical entre tarjetas
GRP_GAP  = 14    # espacio extra entre grupos
HDR_H    = 38    # altura de la cabecera de página


def generar_pdf_partidos(grupos_ordenados: list, torneo_nombre: str, url_vista: str | None = None) -> bytes:
    """
    Genera el PDF con tarjetas de partidos horizontales a ancho completo.

    grupos_ordenados: lista de (grupo_id, info) donde
        info = {"nombre": str, "orden_cuadro": int|None, "partidos": [dict, ...]}
    torneo_nombre: nombre del torneo para la cabecera.
    url_vista: URL pública del bracket; si se proporciona, se añade una última página con QR.
    """
    buf = io.BytesIO()
    c   = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Partidos — {torneo_nombre}")
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}

    def draw_page_header():
        hx = MARGIN
        hy = PAGE_H - MARGIN - HDR_H
        hw = CARD_W
        c.setFillColor(RED)
        c.roundRect(hx, hy, hw, HDR_H, 6, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 13)
        title = torneo_nombre.upper()
        max_t = hw - 180
        while title and c.stringWidth(title, "Helvetica-Bold", 13) > max_t:
            title = title[:-1]
        c.drawString(hx + 14, hy + 13, title)
        c.setFont("Helvetica", 8)
        c.drawRightString(hx + hw - 14, hy + 13, "CALENDARIO DE PARTIDOS")

    def new_page():
        c.showPage()
        draw_page_header()
        return PAGE_H - MARGIN - HDR_H - 10

    draw_page_header()
    y = PAGE_H - MARGIN - HDR_H - 10   # cursor: top del contenido

    for _gid, info in grupos_ordenados:
        partidos = info.get("partidos", [])
        if not partidos:
            continue

        # espacio para cabecera de grupo + al menos 1 tarjeta
        needed = GH + CARD_GAP + CARD_H
        if y - needed < MARGIN:
            y = new_page()

        y -= GRP_GAP
        # cabecera de grupo
        _draw_group_header(c, MARGIN, y - GH, info["nombre"], len(partidos))
        y -= GH + CARD_GAP

        for partido in partidos:
            if y - CARD_H < MARGIN:
                y = new_page()
                _draw_group_header(c, MARGIN, y - GH, info["nombre"] + " (cont.)", 0)
                y -= GH + CARD_GAP

            jornada = partido.get("jornada")
            jornada_label = f"Jornada {jornada}" if jornada is not None else ""

            _draw_card(c, MARGIN, y - CARD_H, partido, info["nombre"], jornada_label, img_cache)
            y -= CARD_H + CARD_GAP

        # ── Partidos de la siguiente ronda (si los hay) ───────────────────────
        partidos_sig = info.get("partidos_siguiente", [])
        if partidos_sig:
            # nombre del grupo siguiente (guardado en _grupo_nombre del primer partido)
            sig_nombre = partidos_sig[0].get("_grupo_nombre", "Siguiente ronda")
            needed_next = CARD_GAP + NXT_HDR_H + CARD_GAP + NXT_CARD_H
            if y - needed_next < MARGIN:
                y = new_page()

            y -= CARD_GAP
            _draw_next_round_header(c, MARGIN, y - NXT_HDR_H, sig_nombre)
            y -= NXT_HDR_H + CARD_GAP

            for ps in partidos_sig:
                if y - NXT_CARD_H < MARGIN:
                    y = new_page()
                _draw_next_round_card(c, MARGIN, y - NXT_CARD_H, ps, img_cache)
                y -= NXT_CARD_H + CARD_GAP

    if url_vista:
        _draw_qr_page(c, url_vista, torneo_nombre)

    c.save()
    return buf.getvalue()
