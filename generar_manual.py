"""Genera el manual de usuario de Gestor Torneo RFFM en PDF."""

from fpdf import FPDF
from datetime import date

# ── Paleta ──────────────────────────────────────────────────────────────────
ROJO_OSC  = (140,   0,   0)
ROJO      = (204,   0,   0)
GRIS      = (130, 130, 130)
GRIS_CLAR = (220, 220, 220)
NEGRO     = ( 26,  26,  26)
BLANCO    = (255, 255, 255)
DARK_BG   = ( 14,  17,  23)   # fondo Streamlit dark
SIDEBAR   = ( 30,  35,  45)

LOGO_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"
LOGO_TV  = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"


# ── Clase base ───────────────────────────────────────────────────────────────
class Manual(FPDF):

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*ROJO_OSC)
        self.rect(0, 0, 210, 9, style="F")
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*BLANCO)
        self.set_xy(10, 1.5)
        self.cell(140, 6, "Gestor Torneo RFFM - Manual de Usuario")
        self.set_x(0)
        self.cell(200, 6, f"Pagina {self.page_no()}", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRIS)
        self.cell(0, 6, f"Real Federacion de Futbol Madrilena  (c)  {date.today().year}", align="C")

    # ── Tipografia ────────────────────────────────────────────────────────────

    def seccion(self, num, titulo):
        self.ln(5)
        self.set_fill_color(*ROJO)
        self.set_text_color(*BLANCO)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, f"  {num}.  {titulo}", fill=True, ln=True)
        self.set_text_color(*NEGRO)
        self.ln(2)

    def subseccion(self, titulo):
        self.ln(1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ROJO_OSC)
        self.cell(0, 7, titulo, ln=True)
        self.set_text_color(*NEGRO)

    def p(self, texto):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*NEGRO)
        self.multi_cell(self.epw, 5.5, texto)
        self.ln(1.5)

    def li(self, items):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*NEGRO)
        for item in items:
            self.set_x(self.l_margin + 6)
            self.multi_cell(self.epw - 6, 5.5, f"-  {item}")

    def nota(self, texto):
        self.set_x(self.l_margin)
        self.set_fill_color(255, 252, 225)
        self.set_draw_color(200, 160, 0)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(100, 70, 0)
        self.multi_cell(self.epw, 5.5, f"  NOTA:  {texto}", border=1, fill=True)
        self.set_text_color(*NEGRO)
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def aviso(self, texto):
        self.set_x(self.l_margin)
        self.set_fill_color(255, 235, 235)
        self.set_draw_color(*ROJO)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*ROJO_OSC)
        self.multi_cell(self.epw, 5.5, f"  AVISO:  {texto}", border=1, fill=True)
        self.set_text_color(*NEGRO)
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    # ── Mockups de pantalla ───────────────────────────────────────────────────

    def _chrome(self, x, y, w, h):
        """Barra de navegador simulada."""
        self.set_fill_color(50, 50, 50)
        self.rect(x, y, w, 6, style="F")
        self.set_fill_color(80, 80, 80)
        for i, cx in enumerate([x+2, x+5, x+8]):
            self.circle(cx, y+3, 1.2, style="F")
        self.set_fill_color(240, 240, 240)
        self.rect(x+14, y+1, w-18, 4, style="F")
        self.set_font("Helvetica", "", 5)
        self.set_text_color(100, 100, 100)
        self.set_xy(x+15, y+1.5)
        self.cell(w-20, 3, "localhost:8501")
        self.set_text_color(*NEGRO)

    def mockup_login(self, x=None, y=None, w=None, h=110):
        x = x or self.l_margin
        y = y or self.get_y()
        w = w or self.epw
        # Fondo dark
        self.set_fill_color(*DARK_BG)
        self.rect(x, y, w, h, style="F")
        self._chrome(x, y, w, 6)
        # Tarjeta central
        cx, cw, ch = x + w*0.25, w*0.5, 55
        cy = y + (h - ch) / 2 + 2
        self.set_fill_color(30, 35, 48)
        self.set_draw_color(60, 65, 80)
        self.rect(cx, cy, cw, ch, style="DF")
        # Logo placeholder
        try:
            self.image(LOGO_URL, cx + cw/2 - 8, cy + 4, 16, 16)
        except Exception:
            self.set_fill_color(*ROJO)
            self.rect(cx + cw/2 - 8, cy + 4, 16, 16, style="F")
        # Titulo
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*BLANCO)
        self.set_xy(cx, cy + 22)
        self.cell(cw, 5, "Gestion de Campeonato RFFM", align="C", ln=True)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*GRIS)
        self.set_xy(cx, cy + 27)
        self.cell(cw, 4, "Acceso restringido", align="C", ln=True)
        # Inputs
        for label, dy in [("Usuario", 33), ("Contrasena", 40)]:
            self.set_fill_color(20, 25, 35)
            self.set_draw_color(70, 75, 90)
            self.rect(cx + 5, cy + dy, cw - 10, 5, style="DF")
            self.set_font("Helvetica", "", 5.5)
            self.set_text_color(100, 110, 130)
            self.set_xy(cx + 7, cy + dy + 0.8)
            self.cell(cw - 14, 3.5, label)
        # Boton
        self.set_fill_color(*ROJO)
        self.rect(cx + 5, cy + 47, cw - 10, 5, style="F")
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*BLANCO)
        self.set_xy(cx + 5, cy + 47.5)
        self.cell(cw - 10, 4, "Entrar", align="C")
        self.set_text_color(*NEGRO)
        self.set_xy(x, y + h)
        self.ln(3)

    def _sidebar(self, x, y, h, menu_activo="Dashboard"):
        sw = 42
        self.set_fill_color(*SIDEBAR)
        self.rect(x, y, sw, h, style="F")
        # Logo + titulo
        try:
            self.image(LOGO_URL, x + 3, y + 6, 8, 8)
        except Exception:
            pass
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*BLANCO)
        self.set_xy(x + 13, y + 7)
        self.cell(sw - 15, 4, "RFFM Torneos")
        # Selector torneo
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(150, 160, 180)
        self.set_xy(x + 3, y + 18)
        self.cell(sw - 6, 3.5, "Torneo activo:")
        self.set_fill_color(40, 45, 60)
        self.rect(x + 3, y + 22, sw - 6, 5, style="F")
        self.set_text_color(*BLANCO)
        self.set_xy(x + 4, y + 23)
        self.cell(sw - 8, 3.5, "Copa RFFM 2026")
        # Menu items
        items = ["Torneos", "Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual", "Sorteo"]
        for i, item in enumerate(items):
            iy = y + 32 + i * 8
            if item == menu_activo:
                self.set_fill_color(*ROJO)
                self.rect(x, iy - 0.5, sw, 7, style="F")
                self.set_text_color(*BLANCO)
            else:
                self.set_text_color(170, 180, 200)
            self.set_font("Helvetica", "B" if item == menu_activo else "", 5.5)
            self.set_xy(x + 6, iy + 0.5)
            self.cell(sw - 8, 5, item)
        self.set_text_color(*NEGRO)
        return sw

    def _topbar(self, x, y, w, titulo):
        self.set_fill_color(*DARK_BG)
        self.rect(x, y, w, 10, style="F")
        try:
            self.image(LOGO_URL, x + 3, y + 1, 8, 8)
        except Exception:
            pass
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*BLANCO)
        self.set_xy(x + 13, y + 1.5)
        self.cell(w, 7, titulo)
        self.set_text_color(*NEGRO)

    def mockup_con_sidebar(self, menu, contenido_fn, h=105):
        x = self.l_margin
        y = self.get_y()
        w = self.epw
        # Fondo global
        self.set_fill_color(*DARK_BG)
        self.rect(x, y, w, h, style="F")
        self._chrome(x, y, w, 6)
        sw = self._sidebar(x, y + 6, h - 6, menu_activo=menu)
        # Area de contenido
        cx = x + sw
        cw = w - sw
        self._topbar(cx, y + 6, cw, f"Gestion de Campeonato RFFM")
        contenido_fn(cx, y + 16, cw, h - 16)
        self.set_xy(x, y + h)
        self.ln(3)

    # ── Contenidos de mockup por pantalla ─────────────────────────────────────

    def _contenido_dashboard(self, x, y, w, h):
        pad = 3
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(170, 180, 200)
        self.set_xy(x + pad, y + pad)
        self.cell(w - pad*2, 4, "Copa RFFM 2026 - Torneo activo")
        # Metricas
        for i, (label, val) in enumerate([("Total Equipos", "32"), ("En Competicion", "32")]):
            mx = x + pad + i * (w - pad*2 - 4) / 2 + i * 2
            mw = (w - pad*2 - 4) / 2
            self.set_fill_color(30, 35, 48)
            self.rect(mx, y + 10, mw, 16, style="F")
            self.set_font("Helvetica", "", 5.5)
            self.set_text_color(150, 160, 180)
            self.set_xy(mx + 2, y + 12)
            self.cell(mw - 4, 3.5, label)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*BLANCO)
            self.set_xy(mx + 2, y + 16)
            self.cell(mw - 4, 8, val)
        # Buscador
        self.set_fill_color(30, 35, 48)
        self.rect(x + pad, y + 30, w - pad*2, 5, style="F")
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(100, 110, 130)
        self.set_xy(x + pad + 2, y + 31.5)
        self.cell(w - pad*2 - 4, 3, "Filtrar por nombre...")
        # Grid de equipos
        cols, rows = 4, 2
        ew = (w - pad*2 - (cols-1)*2) / cols
        for r in range(rows):
            for c in range(cols):
                ex = x + pad + c * (ew + 2)
                ey = y + 38 + r * 22
                self.set_fill_color(255, 255, 255)
                self.rect(ex, ey, ew, 19, style="F")
                self.set_fill_color(220, 220, 220)
                self.rect(ex + ew/2 - 5, ey + 2, 10, 10, style="F")
                self.set_font("Helvetica", "B", 5)
                self.set_text_color(40, 40, 40)
                self.set_xy(ex, ey + 13)
                self.cell(ew, 4, f"EQUIPO {r*cols+c+1}", align="C")
        self.set_text_color(*NEGRO)

    def _contenido_carga(self, x, y, w, h):
        pad = 3
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*BLANCO)
        self.set_xy(x + pad, y + pad)
        self.cell(w - pad*2, 5, "Importacion Masiva de Equipos")
        # Uploader
        self.set_fill_color(30, 35, 48)
        self.set_draw_color(70, 80, 100)
        self.rect(x + pad, y + 12, w - pad*2, 18, style="DF")
        self.set_font("Helvetica", "", 6)
        self.set_text_color(150, 160, 180)
        self.set_xy(x + pad, y + 18)
        self.cell(w - pad*2, 4, "Arrastra tu Excel o CSV aqui", align="C")
        self.set_xy(x + pad, y + 22)
        self.cell(w - pad*2, 4, "[xlsx, csv]", align="C")
        # Warning duplicados
        self.set_fill_color(255, 200, 100)
        self.rect(x + pad, y + 33, w - pad*2, 7, style="F")
        self.set_font("Helvetica", "B", 5.5)
        self.set_text_color(100, 60, 0)
        self.set_xy(x + pad + 1, y + 35)
        self.cell(w - pad*2 - 2, 3.5, "AVISO: 2 equipos ya existen y se omitiran")
        # Boton
        self.set_fill_color(*ROJO)
        mx = x + pad + (w - pad*2) * 0.25
        mw = (w - pad*2) * 0.5
        self.rect(mx, y + 43, mw, 5, style="F")
        self.set_font("Helvetica", "B", 5.5)
        self.set_text_color(*BLANCO)
        self.set_xy(mx, y + 44)
        self.cell(mw, 3.5, "Confirmar y subir 30 equipos", align="C")
        self.set_text_color(*NEGRO)
        self.set_draw_color(0, 0, 0)

    def _contenido_configurador(self, x, y, w, h):
        pad = 3
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*BLANCO)
        self.set_xy(x + pad, y + pad)
        self.cell(w - pad*2, 5, "Definicion de Grupos por Fase")
        # Selector fase
        self.set_fill_color(30, 35, 48)
        self.rect(x + pad, y + 12, w - pad*2, 5, style="F")
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(200, 210, 220)
        self.set_xy(x + pad + 2, y + 13.5)
        self.cell(w - pad*2 - 4, 3, "Fase de grupos  v")
        # Fila añadir grupos
        col_w = (w - pad*2) / 3
        labels = [("Anadir N grupos", "2"), ("Equipos por grupo", "4"), ("Accion", "Anadir")]
        for i, (lbl, val) in enumerate(labels):
            bx = x + pad + i * col_w
            self.set_fill_color(30, 35, 48)
            self.rect(bx + 1, y + 22, col_w - 2, 5, style="F")
            self.set_font("Helvetica", "", 5)
            self.set_text_color(150, 160, 180)
            self.set_xy(bx + 2, y + 23)
            self.cell(col_w - 4, 2.5, lbl)
        # Mini grupos
        self.set_font("Helvetica", "B", 5)
        self.set_text_color(170, 180, 200)
        self.set_xy(x + pad, y + 30)
        self.cell(w - pad*2, 3, "Estructura y Origen de Plazas")
        gw = (w - pad*2 - 4) / 3
        for i in range(3):
            gx = x + pad + i * (gw + 2)
            self.set_fill_color(*ROJO_OSC)
            self.rect(gx, y + 35, gw, 18, style="F")
            self.set_fill_color(*ROJO)
            self.rect(gx, y + 35, gw, 5, style="F")
            self.set_font("Helvetica", "B", 5)
            self.set_text_color(*BLANCO)
            self.set_xy(gx + 1, y + 36.5)
            self.cell(gw - 2, 3, f"GRUPO {i+1}")
            for j in range(4):
                self.set_fill_color(255, 255, 255)
                self.rect(gx + 2, y + 41 + j*2.5, gw - 4, 2, style="F")
        self.set_text_color(*NEGRO)

    def _contenido_cuadro(self, x, y, w, h):
        pad = 3
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*BLANCO)
        self.set_xy(x + pad, y + pad)
        self.cell(w - pad*2, 5, "Gestion de Equipos por Grupo")
        # Selector fase
        self.set_fill_color(30, 35, 48)
        self.rect(x + pad, y + 12, w - pad*2, 5, style="F")
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(200, 210, 220)
        self.set_xy(x + pad + 2, y + 13.5)
        self.cell(w - pad*2 - 4, 3, "Seleccionar Fase:  Fase de grupos  v")
        # Grid de grupos dark/rojo
        equipos_mock = [
            [["Real Madrid", True], ["Atletico", True], ["Getafe", True], ["Leganes", True]],
            [["Rayo", True], ["Alcorcon", True], [None, False], [None, False]],
            [["Mostoles", True], ["Alcala", True], ["Vallecas", True], [None, False]],
        ]
        gw = (w - pad*2 - 4) / 3
        for i, grupo_equipos in enumerate(equipos_mock):
            gx = x + pad + i * (gw + 2)
            gy = y + 22
            # Cabecera
            self.set_fill_color(*ROJO)
            self.rect(gx, gy, gw, 5, style="F")
            self.set_font("Helvetica", "B", 5)
            self.set_text_color(*BLANCO)
            self.set_xy(gx + 2, gy + 1)
            self.cell(gw - 10, 3.5, f"GRUPO {i+1}")
            # Boton X pequeño
            self.set_fill_color(*ROJO_OSC)
            self.rect(gx + gw - 8, gy + 0.5, 7, 4, style="F")
            self.set_font("Helvetica", "B", 4.5)
            self.set_xy(gx + gw - 8, gy + 0.8)
            self.cell(7, 3, "X", align="C")
            # Cuerpo
            self.set_fill_color(*ROJO_OSC)
            self.rect(gx, gy + 5, gw, len(grupo_equipos)*6 + 2, style="F")
            for j, (nombre, asignado) in enumerate(grupo_equipos):
                ey = gy + 6 + j*6
                if asignado and nombre:
                    self.set_fill_color(255, 255, 255)
                    self.rect(gx + 1, ey, gw - 2, 5, style="F")
                    self.set_font("Helvetica", "", 4.5)
                    self.set_text_color(40, 40, 40)
                    self.set_xy(gx + 3, ey + 0.8)
                    self.cell(gw - 14, 3.5, nombre)
                    # Boton X por equipo
                    self.set_fill_color(240, 240, 240)
                    self.rect(gx + gw - 8, ey + 0.5, 6, 4, style="F")
                    self.set_font("Helvetica", "B", 4)
                    self.set_text_color(150, 0, 0)
                    self.set_xy(gx + gw - 8, ey + 0.8)
                    self.cell(6, 3, "x", align="C")
                else:
                    self.set_draw_color(100, 0, 0)
                    self.rect(gx + 1, ey, gw - 2, 5, style="D")
                    self.set_draw_color(0, 0, 0)
        self.set_text_color(*NEGRO)

    def _contenido_sorteo(self, x, y, w, h):
        pad = 3
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*BLANCO)
        self.set_xy(x + pad, y + pad)
        self.cell(w - pad*2, 5, "Mesa de Sorteo (Fase Inicial)")
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(150, 160, 180)
        self.set_xy(x + pad, y + 9)
        self.cell(w - pad*2, 3.5, "Configurando sorteo para: Fase de grupos")
        # Contenedor
        self.set_fill_color(30, 35, 48)
        self.set_draw_color(60, 70, 90)
        self.rect(x + pad, y + 16, w - pad*2, 25, style="DF")
        col_w = (w - pad*2 - 6) / 3
        labels = ["Equipo:", "Grupo:", ""]
        vals = ["Real Madrid CF", "Grupo 1 (2 huecos)", "CONFIRMAR"]
        for i, (lbl, val) in enumerate(zip(labels, vals)):
            bx = x + pad + 2 + i * (col_w + 2)
            self.set_font("Helvetica", "", 5)
            self.set_text_color(180, 190, 210)
            self.set_xy(bx, y + 18)
            self.cell(col_w, 3, lbl)
            if i < 2:
                self.set_fill_color(20, 25, 35)
                self.rect(bx, y + 22, col_w, 5, style="F")
                self.set_font("Helvetica", "", 5)
                self.set_text_color(*BLANCO)
                self.set_xy(bx + 1, y + 23.5)
                self.cell(col_w - 2, 3, val)
            else:
                self.set_fill_color(*ROJO)
                self.rect(bx, y + 22, col_w, 5, style="F")
                self.set_font("Helvetica", "B", 5.5)
                self.set_text_color(*BLANCO)
                self.set_xy(bx, y + 23.5)
                self.cell(col_w, 2.5, "CONFIRMAR", align="C")
        # Info
        self.set_fill_color(20, 80, 20)
        self.rect(x + pad, y + 45, w - pad*2, 5, style="F")
        self.set_font("Helvetica", "", 5.5)
        self.set_text_color(200, 240, 200)
        self.set_xy(x + pad + 2, y + 46.5)
        self.cell(w - pad*2 - 4, 3, "Faltan por asignar 18 equipos")
        self.set_text_color(*NEGRO)
        self.set_draw_color(0, 0, 0)

    def mockup_tv(self, x=None, y=None, w=None, h=90):
        x = x or self.l_margin
        y = y or self.get_y()
        w = w or self.epw
        # Fondo dark red
        self.set_fill_color(14, 17, 23)
        self.rect(x, y, w, h, style="F")
        self._chrome(x, y, w, 6)
        inner_y = y + 6
        inner_h = h - 6
        self.set_fill_color(120, 0, 0)
        self.rect(x, inner_y, w, inner_h, style="F")
        # Logo + titulo
        try:
            self.image(LOGO_TV, x + w/2 - 30, inner_y + 5, 12, 12)
        except Exception:
            pass
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*BLANCO)
        self.set_xy(x, inner_y + 4)
        self.cell(w, 14, "GRUPO 1", align="C")
        # Tarjetas de equipos
        equipos_tv = ["REAL MADRID CF", "ATLETICO DE MADRID", "GETAFE CF", "CD LEGANES"]
        for i, eq in enumerate(equipos_tv):
            ey = inner_y + 22 + i * 12
            self.set_fill_color(255, 255, 255)
            self.rect(x + 20, ey, w - 40, 10, style="F")
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(26, 26, 36)
            self.set_xy(x + 30, ey + 1.5)
            self.cell(w - 60, 7, eq)
        # Navegador grupos
        btn_w = (w - 40) / 6
        for i in range(6):
            bx = x + 20 + i * (btn_w + 1)
            bg = ROJO if i == 0 else (60, 60, 60)
            self.set_fill_color(*bg)
            self.rect(bx, inner_y + inner_h - 10, btn_w, 7, style="F")
            self.set_font("Helvetica", "B", 5)
            self.set_text_color(*BLANCO)
            self.set_xy(bx, inner_y + inner_h - 9.5)
            self.cell(btn_w, 5, f"G{i+1}", align="C")
        self.set_text_color(*NEGRO)
        self.set_xy(x, y + h)
        self.ln(3)

    def tabla_datos(self, headers, filas):
        col_w = self.epw / len(headers)
        self.set_fill_color(*ROJO)
        self.set_text_color(*BLANCO)
        self.set_font("Helvetica", "B", 8.5)
        for h in headers:
            self.cell(col_w, 7, f"  {h}", fill=True, border=1)
        self.ln()
        self.set_font("Helvetica", "", 8.5)
        for i, fila in enumerate(filas):
            self.set_fill_color(245, 245, 245) if i % 2 else self.set_fill_color(255, 255, 255)
            self.set_text_color(*NEGRO)
            for celda in fila:
                self.cell(col_w, 6, f"  {celda}", fill=True, border=1)
            self.ln()
        self.ln(3)


