"""
Genera imagen JPG de un terreno de fútbol 11 (vista cenital) con dos mitades.
Mitad izquierda = Campo B, mitad derecha = Campo A.
Los partidos de cada campo se superponen en su respectiva mitad.
"""
import io
import math
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

# ── Dimensiones de imagen ──────────────────────────────────────────────────────
IMG_W, IMG_H = 1800, 1100
MX, MY = 70, 70           # márgenes exteriores
FW = IMG_W - 2 * MX       # ancho campo en px  = 1660
FH = IMG_H - 2 * MY       # alto campo en px   = 960
FX, FY = MX, MY           # esquina superior-izquierda del campo
CX = FX + FW / 2          # línea de centro (x)
CY = FY + FH / 2          # centro vertical
SX = FW / 105.0            # px por metro (eje horizontal)
SY = FH / 68.0             # px por metro (eje vertical)
LW = 4                     # grosor de líneas de campo

# ── Colores ────────────────────────────────────────────────────────────────────
GL = (56, 142, 43)         # césped claro
GD = (47, 120, 36)         # césped oscuro
W  = (255, 255, 255)       # blanco
K  = (0, 0, 0)             # negro

# ── Fuentes (Windows → fallback cross-platform) ────────────────────────────────
_BOLD_FONTS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_REG_FONTS = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (_BOLD_FONTS if bold else _REG_FONTS):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _trunc(draw, text: str, font, max_w: float) -> str:
    while text and _text_w(draw, text, font) > max_w:
        text = text[:-1]
    return text


# ── Dibujo del campo ───────────────────────────────────────────────────────────

def _draw_pitch(draw: ImageDraw.ImageDraw) -> None:
    # Franjas de césped
    n = 14
    sw = FW / n
    for i in range(n):
        c = GL if i % 2 == 0 else GD
        draw.rectangle([int(FX + i * sw), FY, int(FX + (i + 1) * sw) + 1, FY + FH], fill=c)

    # Contorno exterior
    draw.rectangle([FX, FY, FX + FW, FY + FH], outline=W, width=LW)

    # Línea de centro
    draw.line([(CX, FY), (CX, FY + FH)], fill=W, width=LW)

    # Círculo central (r = 9.15 m)
    rx, ry = 9.15 * SX, 9.15 * SY
    draw.ellipse([CX - rx, CY - ry, CX + rx, CY + ry], outline=W, width=LW)
    draw.ellipse([CX - 5, CY - 5, CX + 5, CY + 5], fill=W)

    # Áreas de penalti (16.5 m profundidad, 40.32 m ancho)
    pa_d, pa_h = 16.5 * SX, 20.16 * SY
    draw.rectangle([FX,            CY - pa_h, FX + pa_d,      CY + pa_h], outline=W, width=LW)
    draw.rectangle([FX + FW - pa_d, CY - pa_h, FX + FW,       CY + pa_h], outline=W, width=LW)

    # Áreas de portería (5.5 m × 18.32 m)
    ga_d, ga_h = 5.5 * SX, 9.16 * SY
    draw.rectangle([FX,             CY - ga_h, FX + ga_d,      CY + ga_h], outline=W, width=LW)
    draw.rectangle([FX + FW - ga_d, CY - ga_h, FX + FW,        CY + ga_h], outline=W, width=LW)

    # Porterías (7.32 m ancho, ~2.44 m profundidad)
    g_d, g_h = 4 * SX, 3.66 * SY
    draw.rectangle([FX - g_d,      CY - g_h, FX,           CY + g_h], outline=W, width=2)
    draw.rectangle([FX + FW,       CY - g_h, FX + FW + g_d, CY + g_h], outline=W, width=2)

    # Puntos de penalti (11 m)
    for ps_x in [FX + 11 * SX, FX + FW - 11 * SX]:
        draw.ellipse([ps_x - 5, CY - 5, ps_x + 5, CY + 5], fill=W)

    # Arcos del área (D)
    r_d = 9.15
    rx_d, ry_d = r_d * SX, r_d * SY
    cos_t = 5.5 / r_d   # = (16.5 - 11) / 9.15
    if cos_t <= 1:
        theta = math.degrees(math.acos(cos_t))   # ≈ 53°
        ps_lx = FX + 11 * SX
        draw.arc([ps_lx - rx_d, CY - ry_d, ps_lx + rx_d, CY + ry_d],
                 -theta, theta, fill=W, width=LW)
        ps_rx = FX + FW - 11 * SX
        draw.arc([ps_rx - rx_d, CY - ry_d, ps_rx + rx_d, CY + ry_d],
                 180 - theta, 180 + theta, fill=W, width=LW)

    # Arcos de córner (r = 1 m)
    cr_x, cr_y = SX, SY
    for (cx_c, cy_c, a1, a2) in [
        (FX,       FY,       0,   90),
        (FX + FW,  FY,       90,  180),
        (FX + FW,  FY + FH,  180, 270),
        (FX,       FY + FH,  270, 360),
    ]:
        draw.arc(
            [cx_c - cr_x, cy_c - cr_y, cx_c + cr_x, cy_c + cr_y],
            a1, a2, fill=W, width=LW,
        )


