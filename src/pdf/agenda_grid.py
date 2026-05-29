"""
PDF agenda grid — portrait A4, one page per day, campos as columns.
Proportional time blocks with team names and (when tall enough) shields.
If any block would be shorter than MIN_BLOCK_H, the day is split across two pages.
"""
import io
from collections import defaultdict
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas as pdf_canvas

from ._utils import fetch_img, draw_shield_centered, torneo_pdf_color, RFFM_LOGO_URL

PAGE_W, PAGE_H = A4
MARGIN       = 18
HEADER_H     = 30
CAMPO_HDR_H  = 16
AXIS_W       = 42
SHIELD_MIN_H = 48   # block must be at least this tall to draw shields
SHIELD_SZ    = 20
MIN_BLOCK_H  = 18   # minimum block height; split day if any block would be shorter

DARK  = HexColor("#1A1A1A")
MUTED = HexColor("#1A1A1A")
RED   = HexColor("#CC0000")

DIAS_ES  = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _hm_to_min(t) -> int:
    try:
        parts = str(t)[:5].split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def _min_to_hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _trunc(c, text: str, font: str, size: float, max_w: float) -> str:
    while text and c.stringWidth(text, font, size) > max_w:
        text = text[:-1]
    return text


def _dia_ini(campos_dia: dict, hora_ini_min: int) -> int:
    ini = 23 * 60
    for campo_ps in campos_dia.values():
        for p in campo_ps:
            p_min = _hm_to_min(str(p.get("hora") or "")[:5])
            if p_min > 0:
                ini = min(ini, p_min)
    if ini >= 23 * 60:
        ini = hora_ini_min or (8 * 60)
    ini = (ini // 30) * 30
    return min(ini, hora_ini_min) if hora_ini_min else ini


def _dia_fin(campos_dia: dict, ini_min: int, hora_fin_min: int) -> int:
    if hora_fin_min:
        return hora_fin_min
    fin = ini_min + 60
    for campo_ps in campos_dia.values():
        for p in campo_ps:
            p_min = _hm_to_min(str(p.get("hora") or "")[:5])
            fin = max(fin, p_min + (p.get("duracion_partido") or 50))
    fin = (fin + 29) // 30 * 30
    return fin


def _min_block_h(campos_dia: dict, hora_ini: int, hora_fin: int, px: float) -> float:
    """Return the height of the shortest block in this time window."""
    min_bh = float("inf")
    for campo_ps in campos_dia.values():
        for p in campo_ps:
            p_min = _hm_to_min(str(p.get("hora") or "")[:5])
            dur = p.get("duracion_partido") or 50
            end_min = p_min + dur
            if p_min >= hora_fin or end_min <= hora_ini:
                continue
            clip_start = max(p_min, hora_ini)
            clip_end   = min(end_min, hora_fin)
            bh = (clip_end - clip_start) * px - 1
            if bh < min_bh:
                min_bh = bh
    return min_bh if min_bh != float("inf") else MIN_BLOCK_H


def _draw_day_page(
    c,
    fecha_iso: str,
    campos_dia: dict,
    campo_list: list,
    hora_ini: int,
    hora_fin: int,
    titulo: str,
    img_cache: dict,
    rffm_logo,
    parte: int = 0,   # 0 = página única, 1 = primera mitad, 2 = segunda mitad
):
    n = len(campo_list)
    available_w = PAGE_W - 2 * MARGIN - AXIS_W
    campo_w = available_w / n if n > 0 else available_w
    grid_x  = MARGIN + AXIS_W

    grid_top = PAGE_H - MARGIN - HEADER_H - CAMPO_HDR_H
    grid_bot = MARGIN
    grid_h   = grid_top - grid_bot

    total_min = max(hora_fin - hora_ini, 30)
    px = grid_h / total_min

    # ── Page header ───────────────────────────────────────────────────────────
    hdr_y = PAGE_H - MARGIN - HEADER_H
    c.setFillColor(RED)
    c.roundRect(MARGIN, hdr_y, PAGE_W - 2 * MARGIN, HEADER_H, 5, fill=1, stroke=0)

    try:
        dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
        titulo_dia = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month-1]} de {dt.year}"
    except Exception:
        titulo_dia = fecha_iso

    if parte == 1:
        titulo_dia += f"  ({_min_to_hm(hora_ini)}–{_min_to_hm(hora_fin)}, parte 1/2)"
    elif parte == 2:
        titulo_dia += f"  ({_min_to_hm(hora_ini)}–{_min_to_hm(hora_fin)}, parte 2/2)"

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 12, hdr_y + 10, titulo_dia.upper())
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN - 10, hdr_y + 10, titulo.upper())

    # ── Campo column headers ──────────────────────────────────────────────────
    for i, campo in enumerate(campo_list):
        cx = grid_x + i * campo_w
        c.setFillColor(HexColor("#1A3A5F"))
        c.rect(cx, grid_top, campo_w - 1, CAMPO_HDR_H, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.5)
        label = _trunc(c, (campo or "SIN CAMPO").upper(), "Helvetica-Bold", 7.5, campo_w - 10)
        c.drawCentredString(cx + campo_w / 2, grid_top + 5, label)

    # ── Grid background ───────────────────────────────────────────────────────
    c.setFillColor(HexColor("#F8F8F8"))
    c.rect(grid_x, grid_bot, available_w, grid_h, fill=1, stroke=0)

    # Alternating hour bands
    h = ((hora_ini + 59) // 60) * 60
    while h < hora_fin:
        band_top = grid_top - (h - hora_ini) * px
        band_bot = grid_top - (min(h + 60, hora_fin) - hora_ini) * px
        if (h // 60) % 2 == 0:
            c.setFillColor(HexColor("#F0F4F8"))
            c.rect(grid_x, band_bot, available_w, band_top - band_bot, fill=1, stroke=0)
        h += 60

    # ── Hour lines + axis labels ──────────────────────────────────────────────
    h = ((hora_ini + 59) // 60) * 60
    while h <= hora_fin:
        ly = grid_top - (h - hora_ini) * px
        c.setStrokeColor(HexColor("#AAAAAA"))
        c.setLineWidth(0.5)
        c.setDash()
        c.line(grid_x, ly, PAGE_W - MARGIN, ly)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(grid_x - 4, ly - 4, _min_to_hm(h))
        h += 60

    h = ((hora_ini + 59) // 60) * 60 + 30
    while h < hora_fin:
        ly = grid_top - (h - hora_ini) * px
        c.setStrokeColor(HexColor("#CCCCCC"))
        c.setLineWidth(0.3)
        c.setDash(3, 4)
        c.line(grid_x, ly, PAGE_W - MARGIN, ly)
        c.setDash()
        h += 60

    # Vertical campo separators
    for i in range(n + 1):
        lx = grid_x + i * campo_w
        c.setStrokeColor(HexColor("#BBBBBB"))
        c.setLineWidth(0.4)
        c.setDash()
        c.line(lx, grid_bot, lx, grid_top)

    # Grid outer border
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(0.6)
    c.rect(grid_x, grid_bot, available_w, grid_h, fill=0, stroke=1)

    # ── Match blocks ──────────────────────────────────────────────────────────
    for i, campo in enumerate(campo_list):
        cx = grid_x + i * campo_w
        ps = sorted(campos_dia[campo], key=lambda p: str(p.get("hora") or ""))

        for p in ps:
            p_min   = _hm_to_min(str(p.get("hora") or "")[:5])
            dur     = p.get("duracion_partido") or 50
            end_min = p_min + dur

            if p_min >= hora_fin or end_min <= hora_ini:
                continue

            clip_start = max(p_min, hora_ini)
            clip_end   = min(end_min, hora_fin)

            bh = (clip_end - clip_start) * px - 1
            by = grid_top - (clip_end - hora_ini) * px
            bx = cx + 1.5
            bw = campo_w - 3

            bg_color, border_color = torneo_pdf_color(p.get("torneo_id"))
            c.setFillColor(bg_color)
            c.setStrokeColor(border_color)
            c.setLineWidth(0.5)
            c.roundRect(bx, by, bw, bh, 2, fill=1, stroke=1)

            c.setFillColor(border_color)
            c.rect(bx, by, 3.5, bh, fill=1, stroke=0)

            text_x = bx + 6
            text_w = bw - 10
            loc    = p.get("nombre_local") or "—"
            vis    = p.get("nombre_visitante") or "—"
            rl, rv = p.get("resultado_local"), p.get("resultado_visitante")
            grp    = p.get("nombre_grupo") or ""
            torneo = p.get("nombre_torneo") or ""

            marc_str = f"{rl}–{rv}" if rl is not None and rv is not None else None

            c.setFillColor(DARK)

            if bh >= SHIELD_MIN_H:
                sh_pad  = 4
                sh_cy   = by + bh / 2
                sh_cx_l = bx + sh_pad + SHIELD_SZ / 2
                sh_cx_r = bx + bw - sh_pad - SHIELD_SZ / 2
                inner_w = max(bw - 2 * (sh_pad * 2 + SHIELD_SZ), 20)
                cx_text = bx + bw / 2

                img_l = fetch_img(p.get("escudo_local"), img_cache) or rffm_logo
                img_v = fetch_img(p.get("escudo_visitante"), img_cache) or rffm_logo
                draw_shield_centered(c, img_l, rffm_logo, sh_cx_l, sh_cy, SHIELD_SZ)
                draw_shield_centered(c, img_v, rffm_logo, sh_cx_r, sh_cy, SHIELD_SZ)

                meta_sz = 6
                team_sz = 6
                vs_sz   = 4.5
                gap     = 1.5
                n_meta  = (1 if torneo else 0) + (1 if grp else 0)
                stack_h = (n_meta * (meta_sz + gap)
                           + team_sz + gap + vs_sz + gap + team_sz)
                ty = sh_cy + stack_h / 2

                if torneo:
                    ty -= meta_sz
                    c.setFont("Helvetica-Bold", meta_sz)
                    c.setFillColor(MUTED)
                    c.drawCentredString(cx_text, ty, _trunc(c, torneo, "Helvetica-Bold", meta_sz, inner_w))
                    ty -= gap
                if grp:
                    ty -= meta_sz
                    c.setFont("Helvetica", meta_sz)
                    c.setFillColor(MUTED)
                    c.drawCentredString(cx_text, ty, _trunc(c, grp, "Helvetica", meta_sz, inner_w))
                    ty -= gap

                ty -= team_sz
                c.setFont("Helvetica-Bold", team_sz)
                c.setFillColor(DARK)
                c.drawCentredString(cx_text, ty, _trunc(c, loc, "Helvetica-Bold", team_sz, inner_w))
                ty -= team_sz + gap

                ty -= vs_sz
                c.setFont("Helvetica-Oblique", vs_sz)
                c.setFillColor(MUTED)
                c.drawCentredString(cx_text, ty, "vs")
                ty -= gap

                ty -= team_sz
                c.setFont("Helvetica-Bold", team_sz)
                c.setFillColor(DARK)
                c.drawCentredString(cx_text, ty, _trunc(c, vis, "Helvetica-Bold", team_sz, inner_w))

                if marc_str:
                    ty -= team_sz + gap
                    c.setFont("Helvetica-Bold", 5)
                    c.setFillColor(RED)
                    c.drawCentredString(cx_text, ty, marc_str)

            elif bh >= MIN_BLOCK_H:
                ty = by + bh - 6 - 2
                if torneo:
                    c.setFont("Helvetica-Bold", 6)
                    c.setFillColor(MUTED)
                    c.drawString(text_x, ty, _trunc(c, torneo, "Helvetica-Bold", 6,
                                                    text_w - (25 if marc_str else 0)))
                    if marc_str:
                        c.setFillColor(RED)
                        c.drawRightString(bx + bw - 3, ty, marc_str)
                    ty -= 6 + 2
                if grp:
                    if ty > by + 1:
                        c.setFont("Helvetica", 5.5)
                        c.setFillColor(MUTED)
                        c.drawString(text_x, ty, _trunc(c, grp, "Helvetica", 5.5, text_w))
                        ty -= 5.5 + 2
                if ty > by + 1:
                    c.setFont("Helvetica-Bold", 5.5)
                    c.setFillColor(DARK)
                    c.drawString(text_x, ty, _trunc(c, f"{loc} – {vis}", "Helvetica-Bold", 5.5, text_w))

            else:
                # Fallback compact: nombre en una sola línea (no debería ocurrir tras el split)
                sz  = 5.5
                sep = " – "
                sep_w  = c.stringWidth(sep, "Helvetica-Bold", sz)
                marc_w = (c.stringWidth("  " + marc_str, "Helvetica-Bold", sz) if marc_str else 0)
                half_w = max((text_w - sep_w - marc_w) / 2, 12)
                loc_t  = _trunc(c, loc, "Helvetica-Bold", sz, half_w)
                vis_t  = _trunc(c, vis, "Helvetica-Bold", sz,
                                text_w - sep_w - marc_w - c.stringWidth(loc_t, "Helvetica-Bold", sz))
                c.setFont("Helvetica-Bold", sz)
                c.setFillColor(DARK)
                ty = by + max(bh / 2 - sz / 2, 1)
                c.drawString(text_x, ty, loc_t + sep + vis_t)
                if marc_str:
                    c.setFillColor(RED)
                    c.drawRightString(bx + bw - 3, ty, marc_str)

    c.showPage()


def generar_pdf_agenda_grid(
    partidos: list,
    titulo: str,
    hora_ini_min: int = 480,
    hora_fin_min: int = 1320,
) -> bytes:
    """Returns bytes of a portrait PDF with one page per day (or two if blocks are too small)."""

    por_fecha: dict = defaultdict(lambda: defaultdict(list))
    for p in partidos:
        fecha = str(p.get("fecha") or "")[:10]
        campo = p.get("campo") or "Sin campo"
        por_fecha[fecha][campo].append(p)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(titulo)
    c.setAuthor("Gestor Torneos RFFM")

    img_cache: dict = {}
    rffm_logo = fetch_img(RFFM_LOGO_URL, img_cache)

    grid_top = PAGE_H - MARGIN - HEADER_H - CAMPO_HDR_H
    grid_bot = MARGIN
    grid_h   = grid_top - grid_bot

    CAMPOS_POR_PAGINA = 2

    for fecha_iso in sorted(por_fecha.keys()):
        campos_dia = por_fecha[fecha_iso]
        campo_list = sorted(campos_dia.keys())

        hora_ini_dia  = _dia_ini(campos_dia, hora_ini_min)
        hora_fin_dia  = _dia_fin(campos_dia, hora_ini_dia, hora_fin_min)
        total_min_dia = max(hora_fin_dia - hora_ini_dia, 30)
        px = grid_h / total_min_dia

        # Paginar campos de CAMPOS_POR_PAGINA en CAMPOS_POR_PAGINA
        chunks = [campo_list[i:i + CAMPOS_POR_PAGINA]
                  for i in range(0, len(campo_list), CAMPOS_POR_PAGINA)]

        for chunk in chunks:
            campos_chunk = {k: campos_dia[k] for k in chunk if k in campos_dia}
            if _min_block_h(campos_chunk, hora_ini_dia, hora_fin_dia, px) < MIN_BLOCK_H:
                mid = round((hora_ini_dia + hora_fin_dia) / 2 / 30) * 30
                mid = max(hora_ini_dia + 30, min(mid, hora_fin_dia - 30))
                _draw_day_page(c, fecha_iso, campos_dia, chunk,
                               hora_ini_dia, mid, titulo, img_cache, rffm_logo, parte=1)
                _draw_day_page(c, fecha_iso, campos_dia, chunk,
                               mid, hora_fin_dia, titulo, img_cache, rffm_logo, parte=2)
            else:
                _draw_day_page(c, fecha_iso, campos_dia, chunk,
                               hora_ini_dia, hora_fin_dia, titulo, img_cache, rffm_logo)

    # ── Página de leyenda ─────────────────────────────────────────────────────
    torneo_legend: dict[str, str] = {}
    for p in partidos:
        tid = p.get("torneo_id") or ""
        if tid and tid not in torneo_legend:
            torneo_legend[tid] = p.get("nombre_torneo") or tid

    if torneo_legend:
        c.setPageSize(A4)

        c.setFillColor(RED)
        c.roundRect(MARGIN, PAGE_H - MARGIN - HEADER_H,
                    PAGE_W - 2 * MARGIN, HEADER_H, 5, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN + 12, PAGE_H - MARGIN - HEADER_H + 10, "LEYENDA DE TORNEOS")
        c.setFont("Helvetica", 8)
        c.drawRightString(PAGE_W - MARGIN - 10, PAGE_H - MARGIN - HEADER_H + 10, titulo.upper())

        items   = list(torneo_legend.items())
        item_h  = 24
        swatch_w = 32
        name_w  = (PAGE_W - 2 * MARGIN - 30) / 2 - swatch_w - 10
        col_w   = swatch_w + name_w + 18
        x0 = MARGIN + 10
        y0 = PAGE_H - MARGIN - HEADER_H - CAMPO_HDR_H - 10

        for idx, (tid, nombre) in enumerate(items):
            col_i = idx % 2
            row_i = idx // 2
            ix = x0 + col_i * (col_w + 20)
            iy = y0 - row_i * item_h

            bg_color, border_color = torneo_pdf_color(tid)

            c.setFillColor(bg_color)
            c.setStrokeColor(border_color)
            c.setLineWidth(1)
            c.roundRect(ix, iy - item_h + 4, swatch_w, item_h - 6, 3, fill=1, stroke=1)

            c.setFillColor(border_color)
            c.rect(ix, iy - item_h + 4, 5, item_h - 6, fill=1, stroke=0)

            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 9)
            label = _trunc(c, nombre, "Helvetica-Bold", 9, name_w)
            c.drawString(ix + swatch_w + 6, iy - item_h + 9, label)

        c.showPage()

    c.save()
    return buf.getvalue()