# ════════════════════════════════════════════════════════════════════════════════
# GENERACION DEL PDF
# ════════════════════════════════════════════════════════════════════════════════

pdf = Manual(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(15, 15, 15)
pdf.set_title("Manual de Usuario - Gestor Torneo RFFM")
pdf.set_author("Real Federacion de Futbol Madrilena")


# ──────────────────────────────────────────────────────────────────────────────
# PORTADA
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()

# Fondo superior rojo
pdf.set_fill_color(*ROJO_OSC)
pdf.rect(0, 0, 210, 110, style="F")

# Logo RFFM
try:
    pdf.image(LOGO_URL, 85, 22, 40, 40)
except Exception:
    pdf.set_fill_color(*ROJO)
    pdf.rect(85, 22, 40, 40, style="F")

# Titulo principal
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(*BLANCO)
pdf.set_xy(0, 70)
pdf.cell(210, 12, "Gestor Torneo RFFM", align="C", ln=True)
pdf.set_font("Helvetica", "", 14)
pdf.set_xy(0, 82)
pdf.cell(210, 8, "Manual de Usuario", align="C", ln=True)
pdf.set_font("Helvetica", "", 10)
pdf.set_xy(0, 92)
pdf.cell(210, 6, "Aplicacion web para la gestion de campeonatos de futbol sala y 7", align="C", ln=True)

# Banda blanca central con datos
pdf.set_fill_color(*BLANCO)
pdf.rect(0, 110, 210, 150, style="F")

pdf.set_text_color(*NEGRO)
pdf.set_font("Helvetica", "B", 11)
pdf.set_xy(0, 130)
pdf.cell(210, 7, "Real Federacion de Futbol Madrilena", align="C", ln=True)
pdf.set_font("Helvetica", "", 10)
pdf.set_xy(0, 139)
pdf.cell(210, 6, f"Version 1.0   |   {date.today().strftime('%B %Y')}", align="C", ln=True)

# Tabla de contenidos resumida
pdf.set_xy(40, 160)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*ROJO_OSC)
pdf.cell(130, 7, "Contenidos", ln=True)
pdf.set_xy(40, 168)
secciones_portada = [
    "1. Introduccion y acceso al sistema",
    "2. Gestion de Torneos",
    "3. Dashboard",
    "4. Carga de Equipos",
    "5. Configurador de Fases y Grupos",
    "6. Cuadro Visual",
    "7. Mesa de Sorteo",
    "8. Vista TV",
    "9. Bracket HTML",
    "10. Preguntas frecuentes",
]
for s in secciones_portada:
    pdf.set_xy(42, pdf.get_y())
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*NEGRO)
    pdf.cell(130, 6, s, ln=True)