# ── Superposición de partidos ──────────────────────────────────────────────────

_DIA  = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_MES  = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def _fecha_label(fecha_iso: str) -> str:
    try:
        d = datetime.strptime(fecha_iso[:10], "%Y-%m-%d")
        return f"── {_DIA[d.weekday()]} {d.day} {_MES[d.month - 1]} ──"
    except Exception:
        return f"── {fecha_iso} ──"


def _write_half(draw: ImageDraw.ImageDraw, partidos: list,
                x_left: float, x_right: float, titulo: str) -> None:
    mid_x  = (x_left + x_right) / 2
    half_w = x_right - x_left

    # Fonts
    f_title  = _font(40, bold=True)
    f_date   = _font(20, bold=True)
    f_match  = _font(20)

    panel_y0 = FY + 22
    panel_y1 = FY + FH - 22
    text_x   = x_left + 24
    max_text_w = half_w - 48

    # Título de la mitad
    draw.text((mid_x, panel_y0 + 36), titulo.upper(),
              fill=W, font=f_title, anchor="mm", stroke_width=2, stroke_fill=K)

    if not partidos:
        draw.text((mid_x, (panel_y0 + panel_y1) / 2), "Sin partidos",
                  fill=(160, 160, 160), font=_font(24), anchor="mm")
        return

    # Agrupar por fecha
    by_date: dict[str, list] = {}
    for p in partidos:
        d = str(p.get("fecha") or "sin fecha")[:10]
        by_date.setdefault(d, []).append(p)

    LINE_H  = 28
    DATE_H  = 32
    y       = panel_y0 + 88
    MAX_Y   = panel_y1 - 12

    for fecha in sorted(by_date):
        if y + DATE_H > MAX_Y:
            break

        # Separador de fecha
        label = _fecha_label(fecha)
        draw.text((mid_x, y + DATE_H / 2), label,
                  fill=(190, 230, 190), font=f_date, anchor="mm")
        y += DATE_H + 4

        for p in by_date[fecha]:
            if y + LINE_H > MAX_Y:
                break

            hora  = str(p.get("hora") or "")[:5] or "—"
            local = p.get("nombre_local")  or "?"
            visit = p.get("nombre_visitante") or "?"
            gl    = p.get("goles_local")
            gv    = p.get("goles_visitante")
            score = f"  ({gl}–{gv})" if (gl is not None and gv is not None) else ""

            line = f"{hora}   {local}  vs  {visit}{score}"
            line = _trunc(draw, line, f_match, max_text_w)

            draw.text((text_x, y + LINE_H / 2), line,
                      fill=W, font=f_match, anchor="lm",
                      stroke_width=1, stroke_fill=K)
            y += LINE_H

        y += 8  # hueco entre fechas


# ── Función pública ────────────────────────────────────────────────────────────

def generar_imagen_campo(
    partidos_b: list, nombre_b: str,
    partidos_a: list, nombre_a: str,
) -> bytes:
    """
    Genera un JPEG del terreno de juego con los partidos superpuestos.
    Mitad izquierda  → nombre_b (Campo B)
    Mitad derecha    → nombre_a (Campo A)
    """
    # 1. Base RGB: campo vacío
    img = Image.new("RGB", (IMG_W, IMG_H), K)
    draw_base = ImageDraw.Draw(img)
    _draw_pitch(draw_base)

    # 2. Panel semi-transparente sobre cada mitad
    overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    panel_y0 = FY + 22
    panel_y1 = FY + FH - 22
    for x0, x1 in [(FX, CX - LW // 2), (CX + LW // 2, FX + FW)]:
        pw = (x1 - x0) * 0.84
        px0 = (x0 + x1) / 2 - pw / 2
        px1 = (x0 + x1) / 2 + pw / 2
        ov.rectangle([px0, panel_y0, px1, panel_y1], fill=(0, 0, 0, 145))

    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)

    # 3. Texto sobre la imagen compuesta
    draw_text = ImageDraw.Draw(img_rgba)
    _write_half(draw_text, partidos_b, FX, CX, nombre_b)
    _write_half(draw_text, partidos_a, CX, FX + FW, nombre_a)

    # 4. Convertir a RGB y guardar como JPEG
    buf = io.BytesIO()
    img_rgba.convert("RGB").save(buf, format="JPEG", quality=92)
    return buf.getvalue()
