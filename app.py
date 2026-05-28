import base64
import io
import re as _re
import urllib.parse
import datetime
from collections import defaultdict
from typing import Any

import streamlit as st
import pandas as pd

from src.database import (
    get_supabase,
    get_torneos,
    crear_torneo,
    eliminar_torneo,
    get_equipos,
    get_equipos_libres,
    subir_equipos_batch,
    update_equipo,
    patch_equipo,
    get_fases,
    get_grupos_por_fase,
    get_participantes_grupo,
    get_participantes_grupos,
    crear_fase,
    crear_grupos,
    contar_grupos_fase,
    actualizar_grupo,
    eliminar_grupo,
    actualizar_num_vueltas,
    actualizar_duracion_fase,
    set_fase_oculta_bracket,
    hay_partidos_fase,
    eliminar_partidos_fase,
    generar_partidos_fase,
    get_partidos_fase,
    actualizar_partidos_batch,
    eliminar_partido,
    subir_escudo,
    set_visible_bracket,
    set_orden_menu,
    sincronizar_equipos_partidos_fase,
    get_campos_distintos,
    get_partidos_agenda,
    get_grupos_pdf_data,
)
from src.logic import seccion_sorteo_manual
from src.components import (
    renderizar_tarjetas_equipos,
    mostrar_grupo_tv,
    configurar_progresion_visual,
    renderizar_tarjeta_grupo_minimalista,
    renderizar_cuadro_progresion,
    torneo_card_color,
)