# Pie portada
pdf.set_fill_color(*ROJO_OSC)
pdf.rect(0, 270, 210, 27, style="F")
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*BLANCO)
pdf.set_xy(0, 278)
pdf.cell(210, 6, "Documento de uso interno - Real Federacion de Futbol Madrilena", align="C", ln=True)
pdf.set_xy(0, 284)
pdf.cell(210, 6, f"rffm.es  |  {date.today().year}", align="C")


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 1: INTRODUCCION
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("1", "Introduccion")

pdf.p(
    "El Gestor Torneo RFFM es una aplicacion web desarrollada en Python con Streamlit "
    "y conectada a una base de datos Supabase (PostgreSQL). Permite gestionar de forma "
    "integral campeonatos de futbol sala y futbol 7 organizados por la Real Federacion "
    "de Futbol Madrilena."
)

pdf.subseccion("Funcionalidades principales")
pdf.li([
    "Gestion de multiples torneos simultaneos",
    "Carga masiva de equipos desde Excel o CSV con deteccion de duplicados",
    "Configuracion de fases (grupos, cuartos, semifinal, final...)",
    "Sorteo manual de equipos en grupos con vista en tiempo real para pantalla grande",
    "Cuadro visual de grupos con asignacion y eliminacion individual de equipos",
    "Generacion de codigos QR para compartir el bracket",
    "Vista TV con refresco automatico para proyectar el sorteo en directo",
    "Bracket HTML publico (solo lectura) y de gestion (edicion)",
])