# ── QR helper ──────────────────────────────────────────
def generar_qr(url: str, output_size: int | None = None):
    import qrcode
    from PIL import Image
    import urllib.request as _urlreq

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # type: ignore[attr-defined]
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="white").convert("RGBA")  # type: ignore[union-attr]

    # Incrustar el escudo RFFM centrado
    try:
        with _urlreq.urlopen(LOGO_RFFM_URL, timeout=5) as resp:
            logo = Image.open(io.BytesIO(resp.read())).convert("RGBA")
        qr_w, qr_h = img.size
        logo_size = qr_w // 4  # ocupa el 25% del ancho del QR
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)  # type: ignore[attr-defined]
        # Fondo blanco con margen alrededor del logo
        pad = 6
        bg = Image.new("RGBA", (logo_size + pad * 2, logo_size + pad * 2), (255, 255, 255, 255))
        bg_pos = ((qr_w - bg.width) // 2, (qr_h - bg.height) // 2)
        img.paste(bg, bg_pos)
        logo_pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        img.paste(logo, logo_pos, logo)
    except Exception:
        pass  # si falla la descarga el QR sigue siendo válido

    if output_size:
        img = img.resize((output_size, output_size), Image.LANCZOS)  # type: ignore[attr-defined]

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- Constantes ---
LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"

# --- Configuración de página (solo una vez) ---
st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

# CSS global — tema corporativo RFFM
st.markdown("""
<style>

/* ── Botones primarios — rojo RFFM ──────────────────────────────────────── */
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background-color: #cc0000 !important;
    color: white !important;
    border: none !important;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background-color: #a00000 !important;
    color: white !important;
}

/* ── Sidebar — texto blanco solo en elementos de texto, no en portales ─── */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"],
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-value],
section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    color: white !important;
    fill: white !important;
}

/* Inputs del sidebar */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    border-color: rgba(255,255,255,0.4) !important;
    background-color: rgba(255,255,255,0.1) !important;
    color: white !important;
}
section[data-testid="stSidebar"] input::placeholder {
    color: rgba(255,255,255,0.5) !important;
}

/* Hover en botones del sidebar (no botones primarios) */
section[data-testid="stSidebar"] button:not([kind="primary"]):hover {
    background-color: #a00000 !important;
    border-radius: 4px;
}

/* Separadores y expanders del sidebar */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.25) !important;
}
section[data-testid="stSidebar"] details summary:hover {
    background-color: #a00000 !important;
    border-radius: 4px;
}

/* ── Dropdowns / selectbox — asegurar colores correctos en los popups ────── */
/* Popup de opciones (se renderiza fuera del sidebar, en el body) */
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] [role="option"] {
    color: #1a1a1a !important;
    background-color: white !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="menu"] [role="option"]:hover {
    background-color: #f5e6e6 !important;
    color: #1a1a1a !important;
}
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="menu"] [role="option"][aria-selected="true"] {
    background-color: #cc0000 !important;
    color: white !important;
}

/* ── Focus — solo quitar el cyan en inputs, no en listas ────────────────── */
input:focus, textarea:focus {
    outline: none !important;
    box-shadow: none !important;
}
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: #cc0000 !important;
    box-shadow: none !important;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# AUTENTICACIÓN
# -------------------------------------------------------
def check_login():
    """Muestra pantalla de login y devuelve True si autenticado."""
    if st.session_state.get("authenticated"):
        return True

    # CSS específico para el login
    st.markdown("""
    <style>
    /* Botón Entrar — rojo RFFM */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #cc0000 !important;
        color: white !important;
        border: none !important;
    }
    div[data-testid="stForm"] button:hover {
        background-color: #a00000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:24px;">
                <img src="{LOGO_RFFM_URL}" style="width:80px;margin-bottom:12px;">
                <h2 style="margin:0;font-size:1.5rem;text-align:center;color:#1a1a1a;">Gestión de Campeonato RFFM</h2>
                <p style="color:#666666;margin:0;font-size:0.9rem;">Acceso restringido</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", width='stretch', type="primary")

            if submitted:
                valid_user = st.secrets.get("auth", {}).get("username", "")
                valid_pass = st.secrets.get("auth", {}).get("password", "")
                if usuario == valid_user and password == valid_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

    return False

if not check_login():
    st.stop()

# --- Cliente Supabase único ---
supabase = get_supabase()

# -------------------------------------------------------
# HELPERS
# -------------------------------------------------------
def _sort_grupos(grupos):
    """Ordena grupos por orden_cuadro (si está definido) y luego por número en el nombre."""
    def _key(g):
        m = _re.search(r"\d+", g["nombre"])
        num = int(m.group()) if m else 0
        orden = g.get("orden_cuadro")
        return (orden if orden is not None else float("inf"), num)
    return sorted(grupos, key=_key)

# -------------------------------------------------------
# MODO TV
# -------------------------------------------------------
query_params = st.query_params

if "view" in query_params and query_params["view"] == "tv":
    grupo_id_url = query_params.get("grupo")
    torneo_id_tv = query_params.get("torneo")

    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            /* Fondo rojo RFFM en todos los contenedores del modo TV */
            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            [data-testid="stMainBlockContainer"],
            section.main, .main,
            .block-container {
                background-color: #8b0000 !important;
                color: white !important;
            }
            /* Eliminar padding excesivo */
            [data-testid="stMainBlockContainer"] {
                padding-top: 2rem !important;
                max-width: 100% !important;
            }
            /* Botones de navegación de grupos */
            section[data-testid="stMain"] button[kind="secondary"] {
                background-color: rgba(255,255,255,0.15) !important;
                color: white !important;
                border: 1px solid rgba(255,255,255,0.3) !important;
            }
            section[data-testid="stMain"] button[kind="secondary"]:hover {
                background-color: rgba(255,255,255,0.25) !important;
            }
            section[data-testid="stMain"] button[kind="primary"] {
                background-color: white !important;
                color: #8b0000 !important;
            }
            /* Ocultar header de Streamlit */
            [data-testid="stHeader"] { display: none !important; }
            hr { border-color: rgba(255,255,255,0.2) !important; }
        </style>
    """, unsafe_allow_html=True)

    # ── QR Bracket Vista (esquina superior derecha, fijo) ─────────────────────
    if torneo_id_tv:
        try:
            _url_vista_tv = f"https://www.rffm.es/actualidad/futbol-7/torneo-campeones-2026?torneo={torneo_id_tv}"
            _qr_buf = generar_qr(_url_vista_tv)
            _qr_b64 = base64.b64encode(_qr_buf.getvalue()).decode()
            st.markdown(f"""
                <div style="position: fixed; top: 1rem; right: 1rem; z-index: 9999;
                            background: white; border-radius: 8px; padding: 6px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.4);">
                    <img src="data:image/png;base64,{_qr_b64}"
                         style="width: 140px; height: 140px; display: block;">
                    <div style="text-align: center; font-size: 11px; color: #333;
                                margin-top: 4px; font-family: sans-serif;
                                font-weight: bold; max-width: 140px;">
                        Consulta el cuadro del torneo
                    </div>
                </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

    if grupo_id_url:
        mostrar_grupo_tv(grupo_id_url, torneo_id=torneo_id_tv)
    else:
        st.warning("⚠️ No se ha especificado ningún ID de grupo en la URL.")

    st.stop()

# -------------------------------------------------------
# CABECERA
# -------------------------------------------------------
st.markdown(
    f"""
    <div style="display: flex; align-items: center;">
        <img src="{LOGO_RFFM_URL}" style="width: 50px; margin-right: 15px;">
        <h1 style="margin: 0;">Gestión de Campeonato RFFM</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------
# SELECTOR DE TORNEO (sidebar)
# -------------------------------------------------------
if st.sidebar.button("🔒 Cerrar sesión", width='stretch'):
    st.session_state.authenticated = False
    st.rerun()

_URL_CUADRO = "https://www.rffm.es/actualidad/futbol-7/torneo-campeones-2026"

if st.sidebar.button("📅 Agenda Global", width='stretch'):
    st.session_state["view"] = "agenda_global"

st.sidebar.markdown("---")
st.sidebar.markdown("## Torneo")

torneos = get_torneos()

if not torneos:
    st.sidebar.info("No hay torneos. Crea uno primero.")
    torneo_actual = None
else:
    nombres_torneos = [t["nombre"] for t in torneos]

    if "torneo_idx" not in st.session_state:
        st.session_state.torneo_idx = 0

    # Clampear por si se borró el torneo seleccionado
    st.session_state.torneo_idx = min(st.session_state.torneo_idx, len(nombres_torneos) - 1)

    torneo_sel = st.sidebar.selectbox(
        "Seleccionar torneo",
        nombres_torneos,
        index=st.session_state.torneo_idx,
        key="torneo_selector",
        on_change=lambda: st.session_state.pop("view", None),
    )
    st.session_state.torneo_idx = nombres_torneos.index(torneo_sel)
    torneo_actual: dict[str, Any] | None = next((t for t in torneos if t["nombre"] == torneo_sel), None)

    if torneo_actual:
        _bg, _border = torneo_card_color(torneo_actual["id"])
        st.sidebar.markdown(
            f'<div style="background:{_bg};border:1.5px solid {_border};border-radius:8px;'
            f'padding:6px 12px;font-size:0.8rem;font-weight:600;color:#1a1c24;'
            f'text-align:center;margin-bottom:4px;">'
            f'🏟️ {torneo_actual["nombre"]}</div>',
            unsafe_allow_html=True,
        )

with st.sidebar.expander("➕ Nuevo torneo"):
    nuevo_nombre = st.text_input("Nombre", placeholder="ej: Copa RFFM 2026", key="sb_nuevo_nombre")
    nueva_desc   = st.text_input("Descripción (opcional)", key="sb_nueva_desc")
    if st.button("Crear", width='stretch', key="sb_crear_torneo"):
        if nuevo_nombre.strip():
            try:
                crear_torneo(nuevo_nombre.strip(), nueva_desc.strip())
                st.success(f"Torneo '{nuevo_nombre}' creado.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("El nombre no puede estar vacío.")

st.sidebar.markdown("---")

# -------------------------------------------------------
# NAVEGACIÓN
# -------------------------------------------------------
menu = st.sidebar.selectbox(
    "Menú",
    ["Dashboard", "Configurador", "Cuadro Visual", "Partidos", "Sorteo", "Ajustes"],
    on_change=lambda: st.session_state.pop("view", None),
)

# -------------------------------------------------------
# AGENDA: diálogo de edición de horario
# -------------------------------------------------------
# DASHBOARD GLOBAL — Agenda (no requiere torneo)
# -------------------------------------------------------
if st.session_state.get("view") == "agenda_global":
    _ag_col_title, _ag_col_qr = st.columns([4, 1])
    _ag_col_title.subheader("📅 Agenda Global de Partidos")

    with _ag_col_qr:
        with st.expander("QR Cuadro Visual"):
            try:
                _qr_buf = generar_qr(_URL_CUADRO)
                st.image(_qr_buf, width='stretch')
                _qr_buf.seek(0)
                st.download_button(
                    "⬇️ Descargar QR",
                    data=_qr_buf,
                    file_name="qr_cuadro_rffm.png",
                    mime="image/png",
                    width='stretch',
                    key="dl_qr_global",
                )
                _qr_hd = generar_qr(_URL_CUADRO, output_size=1080)
                st.download_button(
                    "⬇️ Descargar QR 1080×1080",
                    data=_qr_hd,
                    file_name="qr_cuadro_rffm_1080.png",
                    mime="image/png",
                    width='stretch',
                    key="dl_qr_global_hd",
                )
            except Exception:
                pass

    if st.sidebar.button("← Volver", width='stretch', key="back_agenda"):
        st.session_state.pop("view", None)
        st.rerun()

    _ag_todos_torneos = get_torneos()
    _ag_todos_campos  = get_campos_distintos()

    _ag_hoy = datetime.date.today()
    _ag_r1c1, _ag_r1c2, _ag_r1c3, _ag_r1c4 = st.columns([1, 1, 1, 1])
    _ag_fecha_desde = _ag_r1c1.date_input("Desde", value=_ag_hoy, format="DD/MM/YYYY", key="gag_desde")
    _ag_fecha_hasta = _ag_r1c2.date_input("Hasta", value=_ag_hoy, format="DD/MM/YYYY", key="gag_hasta")
    _ag_hora_ini    = _ag_r1c3.time_input("Hora inicio (vacío = auto)", value=None, key="gag_hora_ini", step=1800)
    _ag_hora_fin    = _ag_r1c4.time_input("Hora fin (vacío = auto)",   value=None, key="gag_hora_fin", step=1800)

    _ag_r2c1, _ag_r2c2 = st.columns([2, 2])
    _ag_campos_sel  = _ag_r2c1.multiselect("Campo(s)",   options=_ag_todos_campos, placeholder="Todos los campos", key="gag_campos")
    _ag_torneos_sel = _ag_r2c2.multiselect("Torneo(s)",  options=[t["nombre"] for t in _ag_todos_torneos], placeholder="Todos los torneos", key="gag_torneos")

    _ag_torneo_ids = [t["id"] for t in _ag_todos_torneos if t["nombre"] in _ag_torneos_sel] if _ag_torneos_sel else None
    _ag_campos_ids = _ag_campos_sel if _ag_campos_sel else None

    _ag_partidos = get_partidos_agenda(
        fecha_desde=_ag_fecha_desde,
        fecha_hasta=_ag_fecha_hasta,
        campos=_ag_campos_ids,
        torneo_ids=_ag_torneo_ids,
    )
    # Guardamos en session_state para que el diálogo pueda encontrar el partido por id
    st.session_state.ag_partidos_cache = _ag_partidos

    # ── Rango horario efectivo ────────────────────────────
    # 0    = sin suelo: cada día arranca en su primer partido
    # 1440 = sin tope:  cada día termina en su último partido
    _ag_ini_min_eff = _ag_hora_ini.hour * 60 + _ag_hora_ini.minute if _ag_hora_ini is not None else 0
    _ag_fin_min_eff = _ag_hora_fin.hour * 60 + _ag_hora_fin.minute if _ag_hora_fin is not None else 0

    # ── Downloads ─────────────────────────────────────────
    st.markdown("---")
    _ag_dc1, _ag_dc2, _ag_dc3 = st.columns([1, 1, 1])

    with _ag_dc1:
        if st.button("📄 PDF Agenda por campo", width='stretch', type="primary"):
            if not _ag_partidos:
                st.warning("No hay partidos con los filtros seleccionados.")
            else:
                with st.spinner("Generando PDF…"):
                    from src.pdf.agenda import generar_pdf_agenda
                    _rango = ""
                    if _ag_fecha_desde and _ag_fecha_hasta:
                        _rango = f" · {_ag_fecha_desde.strftime('%d/%m/%Y')} – {_ag_fecha_hasta.strftime('%d/%m/%Y')}"
                    _pdf = generar_pdf_agenda(_ag_partidos, "Agenda de partidos" + _rango)
                st.download_button("⬇️ Descargar PDF", data=_pdf, file_name="agenda_partidos.pdf",
                                   mime="application/pdf", key="dl_gag_pdf")

    with _ag_dc2:
        if st.button("📊 PDF Rejilla horaria", width='stretch', type="primary"):
            if not _ag_partidos:
                st.warning("No hay partidos con los filtros seleccionados.")
            else:
                with st.spinner("Generando PDF rejilla…"):
                    from src.pdf.agenda_grid import generar_pdf_agenda_grid
                    _ini_min_dl = _ag_ini_min_eff
                    _fin_min_dl = _ag_fin_min_eff
                    _rango = ""
                    if _ag_fecha_desde and _ag_fecha_hasta:
                        _rango = f" · {_ag_fecha_desde.strftime('%d/%m/%Y')} – {_ag_fecha_hasta.strftime('%d/%m/%Y')}"
                    _pdf_grid = generar_pdf_agenda_grid(
                        _ag_partidos, "Agenda de partidos" + _rango,
                        hora_ini_min=_ini_min_dl, hora_fin_min=_fin_min_dl,
                    )
                st.download_button("⬇️ Descargar PDF", data=_pdf_grid, file_name="agenda_rejilla.pdf",
                                   mime="application/pdf", key="dl_gag_grid")

    with _ag_dc3:
        if st.button("📋 Excel Rejilla horaria", width='stretch', type="primary"):
            if not _ag_partidos:
                st.warning("No hay partidos con los filtros seleccionados.")
            else:
                with st.spinner("Generando Excel…"):
                    from src.excel_agenda import generar_excel_agenda
                    _ini_min_dl = _ag_ini_min_eff
                    _fin_min_dl = _ag_fin_min_eff
                    _ag_color_map = {
                        t["id"]: torneo_card_color(t["id"]) for t in _ag_todos_torneos
                    }
                    _xlsx = generar_excel_agenda(
                        _ag_partidos, "Agenda de partidos",
                        hora_ini_min=_ini_min_dl, hora_fin_min=_fin_min_dl,
                        color_map=_ag_color_map,
                    )
                st.download_button("⬇️ Descargar Excel", data=_xlsx,
                                   file_name="agenda_rejilla.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="dl_gag_xlsx")

    if not _ag_partidos:
        st.info("No hay partidos programados para los filtros seleccionados.")
        st.stop()

    # ── Helpers para vista de rejilla temporal ────────────
    _PX_MIN   = 3    # píxeles por minuto
    _AXIS_W   = 52   # px del eje de horas
    _CAMPO_W  = 290  # px de ancho fijo por campo (scroll a partir de 3)
    _HDR_H    = 28   # px de altura fija del header de campo
    _SHIELD   = 32   # px de tamaño de escudo
    _RFFM_LOGO_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"

    def _hm_to_min(t) -> int:
        try:
            parts = str(t)[:5].split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return 0

    def _min_to_hm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    def _dia_ini(campos_dia: dict) -> int:
        """Calcula el ini_min de un día a partir del primer partido, redondeado a 30 min."""
        ini = 23 * 60
        for _campo_ps in campos_dia.values():
            for _p in _campo_ps:
                _h = str(_p.get("hora") or "")[:5]
                if len(_h) == 5 and ":" in _h:
                    try:
                        _pm = int(_h[:2]) * 60 + int(_h[3:])
                        if _pm > 0:
                            ini = min(ini, _pm)
                    except Exception:
                        pass
        if ini >= 23 * 60:
            ini = _ag_ini_min_eff or (8 * 60)
        ini = (ini // 30) * 30  # redondear hacia abajo a 30 min
        if _ag_hora_ini is not None:
            ini = min(ini, _ag_ini_min_eff)
        return ini

    def _dia_fin_min(campos_dia: dict, ini_min: int) -> int:
        """Calcula el fin_min de un día a partir de sus partidos, redondeado a 30 min."""
        fin = ini_min + 60
        for _campo_ps in campos_dia.values():
            for _p in _campo_ps:
                _h = str(_p.get("hora") or "")[:5]
                if len(_h) == 5 and ":" in _h:
                    try:
                        _pm = int(_h[:2]) * 60 + int(_h[3:])
                        fin = max(fin, _pm + (_p.get("duracion_partido") or 50))
                    except Exception:
                        pass
        return (fin + 29) // 30 * 30

    def _axis_inner(ini_min: int, fin_min: int) -> str:
        html = ""
        _h = ((ini_min + 59) // 60) * 60
        while _h <= fin_min:
            _top = (_h - ini_min) * _PX_MIN - 7
            html += (f'<div style="position:absolute;top:{_top}px;right:6px;'
                     f'font-size:0.65rem;color:#888;white-space:nowrap;">{_min_to_hm(_h)}</div>')
            _h += 60
        return html

    def _campo_inner(partidos_campo: list, color_cache: dict, ini_min: int, fin_min: int) -> str:
        html = ""
        total_h = (fin_min - ini_min) * _PX_MIN
        # Líneas de hora completa
        _h = ((ini_min + 59) // 60) * 60
        while _h <= fin_min:
            _top = (_h - ini_min) * _PX_MIN
            html += (f'<div style="position:absolute;top:{_top}px;left:0;right:0;'
                     f'height:1px;background:#bbb;z-index:1;"></div>')
            _h += 60
        # Líneas de media hora discontinuas
        _h = ((ini_min + 59) // 60) * 60 + 30
        while _h < fin_min:
            _top = (_h - ini_min) * _PX_MIN
            html += (f'<div style="position:absolute;top:{_top}px;left:0;right:0;'
                     f'height:1px;border-top:1px dashed #ccc;z-index:1;"></div>')
            _h += 60
        # Partidos
        for _p in partidos_campo:
            try:
                _sm = _hm_to_min(str(_p.get("hora") or "")[:5])
            except Exception:
                continue
            _dur = _p.get("duracion_partido") or 30
            _em  = _sm + _dur
            if _sm >= fin_min or _em <= ini_min:
                continue
            _top = (max(_sm, ini_min) - ini_min) * _PX_MIN
            _hb  = (min(_em, fin_min) - max(_sm, ini_min)) * _PX_MIN - 2
            _tid = _p.get("torneo_id") or ""
            _cbg, _cborder = color_cache.get(_tid, ("#ffffff", "#d0d0d0"))
            _loc = _p.get("nombre_local") or "–"
            _vis = _p.get("nombre_visitante") or "–"
            _tor = _p.get("nombre_torneo") or ""
            _grp = _p.get("nombre_grupo") or ""
            _rl, _rv = _p.get("resultado_local"), _p.get("resultado_visitante")
            _marc_str = f"{_rl}–{_rv}" if _rl is not None and _rv is not None else ""
            _marc_html = (f'<div style="font-size:0.63rem;font-weight:700;color:#cc0000;text-align:center;">{_marc_str}</div>'
                          if _marc_str else "")
            _grp_tor = " · ".join(filter(None, [_grp, _tor]))
            _esc_l = _p.get("escudo_local") or _RFFM_LOGO_URL
            _esc_v = _p.get("escudo_visitante") or _RFFM_LOGO_URL
            _card_base = (f'position:absolute;top:{_top}px;left:2px;right:2px;height:{_hb}px;'
                          f'background-color:{_cbg};border-left:3px solid {_cborder};border-radius:3px;'
                          f'overflow:hidden;z-index:2;box-sizing:border-box;')

            if _hb >= 48:
                # Layout completo: grupo·torneo arriba, escudos a los lados, equipos centrados
                html += (
                    f'<div style="{_card_base}display:flex;flex-direction:column;'
                    f'align-items:center;justify-content:center;padding:2px 3px;gap:1px;">'
                    f'<div style="font-size:0.58rem;color:#555;text-align:center;width:100%;'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_grp_tor}</div>'
                    f'<div style="display:flex;align-items:center;width:100%;gap:2px;">'
                    f'<img src="{_esc_l}" width="{_SHIELD}" height="{_SHIELD}" '
                    f'style="object-fit:contain;flex-shrink:0;border-radius:3px;" '
                    f'onerror="this.src=\'{_RFFM_LOGO_URL}\'">'
                    f'<div style="flex:1;text-align:center;min-width:0;overflow:hidden;">'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_loc}</div>'
                    f'<div style="font-size:0.55rem;color:#888;font-style:italic;">vs</div>'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#1a1a1a;'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_vis}</div>'
                    f'</div>'
                    f'<img src="{_esc_v}" width="{_SHIELD}" height="{_SHIELD}" '
                    f'style="object-fit:contain;flex-shrink:0;border-radius:3px;" '
                    f'onerror="this.src=\'{_RFFM_LOGO_URL}\'">'
                    f'</div>'
                    f'{_marc_html}'
                    f'</div>'
                )
            elif _hb >= 24:
                # Dos líneas: grupo·torneo / local – visitante
                html += (
                    f'<div style="{_card_base}padding:2px 4px;">'
                    f'<div style="font-size:0.58rem;color:#555;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis;">{_grp_tor}</div>'
                    f'<div style="font-size:0.63rem;font-weight:700;color:#1a1a1a;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_loc} – {_vis}</div>'
                    f'{_marc_html}'
                    f'</div>'
                )
            else:
                # Una sola línea compacta
                html += (
                    f'<div style="{_card_base}padding:1px 4px;display:flex;align-items:center;">'
                    f'<div style="font-size:0.6rem;font-weight:700;color:#1a1a1a;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_loc} – {_vis}</div>'
                    f'</div>'
                )
        return html

    def _dia_grid_html(campos_dia: dict, campo_list: list, color_cache: dict, ini_min: int, fin_min: int) -> str:
        n = len(campo_list)
        total_h = (fin_min - ini_min) * _PX_MIN
        total_w  = _AXIS_W + n * _CAMPO_W

        # ── Fila 1: espacio vacío bajo el eje + headers de campos ─────────────
        # El eje no tiene header; los campos sí. Se separa en dos filas flex
        # para que el eje de horas y los grids compartan el mismo origen Y.
        hdr_spacer = f'<div style="width:{_AXIS_W}px;flex-shrink:0;"></div>'
        hdr_cols = ""
        for _campo_n in campo_list:
            hdr_cols += (
                f'<div style="width:{_CAMPO_W}px;flex-shrink:0;padding-right:6px;">'
                f'<div style="background:#1A3A5F;color:white;font-weight:700;font-size:0.8rem;'
                f'height:{_HDR_H}px;line-height:{_HDR_H}px;'
                f'border-radius:6px 6px 0 0;padding:0 8px;white-space:nowrap;'
                f'overflow:hidden;text-overflow:ellipsis;">📍 {_campo_n}</div>'
                f'</div>'
            )

        # ── Fila 2: eje de horas + grids de partidos ──────────────────────────
        axis_col = (
            f'<div style="width:{_AXIS_W}px;flex-shrink:0;position:relative;'
            f'height:{total_h}px;border-right:1px solid #ccc;">'
            f'{_axis_inner(ini_min, fin_min)}</div>'
        )
        grid_cols = ""
        for _campo_n in campo_list:
            grid_cols += (
                f'<div style="width:{_CAMPO_W}px;flex-shrink:0;padding-right:6px;">'
                f'<div style="position:relative;height:{total_h}px;background:#e4e4e4;'
                f'border-radius:0 0 4px 4px;overflow:hidden;border:1px solid #ccc;">'
                f'{_campo_inner(campos_dia[_campo_n], color_cache, ini_min, fin_min)}</div>'
                f'</div>'
            )

        _grid_body = (
            f'<div style="overflow-x:auto;width:100%;padding-bottom:8px;">'
            f'<div style="display:flex;min-width:{total_w}px;">{hdr_spacer}{hdr_cols}</div>'
            f'<div style="display:flex;min-width:{total_w}px;">{axis_col}{grid_cols}</div>'
            f'</div>'
        )
        return _grid_body, total_h + _HDR_H

    # ── Caché de colores por torneo ───────────────────────
    _ag_torneo_color_cache: dict = {}
    _ag_name_to_id = {t["nombre"]: t["id"] for t in _ag_todos_torneos}
    for _p in _ag_partidos:
        _tid = _p.get("torneo_id") or _ag_name_to_id.get(_p.get("nombre_torneo", ""), "")
        if _tid and _tid not in _ag_torneo_color_cache:
            _ag_torneo_color_cache[_tid] = torneo_card_color(_tid)

    # ── Agrupar fecha → campo → partidos ──────────────────
    _ag_por_fecha: dict = defaultdict(lambda: defaultdict(list))
    for _p in sorted(_ag_partidos, key=lambda x: (str(x.get("fecha") or ""), str(x.get("hora") or ""))):
        _ag_por_fecha[str(_p.get("fecha") or "")][_p.get("campo") or "Sin campo"].append(_p)

    DIAS_ES  = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    for _fecha_iso in sorted(_ag_por_fecha.keys()):
        try:
            _dt = datetime.date.fromisoformat(_fecha_iso)
            _titulo_dia = f"{DIAS_ES[_dt.weekday()]} {_dt.day} de {MESES_ES[_dt.month - 1]} de {_dt.year}"
        except Exception:
            _titulo_dia = _fecha_iso
        st.markdown(f"### {_titulo_dia}")
        _campos_dia = _ag_por_fecha[_fecha_iso]
        _campo_list = sorted(_campos_dia.keys())
        # ini_min por día: auto desde el primer partido del día, con suelo si hora_ini está fijada
        _ini_min_dia = _dia_ini(_campos_dia)
        # fin_min por día: auto desde los partidos del día, capado por hora_fin si está fijada
        _fin_min_dia = _dia_fin_min(_campos_dia, _ini_min_dia)
        if _ag_hora_fin is not None:
            _fin_min_dia = min(_fin_min_dia, _ag_fin_min_eff)
        _fin_min_dia = max(_fin_min_dia, _ini_min_dia + 30)
        _html_frag, _grid_content_h = _dia_grid_html(
            _campos_dia, _campo_list, _ag_torneo_color_cache, _ini_min_dia, _fin_min_dia
        )
        st.components.v1.html(_html_frag, height=int(_grid_content_h) + 20, scrolling=False)
        st.markdown("---")

    st.stop()

# Guard: todas las secciones requieren un torneo seleccionado
if not torneo_actual:
    st.warning("Selecciona o crea un torneo en el sidebar para continuar.")
    st.stop()

assert torneo_actual is not None  # garantizado por el guard anterior
torneo_id: str = torneo_actual["id"]

# -------------------------------------------------------
# DIALOGS DE MÓDULO
# -------------------------------------------------------
@st.dialog("Enlace y código QR")
def _modal_qr(label: str, url: str) -> None:
    st.markdown(f"**{label}**")
    st.code(url, language=None)
    st.divider()
    try:
        qr_bytes = generar_qr(url).getvalue()
        col_img, col_acc = st.columns([1, 1])
        col_img.image(qr_bytes, width='stretch')
        with col_acc:
            st.caption("Escanea para abrir el enlace directamente.")
            st.download_button(
                "Descargar QR",
                data=qr_bytes,
                file_name=f"qr_{label.replace(' ', '_')}.png",
                mime="image/png",
                key="dl_qr_modal",
            )
    except Exception as e:
        st.error(f"Error generando QR: {e}")


# -------------------------------------------------------
# AJUSTES
# -------------------------------------------------------
if menu == "Ajustes":
    t:   dict[str, Any] = torneo_actual
    tid: str            = torneo_id

    st.subheader(f"Ajustes — {t['nombre']}")
    if t.get("descripcion"):
        st.caption(t["descripcion"])

    # ── URLs ────────────────────────────────────────────────
    url_gestion = f"bracket.html?torneo={tid}"
    url_vista   = f"https://www.rffm.es/actualidad/futbol-7/torneo-campeones-2026?torneo={tid}"
    url_grupos  = f"grupos-info.html?torneo={tid}"

    fases_torneo = supabase.table("fases").select("id").eq("torneo_id", tid).eq("orden", 1).execute().data
    url_tv = None
    if fases_torneo:
        grupos_raw = supabase.table("grupos").select("id, nombre, orden_cuadro").eq("fase_id", fases_torneo[0]["id"]).execute().data
        grupos_tv_ord = _sort_grupos(grupos_raw)
        if grupos_tv_ord:
            url_tv = f"/?view=tv&grupo={grupos_tv_ord[0]['id']}&torneo={tid}"

    cards = [
        ("⚙️", "Bracket Gestión",   "Edita resultados y mueve equipos entre grupos", url_gestion),
        ("👁️", "Bracket Vista",     "Consulta pública, sin edición",                 url_vista),
        ("📋", "Cabeceras Grupos",  "Árbol de grupos con nombre y notas",             url_grupos),
    ]
    if url_tv:
        cards.append(("📺", "Vista TV", "Pantalla de sorteo en tiempo real", url_tv))

    # ── Tarjetas ────────────────────────────────────────────
    st.write("### Accesos")
    cols = st.columns(len(cards))
    for i, (icon, label, desc, url) in enumerate(cards):
        with cols[i]:
            with st.container(border=True):
                st.markdown(
                    f'<div style="font-size:2.2rem;text-align:center;padding:14px 0 6px;">{icon}</div>'
                    f'<p style="font-weight:700;font-size:0.95rem;text-align:center;margin:0 0 4px;">{label}</p>'
                    f'<p style="font-size:0.72rem;color:rgba(255,255,255,0.45);text-align:center;'
                    f'margin:0 0 18px;line-height:1.4;">{desc}</p>',
                    unsafe_allow_html=True,
                )
                if st.button("🔗 URL y QR", key=f"modal_btn_{i}", width='stretch'):
                    _modal_qr(label, url)
                st.link_button("↗ Abrir", url, width='stretch')

    # ── Visibilidad en el menú público ──────────────────────
    st.write("---")
    st.write("### Visibilidad")
    visible_actual = t.get("visible_bracket", True)
    nuevo_visible = st.toggle(
        "Mostrar en el menú público del Bracket Vista",
        value=visible_actual,
        help="Si está desactivado, el torneo no aparece en el menú de bracket-view.",
    )
    if nuevo_visible != visible_actual:
        set_visible_bracket(tid, nuevo_visible)
        st.rerun()

    orden_actual = t.get("orden_menu")
    col_ord, col_ord_btn = st.columns([3, 1])
    nuevo_orden = col_ord.number_input(
        "Posición en el menú público",
        min_value=1,
        max_value=99,
        value=int(orden_actual) if orden_actual is not None else 99,
        step=1,
        help="Número de orden en el menú del Bracket Vista. Los torneos sin valor asignado aparecen al final.",
    )
    if col_ord_btn.button("Guardar orden", width="stretch"):
        set_orden_menu(tid, int(nuevo_orden))
        st.success("✅ Orden actualizado.")
        st.rerun()

    # ── Zona de peligro ─────────────────────────────────────
    st.write("---")
    st.write("### Zona de peligro")
    with st.container(border=True):
        col_txt, col_btn = st.columns([5, 1])
        col_txt.markdown(
            f"Eliminar **{t['nombre']}** y **todos** sus datos (fases, grupos, equipos, participantes). "
            "Esta acción **no se puede deshacer**."
        )
        if col_btn.button("🗑️ Eliminar", key=f"del_{tid}", width='stretch'):
            st.session_state[f"confirm_del_{tid}"] = True

        if st.session_state.get(f"confirm_del_{tid}", False):
            st.warning(f"¿Seguro que quieres eliminar **{t['nombre']}**? Se borrarán todos los datos.")
            c1, c2 = st.columns(2)
            if c1.button("Sí, eliminar definitivamente", key=f"si_del_{tid}", type="primary"):
                try:
                    eliminar_torneo(tid)
                    st.session_state.pop(f"confirm_del_{tid}", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            c2.button(
                "Cancelar",
                key=f"no_del_{tid}",
                on_click=st.session_state.pop,
                args=[f"confirm_del_{tid}", None],
            )

@st.dialog("Importación Masiva de Equipos", width="large")
def _modal_carga_equipos(torneo_id):
    archivo = st.file_uploader("Sube tu Excel o CSV", type=["xlsx", "csv"])

    with st.expander("Ver formato esperado y descargar plantilla"):
        st.markdown("""
El archivo debe ser **Excel (.xlsx)** o **CSV (.csv)** con estas columnas:

| Columna | Obligatorio | Descripción |
|---|---|---|
| `nombre` | ✅ Sí | Nombre del equipo |
| `escudo_url` | ❌ No | URL pública de la imagen del escudo |
| `competicion` | ❌ No | Competición de procedencia |
| `grupo` | ❌ No | Grupo dentro de la competición |

La primera fila debe ser la cabecera con esos nombres exactos (en minúsculas).
Si el equipo ya existe, **solo se actualizan los campos que vengan rellenos**; los vacíos conservan el valor que hay en base de datos.
        """)
        plantilla_df = pd.DataFrame({
            "nombre":      ["Real Madrid", "Barcelona", "Atlético de Madrid"],
            "escudo_url":  ["https://ejemplo.com/rm.png", "https://ejemplo.com/fcb.png", ""],
            "competicion": ["Liga Nacional", "Liga Nacional", "Primera División"],
            "grupo":       ["Grupo A", "Grupo B", ""],
        })
        st.dataframe(plantilla_df, width='stretch', hide_index=True)
        csv_plantilla = plantilla_df.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar plantilla CSV", csv_plantilla, "plantilla_equipos.csv", "text/csv")

    if archivo:
        try:
            df = pd.read_excel(archivo) if archivo.name.endswith("xlsx") else pd.read_csv(archivo)
            # Normalizar nombres de columna: minúsculas, sin espacios, sin acentos
            import unicodedata
            def _norm_col(s):
                s = str(s).strip().lower()
                s = unicodedata.normalize("NFD", s)
                s = "".join(c for c in s if unicodedata.category(c) != "Mn")
                return s
            df.columns = [_norm_col(c) for c in df.columns]
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            st.info("Asegúrate de que el archivo no está corrupto y es un Excel o CSV válido.")
            df = None

        if df is not None:
            st.write("### Vista previa")
            st.dataframe(df, width='stretch')

            if "nombre" not in df.columns:
                st.error("Falta la columna obligatoria: `nombre`")
                cols_encontradas = [f"`{c}`" for c in df.columns.tolist()]
                st.markdown(
                    f"**Columnas encontradas:** {', '.join(cols_encontradas) if cols_encontradas else '_(ninguna)_'}\n\n"
                    "La primera fila debe contener al menos la columna `nombre` (en minúsculas)."
                )
            elif bool(df["nombre"].isna().all()) or df.empty:
                st.error("El archivo está vacío o la columna `nombre` no tiene datos.")
            else:
                # Columnas opcionales presentes en el archivo
                COLS_OPC = ["escudo_url", "competicion", "grupo"]
                cols_opc_presentes = [c for c in COLS_OPC if c in df.columns]

                # Limpiar: quitar filas sin nombre
                df = df[df["nombre"].notna() & (df["nombre"].astype(str).str.strip() != "")].copy()
                df["nombre"] = df["nombre"].astype(str).str.strip()

                # Lookup BD: nombre_upper -> equipo completo
                equipos_bd   = get_equipos(torneo_id)
                bd_por_nombre = {e["nombre"].strip().upper(): e for e in equipos_bd}

                df["_upper"] = df["nombre"].str.upper()
                df_nuevos     = df[~df["_upper"].isin(bd_por_nombre)].drop(columns=["_upper"])
                df_existentes = df[ df["_upper"].isin(bd_por_nombre)].copy()

                # Resumen
                partes = []
                if not df_nuevos.empty:
                    partes.append(f"**{len(df_nuevos)} nuevo(s)**")
                if not df_existentes.empty:
                    partes.append(f"**{len(df_existentes)} existente(s)** (se actualizarán por merge)")
                if partes:
                    st.info("Se procesarán: " + " · ".join(partes))

                if df_nuevos.empty and df_existentes.empty:
                    st.error("No hay filas válidas para procesar.")
                else:
                    n_tot = len(df_nuevos) + len(df_existentes)
                    if st.button(f"Confirmar y procesar {n_tot} equipo(s)",
                                 type="primary", width='stretch'):
                        errores = []
                        with st.spinner("Procesando equipos..."):
                            # ── INSERT nuevos ──────────────────────────────
                            if not df_nuevos.empty:
                                cols_insert = ["nombre"] + cols_opc_presentes
                                registros = (
                                    df_nuevos[cols_insert]
                                    .fillna("")
                                    .to_dict(orient="records")
                                )
                                resultado = subir_equipos_batch(registros, torneo_id)
                                if isinstance(resultado, str):
                                    errores.append(resultado)

                            # ── UPDATE existentes (merge) ──────────────────
                            for _, row in df_existentes.iterrows():
                                eq_bd = bd_por_nombre[row["nombre"].upper()]
                                campos = {}
                                for col in cols_opc_presentes:
                                    val = str(row[col]).strip() if row.get(col) is not None else ""
                                    if val:  # solo sobreescribe si viene relleno
                                        campos[col] = val
                                try:
                                    patch_equipo(eq_bd["id"], campos)
                                except Exception as e:
                                    errores.append(f"{row['nombre']}: {e}")

                        if errores:
                            for err in errores:
                                st.error(err)
                        else:
                            st.success(f"¡{n_tot} equipos procesados con éxito!")
                            st.rerun()


@st.dialog("✏️ Editar equipo")
def _modal_editar_equipo(equipo: dict[str, Any]) -> None:
    escudo_actual = equipo.get("escudo_url") or ""
    if escudo_actual:
        st.image(escudo_actual, width=80)
    nuevo_nombre = st.text_input("Nombre del equipo", value=equipo["nombre"])
    nuevo_escudo = st.text_input("URL del escudo (opcional)", value=escudo_actual,
                                 placeholder="https://ejemplo.com/escudo.png")
    if nuevo_escudo and nuevo_escudo != escudo_actual:
        st.image(nuevo_escudo, width=80, caption="Vista previa")
    fichero = st.file_uploader(
        "O sube una imagen directamente",
        type=["png", "jpg", "jpeg", "webp", "svg"],
        help="Si subes una imagen, reemplaza la URL anterior.",
    )
    if fichero:
        st.image(fichero, width=80, caption="Vista previa del fichero")
    nueva_competicion = st.text_input("Competición", value=equipo.get("competicion") or "",
                                      placeholder="Ej: Liga Nacional")
    nuevo_grupo = st.text_input("Grupo", value=equipo.get("grupo") or "",
                                placeholder="Ej: Grupo A")
    st.write("")
    if st.button("💾 Guardar cambios", width='stretch', type="primary"):
        nombre_limpio = nuevo_nombre.strip()
        if not nombre_limpio:
            st.error("El nombre no puede estar vacío.")
        else:
            if fichero:
                try:
                    url_final = subir_escudo(fichero)
                except Exception as e:
                    st.error(f"Error al subir la imagen: {e}")
                    st.stop()
            else:
                url_final = nuevo_escudo.strip()
            update_equipo(equipo["id"], nombre_limpio, url_final,
                          nueva_competicion.strip(), nuevo_grupo.strip())
            st.rerun()


# -------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------
if menu == "Dashboard":
    equipos = get_equipos(torneo_id)
    col_e1, col_e2, col_btn, col_pdf, col_grp = st.columns([1, 1, 1, 1, 1], vertical_alignment="bottom")
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e["eliminado"]]))
    if col_btn.button("Añadir equipos", width='stretch'):
        _modal_carga_equipos(torneo_id)
    if col_pdf.button("🖨️ Tarjetas sorteo", width='stretch', disabled=len(equipos) == 0):
        with st.spinner("Generando tarjetas…"):
            from src.pdf.tarjetas import generar_pdf_tarjetas
            _pdf_bytes = generar_pdf_tarjetas(equipos, torneo_actual["nombre"])
        st.download_button(
            "📥 Descargar PDF",
            data=_pdf_bytes,
            file_name=f"tarjetas_{torneo_actual['nombre']}.pdf",
            mime="application/pdf",
            width='stretch',
        )
    if col_grp.button("📋 Detalle grupos", width='stretch'):
        with st.spinner("Generando PDF de grupos…"):
            from src.pdf.grupos import generar_pdf_grupos
            _fases_data = get_grupos_pdf_data(torneo_id)
        if not _fases_data:
            col_grp.warning("No hay grupos configurados.")
        else:
            _pdf_grp = generar_pdf_grupos(_fases_data, torneo_actual["nombre"])
            st.download_button(
                "📥 Descargar PDF grupos",
                data=_pdf_grp,
                file_name=f"grupos_{torneo_actual['nombre']}.pdf",
                mime="application/pdf",
                width='stretch',
            )

    st.write("---")
    st.subheader("Plantilla de Equipos")
    busqueda = st.text_input("Buscar equipo", placeholder="Filtrar por nombre...", label_visibility="collapsed")
    equipos_filtrados = (
        [e for e in equipos if busqueda.strip().upper() in e["nombre"].upper()]
        if busqueda.strip() else equipos
    )
    if busqueda.strip() and not equipos_filtrados:
        st.caption("Sin resultados.")
    renderizar_tarjetas_equipos(equipos_filtrados, editable=True, on_edit=_modal_editar_equipo, torneo_id=torneo_id)

# -------------------------------------------------------
# CONFIGURADOR
# -------------------------------------------------------
if menu == "Configurador":
    st.subheader("Definición de Grupos por Fase")

    with st.expander("➕ Crear Nueva Fase"):
        nueva_fase_nombre = st.text_input("Nombre de la fase (ej: Fase de grupos)")
        orden_fase = st.number_input("Orden", min_value=1, value=1)
        if st.button("Guardar Fase"):
            try:
                crear_fase(nueva_fase_nombre, orden_fase, torneo_id)
                st.success("Fase creada")
                st.rerun()
            except Exception as e:
                st.error(f"Error al crear la fase: {e}")

    fases = get_fases(torneo_id)

    if not fases:
        st.info("Crea una fase arriba para empezar.")
    else:
        col_sel, col_toggle = st.columns([4, 1], vertical_alignment="bottom")
        fase_sel = col_sel.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)

        if fase_actual:
            fase_id = fase_actual["id"]
            es_fase_progresion = fase_actual["orden"] > 1

            # ── Visibilidad en el bracket público ─────────────
            oculta_actual = fase_actual.get("oculta_bracket") or False
            nueva_oculta  = col_toggle.toggle(
                "Ocultar en bracket",
                value=oculta_actual,
                key=f"oculta_{fase_id}",
                help="Oculta esta fase en el Bracket Vista público (Bracket Gestión no se ve afectado)",
            )
            if nueva_oculta != oculta_actual:
                set_fase_oculta_bracket(fase_id, nueva_oculta)
                st.rerun()

            # ── Formato de partidos ──────────────────────────
            num_vueltas_actual = fase_actual.get("num_vueltas") or 1
            col_v, col_aviso = st.columns([2, 3])
            vuelta_sel = col_v.radio(
                "Formato de partidos",
                options=[1, 2],
                format_func=lambda x: "Ida (1 partido)" if x == 1 else "Ida y vuelta (2 partidos)",
                index=num_vueltas_actual - 1,
                horizontal=True,
                key=f"num_vueltas_{fase_id}",
            )
            if vuelta_sel != num_vueltas_actual:
                actualizar_num_vueltas(fase_id, vuelta_sel)
                if hay_partidos_fase(fase_id):
                    col_aviso.warning("⚠️ Formato cambiado. Ve a **Partidos** y regenera el calendario.")
                st.rerun()
            elif hay_partidos_fase(fase_id):
                col_aviso.info("ℹ️ Esta fase ya tiene partidos generados. Si cambias equipos o grupos, ve a **Partidos** y regenera.")

            st.write("---")
            col1, col2, col3 = st.columns([2, 2, 1], vertical_alignment="bottom")
            with col1:
                num_grupos = st.number_input("Añadir N grupos", min_value=1, value=1)
            with col2:
                tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
            with col3:
                if st.button("Añadir", width='stretch'):
                    try:
                        total_existentes = contar_grupos_fase(fase_id)
                        nuevos_grupos = [
                            {
                                "fase_id": fase_id,
                                "nombre": f"{fase_actual['nombre']} {total_existentes + i + 1}",
                                "tipo_grupo": tamano_grupo,
                            }
                            for i in range(num_grupos)
                        ]
                        crear_grupos(nuevos_grupos)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al añadir grupos: {e}")

            st.write("### Estructura y Origen de Plazas")
            grupos = _sort_grupos(get_grupos_por_fase(fase_id))

            if grupos:
                if not es_fase_progresion:
                    st.info("Fase 1: las plazas se llenan por sorteo, no requiere configuración de origen.")

                    with st.expander("Orden y nombres en el cuadro visual"):
                        st.caption("Edita el nombre, el número de equipos y la posición (1, 2, 3…) de cada grupo en el bracket.")
                        orden_rows = [
                            {"Nombre": g["nombre"], "Equipos": g["tipo_grupo"], "Posición": g.get("orden_cuadro")}
                            for g in grupos
                        ]
                        edited_orden = st.data_editor(
                            orden_rows,
                            column_config={
                                "Nombre":   st.column_config.TextColumn(),
                                "Equipos":  st.column_config.NumberColumn(min_value=1, step=1),
                                "Posición": st.column_config.NumberColumn(min_value=1, step=1),
                            },
                            hide_index=True,
                            width='stretch',
                            key=f"orden_cuadro_editor_{fase_id}",
                        )
                        if st.button("Guardar cambios", key=f"guardar_orden_{fase_id}", type="primary"):
                            try:
                                for row, g in zip(edited_orden, grupos):
                                    try:
                                        orden = int(row["Posición"]) if row["Posición"] is not None else None
                                    except (ValueError, TypeError):
                                        orden = None
                                    try:
                                        equipos_num = int(row["Equipos"]) if row["Equipos"] else g["tipo_grupo"]
                                    except (ValueError, TypeError):
                                        equipos_num = g["tipo_grupo"]
                                    nombre = (row["Nombre"] or "").strip() or g["nombre"]
                                    actualizar_grupo(g["id"], nombre, equipos_num, orden)
                                st.success("Cambios guardados.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")
                else:
                    fase_anterior = next(
                        (f for f in fases if f["orden"] == fase_actual["orden"] - 1), None
                    )
                    grupos_fase_anterior = _sort_grupos(get_grupos_por_fase(fase_anterior["id"])) if fase_anterior else []

                    configurar_progresion_visual(
                        grupos_destino=grupos,
                        grupos_origen=grupos_fase_anterior,
                        supabase=supabase,
                        torneo_id=torneo_id,
                    )

                total_plazas = sum(g["tipo_grupo"] for g in grupos)
                st.info(f"Capacidad total de la fase: {total_plazas} equipos.")

                with st.expander("🗑️ Eliminar un grupo"):
                    for g in grupos:
                        g_id = g["id"]
                        confirm_key = f"confirm_del_grupo_{g_id}"
                        col_nombre, col_btn = st.columns([6, 1])
                        col_nombre.markdown(f"**{g['nombre']}** — {g['tipo_grupo']} equipos")
                        if col_btn.button("🗑️", key=f"del_grupo_{g_id}", help=f"Eliminar {g['nombre']}"):
                            st.session_state[confirm_key] = True
                        if st.session_state.get(confirm_key):
                            st.warning(
                                f"¿Eliminar **{g['nombre']}** y todos sus participantes? "
                                "Esta acción no se puede deshacer."
                            )
                            c1, c2 = st.columns(2)
                            if c1.button("Sí, eliminar", key=f"si_del_grupo_{g_id}", type="primary"):
                                try:
                                    eliminar_grupo(g_id)
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                            c2.button(
                                "Cancelar",
                                key=f"no_del_grupo_{g_id}",
                                on_click=st.session_state.pop,
                                args=[confirm_key, None],
                            )



# -------------------------------------------------------
# CUADRO VISUAL
# -------------------------------------------------------
if menu == "Cuadro Visual":
    st.subheader("Gestión de Equipos por Grupo")

    fases = get_fases(torneo_id)

    if not fases:
        st.info("No hay fases configuradas.")
    else:
        fase_sel = st.selectbox("Seleccionar Fase", [f["nombre"] for f in fases])
        fase_actual = next(f for f in fases if f["nombre"] == fase_sel)
        fase_id = fase_actual["id"]
        es_progresion = fase_actual["orden"] > 1

        grupos = _sort_grupos(get_grupos_por_fase(fase_id))
        ids_grupos = [g["id"] for g in grupos]

        if hay_partidos_fase(fase_id):
            st.warning("⚠️ Esta fase ya tiene partidos generados. Si modificas equipos o progresiones, ve a **Partidos** y regenera el calendario.")

        todos_participantes = get_participantes_grupos(ids_grupos) if ids_grupos else []

        participantes_por_grupo: dict = {}
        for p in todos_participantes:
            participantes_por_grupo.setdefault(p["grupo_id"], []).append(p)



        if not es_progresion:
            ocupados_ids = {p["equipo_id"] for p in todos_participantes if p["equipo_id"]}
            equipos_libres = get_equipos_libres(torneo_id, ocupados_ids)

            cols_grupos = st.columns(3)
            for idx, grupo in enumerate(grupos):
                participantes = participantes_por_grupo.get(grupo["id"], [])
                with cols_grupos[idx % 3]:
                    renderizar_tarjeta_grupo_minimalista(
                        grupo=grupo,
                        participantes=participantes,
                        equipos_libres=equipos_libres,
                        es_progresion=False,
                        fases=fases,
                        fase_actual=fase_actual,
                        supabase=supabase,
                    )
        else:
            fase_anterior = next(
                (f for f in fases if f["orden"] == fase_actual["orden"] - 1), None
            )
            grupos_fase_anterior = _sort_grupos(get_grupos_por_fase(fase_anterior["id"])) if fase_anterior else []
            ids_grupos_ant = [g["id"] for g in grupos_fase_anterior]

            participantes_fase_ant = get_participantes_grupos(ids_grupos_ant) if ids_grupos_ant else []

            participantes_ant_por_grupo: dict = {}
            for p in participantes_fase_ant:
                participantes_ant_por_grupo.setdefault(p["grupo_id"], []).append(p)

            ya_asignados_ids = {p["equipo_id"] for p in todos_participantes if p["equipo_id"]}

            renderizar_cuadro_progresion(
                grupos_destino=grupos,
                grupos_origen=grupos_fase_anterior,
                participantes_por_grupo_destino=participantes_por_grupo,
                participantes_por_grupo_origen=participantes_ant_por_grupo,
                ya_asignados_ids=ya_asignados_ids,
                fases=fases,
                fase_actual=fase_actual,
                supabase=supabase,
            )

# -------------------------------------------------------
# PARTIDOS
# -------------------------------------------------------
if menu == "Partidos":
    st.subheader("Calendario de Partidos")

    fases = get_fases(torneo_id)
    if not fases:
        st.info("No hay fases configuradas.")
        st.stop()

    _pt_c1, _pt_c2 = st.columns([3, 1])
    fase_sel = _pt_c1.selectbox("Fase", [f["nombre"] for f in fases])
    fase_actual = next(f for f in fases if f["nombre"] == fase_sel)
    fase_id     = fase_actual["id"]
    num_vueltas = fase_actual.get("num_vueltas") or 1

    _dur_actual = fase_actual.get("duracion_partido") or 50
    _dur_nueva  = _pt_c2.number_input(
        "Duración (min)", min_value=10, max_value=120, value=_dur_actual,
        step=5, key=f"dur_{fase_id}",
        help="Duración de cada partido en minutos. Se usa en la Agenda Global.",
    )
    if _dur_nueva != _dur_actual:
        actualizar_duracion_fase(fase_id, int(_dur_nueva))

    tiene_partidos = hay_partidos_fase(fase_id)

    # ── Generar / Regenerar / Sincronizar ───────────────
    col_gen, col_sync, col_pdf, col_filtro_campo, col_filtro_equipo = st.columns([2, 2, 2, 2, 2])
    with col_gen:
        lbl = "🔄 Regenerar partidos" if tiene_partidos else "⚡ Generar partidos"
        if st.button(lbl, type="primary", width='stretch'):
            if tiene_partidos:
                st.session_state[f"confirm_regen_{fase_id}"] = True
            else:
                try:
                    with st.spinner("Generando partidos..."):
                        n = generar_partidos_fase(fase_id, num_vueltas)
                    if n == 0:
                        st.warning("No se generaron partidos. Revisa que los grupos tienen al menos 2 plazas (campo 'Equipos por grupo').")
                    else:
                        st.success(f"✅ {n} partidos generados.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al generar partidos: {e}")

    with col_sync:
        if tiene_partidos:
            if st.button("🔗 Sincronizar equipos", width='stretch',
                         help="Actualiza los partidos con los equipos que ya han ocupado su plaza en el sorteo"):
                try:
                    with st.spinner("Sincronizando..."):
                        n = sincronizar_equipos_partidos_fase(fase_id)
                    st.success(f"✅ {n} partidos actualizados con equipos reales.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al sincronizar: {e}")

    with col_pdf:
        if tiene_partidos:
            if st.button("📄 Generar PDF", width='stretch', help="Descarga un PDF con las tarjetas de todos los partidos"):
                try:
                    with st.spinner("Generando PDF..."):
                        from src.pdf.partidos import generar_pdf_partidos
                        _partidos_data = get_partidos_fase(fase_id)
                        _grupos_ord = sorted(
                            _partidos_data.items(),
                            key=lambda kv: (kv[1]["orden_cuadro"] is None, kv[1]["orden_cuadro"] or 0, kv[1]["nombre"]),
                        )
                        _torneo_nombre = torneo_actual.get("nombre", "Torneo")
                        _url_vista     = f"https://www.rffm.es/actualidad/futbol-7/torneo-campeones-2026?torneo={torneo_id}"
                        _pdf_bytes = generar_pdf_partidos(_grupos_ord, _torneo_nombre, _url_vista)
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=_pdf_bytes,
                        file_name=f"partidos_{fase_actual.get('nombre','fase').replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{fase_id}",
                    )
                except Exception as _e:
                    st.error(f"Error al generar PDF: {_e}")

    filtro_campo = col_filtro_campo.text_input(
        "Filtrar por campo", placeholder="🏟️ Campo...",
        label_visibility="collapsed",
    )
    filtro_equipo = col_filtro_equipo.text_input(
        "Filtrar por equipo", placeholder="⚽ Equipo...",
        label_visibility="collapsed",
    )

    if st.session_state.get(f"confirm_regen_{fase_id}"):
        st.warning(
            "⚠️ Ya existen partidos para esta fase. Se borrarán todos y se regenerarán "
            "con los equipos y el formato actuales."
        )
        c1, c2 = st.columns(2)
        if c1.button("Sí, regenerar", type="primary", key=f"si_regen_{fase_id}"):
            try:
                with st.spinner("Regenerando..."):
                    eliminar_partidos_fase(fase_id)
                    n = generar_partidos_fase(fase_id, num_vueltas)
                st.session_state.pop(f"confirm_regen_{fase_id}", None)
                if n == 0:
                    st.warning("Se borraron los partidos anteriores, pero no se generaron nuevos. Revisa que los grupos tienen al menos 2 plazas configuradas.")
                else:
                    st.success(f"✅ {n} partidos generados.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al regenerar partidos: {e}")
        c2.button(
            "Cancelar", key=f"no_regen_{fase_id}",
            on_click=st.session_state.pop,
            args=[f"confirm_regen_{fase_id}", None],
        )

    st.write("---")

    # ── Listado editable por grupo ───────────────────────
    partidos_por_grupo = get_partidos_fase(fase_id)

    if not partidos_por_grupo:
        st.info("No hay partidos generados para esta fase. Usa el botón de arriba para crearlos.")
    else:
        grupos_ordenados = sorted(
            partidos_por_grupo.items(),
            key=lambda kv: (kv[1]["orden_cuadro"] is None, kv[1]["orden_cuadro"] or 0, kv[1]["nombre"]),
        )
        for grupo_id, info in grupos_ordenados:
            partidos = info["partidos"]
            _fc = filtro_campo.strip().lower()
            _fe = filtro_equipo.strip().lower()
            if _fc:
                partidos = [p for p in partidos if _fc in (p.get("campo") or "").lower()]
            if _fe:
                partidos = [
                    p for p in partidos
                    if _fe in (p.get("nombre_local") or "").lower()
                    or _fe in (p.get("nombre_visitante") or "").lower()
                ]
            if not partidos and (_fc or _fe):
                continue

            with st.expander(f"**{info['nombre']}** — {len(partidos)} partido(s)", expanded=True):
                df_vista = pd.DataFrame([
                    {
                        "Jornada":    p["jornada"],
                        "Local":      p["nombre_local"],
                        "Visitante":  p["nombre_visitante"],
                        "Fecha":      pd.to_datetime(p["fecha"]).date() if p.get("fecha") else None,
                        "Hora":       p.get("hora") or "",
                        "Campo":      p.get("campo") or "",
                        "Goles L":    p.get("resultado_local"),
                        "Goles V":    p.get("resultado_visitante"),
                        "Invertir ⇅": False,
                        "🗑️":         False,
                    }
                    for p in partidos
                ])

                edited = st.data_editor(
                    df_vista,
                    column_config={
                        "Jornada":    st.column_config.NumberColumn(min_value=1, step=1, width="small"),
                        "Local":      st.column_config.TextColumn(disabled=True),
                        "Visitante":  st.column_config.TextColumn(disabled=True),
                        "Fecha":      st.column_config.DateColumn(width="medium", format="DD/MM/YYYY"),
                        "Hora":       st.column_config.TextColumn(width="small", help="Formato HH:MM"),
                        "Campo":      st.column_config.TextColumn(width="medium"),
                        "Goles L":    st.column_config.NumberColumn(min_value=0, step=1, width="small"),
                        "Goles V":    st.column_config.NumberColumn(min_value=0, step=1, width="small"),
                        "Invertir ⇅": st.column_config.CheckboxColumn(
                            help="Intercambia local y visitante al guardar",
                            width="small",
                        ),
                        "🗑️": st.column_config.CheckboxColumn(
                            help="Marca para eliminar este partido al guardar",
                            width="small",
                        ),
                    },
                    hide_index=True,
                    width='stretch',
                    key=f"editor_partidos_{grupo_id}",
                )

                if st.button("Guardar cambios", key=f"guardar_{grupo_id}", type="primary"):
                    updates = []
                    eliminados = 0
                    for i, row in edited.iterrows():
                        p = partidos[i]
                        if bool(row.get("🗑️", False)):
                            eliminar_partido(p["id"])
                            eliminados += 1
                            continue
                        goles_l  = row["Goles L"]
                        goles_v  = row["Goles V"]
                        fecha    = row["Fecha"]
                        invertir = bool(row.get("Invertir ⇅", False))
                        jornada_val = row.get("Jornada")
                        jornada  = int(jornada_val) if jornada_val is not None and not (isinstance(jornada_val, float) and pd.isna(jornada_val)) else p["jornada"]

                        upd = {
                            "id":                  p["id"],
                            "jornada":             jornada,
                            "fecha":               str(fecha) if fecha is not None else None,
                            "hora":                row["Hora"] or None,
                            "campo":               row["Campo"] or None,
                            "resultado_local":     int(goles_l) if goles_l is not None else None,
                            "resultado_visitante": int(goles_v) if goles_v is not None else None,
                        }
                        if invertir:
                            upd["equipo_local_id"]     = p.get("equipo_visitante_id")
                            upd["equipo_visitante_id"] = p.get("equipo_local_id")
                            upd["pos_local"]           = p.get("pos_visitante")
                            upd["pos_visitante"]       = p.get("pos_local")
                            upd["resultado_local"]     = int(goles_v) if goles_v is not None else None
                            upd["resultado_visitante"] = int(goles_l) if goles_l is not None else None
                        updates.append(upd)
                    if updates:
                        actualizar_partidos_batch(updates)
                    if eliminados:
                        st.success(f"✅ Guardado. {eliminados} partido(s) eliminado(s).")
                    else:
                        st.success("Guardado.")
                    st.rerun()


# -------------------------------------------------------
# SORTEO
# -------------------------------------------------------
if menu == "Sorteo":
    seccion_sorteo_manual(supabase, torneo_id)