pdf.ln(2)
pdf.subseccion("Requisitos de acceso")
pdf.p(
    "La aplicacion es de acceso restringido. Es necesario disponer de usuario y "
    "contrasena proporcionados por el administrador del sistema. El acceso se realiza "
    "desde cualquier navegador web moderno (Chrome, Firefox, Edge, Safari)."
)

pdf.nota(
    "La aplicacion esta disenada para usarse en escritorio o portatil. "
    "El modo TV esta optimizado para pantallas grandes (TV o proyector)."
)

pdf.seccion("2", "Acceso al Sistema")

pdf.p(
    "Al abrir la URL de la aplicacion se muestra la pantalla de acceso. "
    "Introduce el usuario y la contrasena y pulsa 'Entrar'."
)

pdf.mockup_login()

pdf.subseccion("Cerrar sesion")
pdf.p(
    "Para cerrar la sesion, utiliza el boton 'Cerrar sesion' situado en la parte "
    "superior del panel lateral izquierdo (sidebar). Esto redirigira de nuevo a la "
    "pantalla de acceso."
)
pdf.aviso(
    "No compartas tus credenciales. El sistema registra el acceso "
    "con el usuario con el que se ha iniciado sesion."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 3: GESTION DE TORNEOS
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("3", "Gestion de Torneos")

pdf.p(
    "El menu 'Torneos' es el punto de partida. Desde aqui puedes crear nuevos torneos, "
    "consultar los existentes y acceder a sus recursos (bracket, QR, vista TV)."
)

pdf.subseccion("3.1  Crear un torneo")
pdf.li([
    "Accede al menu 'Torneos' en el panel lateral.",
    "Haz clic en el desplegable 'Crear Nuevo Torneo'.",
    "Introduce el nombre (obligatorio) y una descripcion opcional.",
    "Pulsa 'Crear torneo'. El torneo aparecera en la lista inmediatamente.",
])
pdf.ln(2)

pdf.subseccion("3.2  Recursos de cada torneo")
pdf.p(
    "Cada torneo tiene un bloque de enlaces que puedes expandir haciendo clic en el. "
    "Contiene los siguientes recursos:"
)
pdf.tabla_datos(
    ["Recurso", "Descripcion", "Acceso"],
    [
        ["Bracket dinamico", "Cuadro editable (gestion)", "bracket.html?torneo=ID"],
        ["Bracket consulta", "Cuadro solo lectura (publico)", "bracket-view.html?torneo=ID"],
        ["Vista TV", "Pantalla de sorteo en directo", "/?view=tv&grupo=G1&torneo=ID"],
        ["QR Vista publica", "Codigo QR del bracket publico", "Boton en la app"],
        ["QR Gestion", "Codigo QR del bracket de gestion", "Boton en la app"],
    ]
)

pdf.subseccion("3.3  Eliminar un torneo")
pdf.p(
    "Pulsa el icono de papelera junto al torneo. Se pedira confirmacion antes de "
    "eliminar definitivamente el torneo y todos sus datos asociados "
    "(fases, grupos, equipos y participantes)."
)
pdf.aviso(
    "La eliminacion de un torneo es IRREVERSIBLE. "
    "Asegurate de que no necesitas los datos antes de confirmar."
)

pdf.subseccion("3.4  Seleccionar el torneo activo")
pdf.p(
    "El torneo activo se selecciona en el panel lateral mediante el desplegable "
    "'Seleccionar torneo'. Todas las operaciones del resto de secciones "
    "(Dashboard, Configurador, Cuadro Visual, Sorteo) afectan al torneo activo."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 4: DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("4", "Dashboard")

pdf.p(
    "El Dashboard muestra un resumen visual del torneo activo: total de equipos, "
    "equipos en competicion y la plantilla completa con sus escudos."
)

pdf.mockup_con_sidebar("Dashboard", pdf._contenido_dashboard, h=108)

pdf.subseccion("Buscador de equipos")
pdf.p(
    "En la parte superior de la plantilla hay un campo de texto para filtrar los "
    "equipos por nombre en tiempo real. Escribe cualquier parte del nombre y la "
    "cuadricula se actualizara instantaneamente mostrando solo los equipos que coincidan."
)
pdf.nota("El filtro no distingue entre mayusculas y minusculas.")


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 5: CARGA DE EQUIPOS
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("5", "Carga de Equipos")

pdf.p(
    "Esta seccion permite importar equipos de forma masiva desde un archivo Excel "
    "(.xlsx) o CSV (.csv). Es el metodo recomendado cuando hay mas de 5 equipos que cargar."
)

pdf.subseccion("5.1  Formato del archivo")
pdf.p("El archivo debe contener exactamente las siguientes dos columnas:")
pdf.tabla_datos(
    ["Columna", "Descripcion", "Ejemplo"],
    [
        ["nombre", "Nombre completo del equipo", "Real Madrid CF"],
        ["escudo_url", "URL publica de la imagen del escudo", "https://ejemplo.com/escudo.png"],
    ]
)
pdf.nota(
    "Las URLs de los escudos deben ser publicamente accesibles. "
    "Puedes usar servicios como Imgur o el CDN de la propia federacion."
)

pdf.subseccion("5.2  Proceso de carga")
pdf.li([
    "Selecciona el torneo activo en el sidebar.",
    "Ve al menu 'Carga de Equipos'.",
    "Arrastra o selecciona el archivo Excel/CSV.",
    "Revisa la vista previa de los datos.",
    "Si hay duplicados, el sistema los detecta y avisa automaticamente.",
    "Pulsa 'Confirmar y subir' para cargar los equipos nuevos.",
])
pdf.ln(2)

pdf.mockup_con_sidebar("Carga de Equipos", pdf._contenido_carga, h=85)

pdf.subseccion("5.3  Deteccion de duplicados")
pdf.p(
    "Antes de subir, la aplicacion compara los nombres del archivo con los equipos "
    "ya existentes en el torneo (comparacion sin distincion de mayusculas). "
    "Los duplicados se omiten automaticamente y se muestra un aviso con sus nombres. "
    "Si todos los equipos son duplicados, la subida se bloquea."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 6: CONFIGURADOR
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("6", "Configurador de Fases y Grupos")

pdf.p(
    "El Configurador define la estructura del torneo: cuantas fases tiene, "
    "cuantos grupos hay en cada fase y cuantos equipos caben en cada grupo. "
    "Debe completarse antes de realizar el sorteo."
)

pdf.subseccion("6.1  Crear una fase")
pdf.li([
    "Abre el desplegable 'Crear Nueva Fase'.",
    "Escribe el nombre (ej: 'Fase de grupos', 'Cuartos de final').",
    "Asigna un orden numerico (1 para la primera fase, 2 para la segunda, etc.).",
    "Pulsa 'Guardar Fase'.",
])
pdf.ln(2)

pdf.subseccion("6.2  Crear grupos")
pdf.p(
    "Con la fase seleccionada en el desplegable, introduce el numero de grupos "
    "a crear y el numero de equipos por grupo, y pulsa 'Anadir'. "
    "Los grupos se nombran automaticamente (ej: 'Fase de grupos 1', 'Fase de grupos 2'...)."
)

pdf.mockup_con_sidebar("Configurador", pdf._contenido_configurador, h=100)

pdf.subseccion("6.3  Configurar progresion entre fases")
pdf.p(
    "Para fases con orden > 1 (cuartos, semifinal, etc.), el configurador muestra "
    "una vista de progresion donde se define de que grupo de la fase anterior "
    "proviene cada plaza. Cada plaza puede configurarse como:"
)
pdf.li([
    "'Cualquier grupo': cualquier equipo clasificado de la fase anterior.",
    "Un grupo concreto: solo el clasificado de ese grupo especifico.",
])
pdf.nota(
    "Cada grupo de la fase anterior solo puede asignarse a una plaza. "
    "El sistema bloquea asignaciones duplicadas."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 7: CUADRO VISUAL
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("7", "Cuadro Visual")

pdf.p(
    "El Cuadro Visual es la pantalla principal de gestion de equipos por grupo. "
    "Muestra todos los grupos de la fase seleccionada con sus equipos asignados "
    "y permite realizar asignaciones individuales."
)

pdf.mockup_con_sidebar("Cuadro Visual", pdf._contenido_cuadro, h=100)

pdf.subseccion("7.1  Asignar un equipo a un grupo")
pdf.li([
    "Selecciona la fase en el desplegable superior.",
    "Localiza el grupo donde quieres asignar el equipo.",
    "Si el grupo tiene huecos libres, aparece un desplegable con los equipos disponibles.",
    "Selecciona el equipo en el desplegable. La asignacion se guarda automaticamente.",
])
pdf.ln(2)

pdf.subseccion("7.2  Quitar un equipo individual")
pdf.p(
    "Cada equipo asignado muestra un boton 'x' a su derecha. Al pulsarlo, "
    "el equipo se libera del grupo y vuelve a estar disponible en el pool "
    "de equipos sin asignar."
)

pdf.subseccion("7.3  Vaciar un grupo completo")
pdf.p(
    "Cuando un grupo esta completo aparece el boton 'Vaciar grupo'. "
    "Al pulsarlo se solicita confirmacion antes de liberar todos los equipos del grupo."
)

pdf.subseccion("7.4  Fase de progresion")
pdf.p(
    "Para fases de orden > 1, el Cuadro Visual muestra la vista de progresion "
    "con los grupos de la fase anterior (izquierda) y los destino (derecha), "
    "permitiendo asignar equipos clasificados segun la configuracion definida."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 8: SORTEO
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("8", "Mesa de Sorteo")

pdf.p(
    "La Mesa de Sorteo esta disenada para realizar el sorteo de la fase inicial "
    "de forma manual, equipo a equipo, en un acto publico. Permite seleccionar "
    "el equipo (bola) y el grupo de destino y confirmar la asignacion."
)

pdf.mockup_con_sidebar("Sorteo", pdf._contenido_sorteo, h=90)

pdf.subseccion("Flujo de uso")
pdf.li([
    "Asegurate de tener la Fase de grupos configurada (fases con orden 1).",
    "Accede al menu 'Sorteo'.",
    "En el desplegable izquierdo selecciona el equipo que se acaba de sortear.",
    "En el desplegable central selecciona el grupo asignado.",
    "Pulsa 'Confirmar'. Aparece un aviso emergente con la asignacion.",
    "El equipo desaparece del pool y el contador de pendientes se actualiza.",
    "Repite hasta que todos los equipos esten asignados.",
])
pdf.ln(2)
pdf.nota(
    "El sorteo busca primero si existe una plaza vacia en el grupo (para respetar "
    "la configuracion del Configurador) antes de insertar una nueva fila. "
    "Esto garantiza coherencia con el Cuadro Visual."
)
pdf.aviso(
    "El Sorteo solo funciona con la fase de orden 1. Para fases posteriores, "
    "usa el Cuadro Visual con la vista de progresion."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 9: VISTA TV
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("9", "Vista TV")

pdf.p(
    "La Vista TV esta optimizada para proyectarse en una pantalla grande o TV "
    "durante el acto de sorteo. Muestra el grupo actual con los equipos asignados "
    "y se actualiza automaticamente cada 3 segundos."
)

pdf.mockup_tv()

pdf.subseccion("Como acceder")
pdf.p(
    "La URL de la Vista TV se genera automaticamente en la seccion Torneos. "
    "Tiene el formato:"
)
pdf.set_x(pdf.l_margin)
pdf.set_fill_color(30, 30, 30)
pdf.set_text_color(200, 255, 150)
pdf.set_font("Courier", "", 8.5)
pdf.multi_cell(pdf.epw, 6, "  /?view=tv&grupo=Fase de grupos 1&torneo=UUID-DEL-TORNEO", fill=True)
pdf.set_text_color(*NEGRO)
pdf.set_font("Helvetica", "", 9.5)
pdf.ln(3)

pdf.subseccion("Navegacion entre grupos")
pdf.p(
    "En la parte inferior de la pantalla aparecen botones de navegacion (G1, G2, G3...) "
    "para cambiar el grupo visible sin salir de la vista TV. "
    "El boton del grupo actual aparece en rojo."
)
pdf.subseccion("Refresco automatico")
pdf.p(
    "La pantalla se actualiza automaticamente cada 3 segundos. "
    "Cuando se asigna un equipo en el sorteo, aparecera en la Vista TV "
    "en el siguiente ciclo de refresco sin necesidad de recargar manualmente."
)
pdf.nota(
    "Abre la Vista TV en el navegador del ordenador conectado a la pantalla/TV "
    "y pon ese navegador en pantalla completa (F11). "
    "Usa otro dispositivo (tablet o movil) para operar el Sorteo."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 10: BRACKET HTML
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("10", "Bracket HTML")

pdf.p(
    "El proyecto incluye dos archivos HTML en la carpeta public/ para visualizar "
    "el cuadro eliminatorio del torneo de forma grafica:"
)
pdf.tabla_datos(
    ["Archivo", "Descripcion", "Acceso"],
    [
        ["bracket.html", "Version de gestion (editable)", "bracket.html?torneo=ID"],
        ["bracket-view.html", "Version publica (solo lectura)", "bracket-view.html?torneo=ID"],
    ]
)

pdf.p(
    "Ambas versiones se conectan a Supabase para mostrar los datos en tiempo real. "
    "La version de gestion permite mover equipos entre el bracket, "
    "mientras que la version publica es apta para compartir con jugadores o aficionados."
)
pdf.nota(
    "El ID del torneo se encuentra en la seccion Torneos de la aplicacion, "
    "en el bloque de 'Enlaces' de cada torneo."
)


# ──────────────────────────────────────────────────────────────────────────────
# SECCION 11: PREGUNTAS FRECUENTES
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.seccion("11", "Preguntas Frecuentes")

faqs = [
    (
        "No puedo entrar a la aplicacion. Que hago?",
        "Verifica que el usuario y la contrasena son correctos. "
        "Si el problema persiste, contacta al administrador del sistema para "
        "restablecer las credenciales."
    ),
    (
        "Puedo tener varios torneos activos a la vez?",
        "Si. La aplicacion soporta multiples torneos simultaneos. "
        "Selecciona el torneo activo en el desplegable del sidebar antes de "
        "realizar cualquier operacion."
    ),
    (
        "Como elimino un equipo que ya esta en un grupo?",
        "En el Cuadro Visual, cada equipo asignado tiene un boton 'x' a su derecha. "
        "Pulsalo para liberarlo del grupo sin afectar al resto de equipos."
    ),
    (
        "El archivo Excel da error al subir. Por que?",
        "Asegurate de que el archivo tiene exactamente las columnas 'nombre' y "
        "'escudo_url' (en minusculas, sin espacios). Si el archivo tiene columnas "
        "adicionales, no hay problema; solo se usaran esas dos."
    ),
    (
        "Como comparto el cuadro con los equipos participantes?",
        "Usa la URL del Bracket de consulta (bracket-view.html?torneo=ID) "
        "o genera el codigo QR desde la seccion Torneos. "
        "Esta version es de solo lectura y no requiere autenticacion."
    ),
    (
        "La Vista TV no se actualiza. Que ocurre?",
        "Comprueba que el navegador tiene conexion a internet y que la URL "
        "incluye los parametros correctos (view=tv, grupo y torneo). "
        "Si la pagina muestra un error, recarga manualmente."
    ),
    (
        "Puedo usar la aplicacion en el movil?",
        "Si, pero el diseno esta optimizado para escritorio. "
        "En movil, el sidebar se colapsa y puede ser necesario hacer scroll. "
        "La Vista TV funciona bien en cualquier tamano de pantalla."
    ),
    (
        "Como configuro el sorteo para que respete el Configurador?",
        "El Sorteo detecta automaticamente la fase de orden 1 del torneo activo. "
        "Asegurate de que tienes creada al menos una fase con orden=1 y sus grupos "
        "antes de acceder a la Mesa de Sorteo."
    ),
]

for i, (pregunta, respuesta) in enumerate(faqs):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*ROJO_OSC)
    pdf.multi_cell(pdf.epw, 6, f"P{i+1}.  {pregunta}")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*NEGRO)
    pdf.multi_cell(pdf.epw, 5.5, f"     {respuesta}")
    pdf.ln(3)


# ──────────────────────────────────────────────────────────────────────────────
# ULTIMA PAGINA: CONTACTO / VERSION
# ──────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.set_fill_color(*ROJO_OSC)
pdf.rect(0, 80, 210, 137, style="F")

pdf.set_xy(0, 100)
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(*BLANCO)
pdf.cell(210, 10, "Contacto y Soporte", align="C", ln=True)

pdf.set_font("Helvetica", "", 10)
pdf.set_xy(0, 118)
pdf.cell(210, 7, "Real Federacion de Futbol Madrilena", align="C", ln=True)
pdf.set_xy(0, 126)
pdf.cell(210, 7, "rffm.es", align="C", ln=True)

pdf.set_font("Helvetica", "I", 9)
pdf.set_text_color(200, 200, 200)
pdf.set_xy(0, 155)
pdf.cell(210, 6, f"Manual de Usuario  |  Version 1.0  |  {date.today().strftime('%B %Y')}", align="C", ln=True)
pdf.set_xy(0, 162)
pdf.cell(210, 6, "Generado automaticamente por el sistema Gestor Torneo RFFM", align="C")


# ──────────────────────────────────────────────────────────────────────────────
# GUARDAR
# ──────────────────────────────────────────────────────────────────────────────
output_path = "Manual_Gestor_Torneo_RFFM.pdf"
pdf.output(output_path)
print(f"PDF generado: {output_path}  ({pdf.page} paginas)")
