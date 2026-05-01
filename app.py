import io
import re as _re
import urllib.parse
import datetime
from collections import defaultdict

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
    hay_partidos_fase,
    eliminar_partidos_fase,
    generar_partidos_fase,
    get_partidos_fase,
    actualizar_partidos_batch,
    sincronizar_equipos_partidos_fase,
    get_campos_distintos,
    get_partidos_agenda,
)
from src.logic import seccion_sorteo_manual
from src.components import (
    renderizar_tarjetas_equipos,
    mostrar_grupo_tv,
    configurar_progresion_visual,
    renderizar_tarjeta_grupo_minimalista,
    renderizar_cuadro_progresion,
)


# ── QR helper ──────────────────────────────────────────
def generar_qr(url: str):
    import qrcode
    from PIL import Image
    import urllib.request as _urlreq

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # H=30% tolerancia para incrustar logo
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#7b0000", back_color="white").convert("RGBA")

    # Incrustar el escudo RFFM centrado
    try:
        with _urlreq.urlopen(LOGO_RFFM_URL, timeout=5) as resp:
            logo = Image.open(io.BytesIO(resp.read())).convert("RGBA")
        qr_w, qr_h = img.size
        logo_size = qr_w // 4  # ocupa el 25% del ancho del QR
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        # Fondo blanco con margen alrededor del logo
        pad = 6
        bg = Image.new("RGBA", (logo_size + pad * 2, logo_size + pad * 2), (255, 255, 255, 255))
        bg_pos = ((qr_w - bg.width) // 2, (qr_h - bg.height) // 2)
        img.paste(bg, bg_pos)
        logo_pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        img.paste(logo, logo_pos, logo)
    except Exception:
        pass  # si falla la descarga el QR sigue siendo válido

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
            submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")

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
if st.sidebar.button("🔒 Cerrar sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

# QR de acceso al menú de cuadros (URL global, no ligada a ningún torneo)
_URL_CUADRO = "https://bit.ly/cuadro-torneo-rffm"
with st.sidebar.expander("QR Cuadro Visual"):
    _buf = generar_qr(_URL_CUADRO)
    st.image(_buf, use_container_width=True)
    _buf.seek(0)
    st.download_button(
        "Descargar",
        data=_buf,
        file_name="qr_cuadro_rffm.png",
        mime="image/png",
        use_container_width=True,
    )

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
    )
    st.session_state.torneo_idx = nombres_torneos.index(torneo_sel)
    torneo_actual = next((t for t in torneos if t["nombre"] == torneo_sel), None)
    torneo_id = torneo_actual["id"]

with st.sidebar.expander("➕ Nuevo torneo"):
    nuevo_nombre = st.text_input("Nombre", placeholder="ej: Copa RFFM 2026", key="sb_nuevo_nombre")
    nueva_desc   = st.text_input("Descripción (opcional)", key="sb_nueva_desc")
    if st.button("Crear", use_container_width=True, key="sb_crear_torneo"):
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
    ["Dashboard", "Configurador", "Cuadro Visual", "Partidos", "Agenda", "Sorteo", "Ajustes"],
)

# Guard: todas las secciones requieren un torneo seleccionado
if not torneo_actual:
    st.warning("Selecciona o crea un torneo en el sidebar para continuar.")
    st.stop()

# -------------------------------------------------------
# AJUSTES
# -------------------------------------------------------
if menu == "Ajustes":
    t   = torneo_actual
    tid = torneo_id

    st.subheader(f"Ajustes — {t['nombre']}")
    if t.get("descripcion"):
        st.caption(t["descripcion"])

    # ── URLs ────────────────────────────────────────────────
    url_gestion = f"bracket.html?torneo={tid}"
    url_vista   = f"bracket-view.html?torneo={tid}"
    url_grupos  = f"grupos-info.html?torneo={tid}"

    fases_torneo = supabase.table("fases").select("id").eq("torneo_id", tid).eq("orden", 1).execute().data
    url_tv = None
    if fases_torneo:
        grupos_raw = supabase.table("grupos").select("id, nombre, orden_cuadro").eq("fase_id", fases_torneo[0]["id"]).execute().data
        grupos_tv_ord = sorted(
            grupos_raw,
            key=lambda g: (g["orden_cuadro"] if g.get("orden_cuadro") is not None else float("inf"),
                           int(m.group()) if (m := _re.search(r"\d+", g["nombre"])) else 0)
        )
        if grupos_tv_ord:
            url_tv = f"/?view=tv&grupo={grupos_tv_ord[0]['id']}&torneo={tid}"

    cards = [
        ("⚙️", "Bracket Gestión",   "Edita resultados y mueve equipos entre grupos", url_gestion),
        ("👁️", "Bracket Vista",     "Consulta pública, sin edición",                 url_vista),
        ("📋", "Cabeceras Grupos",  "Árbol de grupos con nombre y notas",             url_grupos),
    ]
    if url_tv:
        cards.append(("📺", "Vista TV", "Pantalla de sorteo en tiempo real", url_tv))

    # ── Modal QR ────────────────────────────────────────────
    @st.dialog("Enlace y código QR")
    def _modal_qr(label, url):
        st.markdown(f"**{label}**")
        st.code(url, language=None)
        st.divider()
        try:
            qr_bytes = generar_qr(url).getvalue()
            col_img, col_acc = st.columns([1, 1])
            col_img.image(qr_bytes, use_container_width=True)
            with col_acc:
                st.caption("Escanea para abrir el enlace directamente.")
                st.download_button(
                    "Descargar QR",
                    data=qr_bytes,
                    file_name=f"qr_{label.replace(' ', '_')}.png",
                    mime="image/png",
                    key=f"dl_qr_modal",
                )
        except Exception as e:
            st.error(f"Error generando QR: {e}")

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
                if st.button("🔗 URL y QR", key=f"modal_btn_{i}", use_container_width=True):
                    _modal_qr(label, url)
                st.link_button("↗ Abrir", url, use_container_width=True)

    # ── Zona de peligro ─────────────────────────────────────
    st.write("---")
    st.write("### Zona de peligro")
    with st.container(border=True):
        col_txt, col_btn = st.columns([5, 1])
        col_txt.markdown(
            f"Eliminar **{t['nombre']}** y **todos** sus datos (fases, grupos, equipos, participantes). "
            "Esta acción **no se puede deshacer**."
        )
        if col_btn.button("🗑️ Eliminar", key=f"del_{tid}", use_container_width=True):
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

# -------------------------------------------------------
# MODAL CARGA DE EQUIPOS
# -------------------------------------------------------
@st.dialog("Importación Masiva de Equipos", width="large")
def _modal_carga_equipos(torneo_id):
    archivo = st.file_uploader("Sube tu Excel o CSV", type=["xlsx", "csv"])

    with st.expander("Ver formato esperado y descargar plantilla"):
        st.markdown("""
El archivo debe ser **Excel (.xlsx)** o **CSV (.csv)** con exactamente estas dos columnas:

| Columna | Obligatorio | Descripción |
|---|---|---|
| `nombre` | ✅ Sí | Nombre del equipo |
| `escudo_url` | ✅ Sí | URL pública de la imagen del escudo (puede dejarse vacía) |

La primera fila debe ser la cabecera con esos nombres exactos (en minúsculas).
        """)
        plantilla_df = pd.DataFrame({
            "nombre":     ["Real Madrid", "Barcelona", "Atlético de Madrid"],
            "escudo_url": ["https://ejemplo.com/rm.png", "https://ejemplo.com/fcb.png", ""],
        })
        st.dataframe(plantilla_df, use_container_width=True, hide_index=True)
        csv_plantilla = plantilla_df.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar plantilla CSV", csv_plantilla, "plantilla_equipos.csv", "text/csv")

    if archivo:
        try:
            df = pd.read_excel(archivo) if archivo.name.endswith("xlsx") else pd.read_csv(archivo)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            st.info("Asegúrate de que el archivo no está corrupto y es un Excel o CSV válido.")
            df = None

        if df is not None:
            st.write("### Vista previa")
            st.dataframe(df, use_container_width=True)

            tiene_nombre = "nombre"     in df.columns
            tiene_escudo = "escudo_url" in df.columns

            if not tiene_nombre or not tiene_escudo:
                faltantes = []
                if not tiene_nombre: faltantes.append("`nombre`")
                if not tiene_escudo: faltantes.append("`escudo_url`")
                st.error(f"Faltan las columnas obligatorias: {', '.join(faltantes)}")
                cols_encontradas = [f"`{c}`" for c in df.columns.tolist()]
                st.markdown(
                    f"**Columnas encontradas:** {', '.join(cols_encontradas) if cols_encontradas else '_(ninguna)_'}\n\n"
                    "Revisa que la primera fila contiene exactamente `nombre` y `escudo_url` (en minúsculas)."
                )
            elif df["nombre"].isna().all() or df.empty:
                st.error("El archivo está vacío o la columna `nombre` no tiene datos.")
            else:
                nombres_existentes = {e["nombre"].strip().upper() for e in get_equipos(torneo_id)}
                df["_nuevo"] = ~df["nombre"].str.strip().str.upper().isin(nombres_existentes)
                duplicados = df[~df["_nuevo"]]["nombre"].tolist()
                df_nuevos  = df[df["_nuevo"]].drop(columns=["_nuevo"])

                if duplicados:
                    st.warning(f"⚠️ Ya existen y se omitirán: **{', '.join(duplicados)}**")

                if df_nuevos.empty:
                    st.error("Todos los equipos ya existen en el torneo.")
                else:
                    label = f"Confirmar y subir {len(df_nuevos)} equipo(s)" if duplicados else "Confirmar y subir"
                    if st.button(label, type="primary", use_container_width=True):
                        equipos_dict = df_nuevos[["nombre", "escudo_url"]].to_dict(orient="records")
                        with st.spinner(f"Subiendo {len(equipos_dict)} equipos..."):
                            resultado = subir_equipos_batch(equipos_dict, torneo_id)
                        if isinstance(resultado, str):
                            st.error(resultado)
                        else:
                            st.success(f"¡{len(equipos_dict)} equipos cargados con éxito!")
                            st.rerun()

# -------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------
if menu == "Dashboard":
    equipos = get_equipos(torneo_id)
    col_e1, col_e2, col_btn = st.columns([1, 1, 1], vertical_alignment="bottom")
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e["eliminado"]]))
    if col_btn.button("Añadir equipos", use_container_width=True, ):
        _modal_carga_equipos(torneo_id)

    st.write("---")
    st.subheader("Plantilla de Equipos")
    busqueda = st.text_input("Buscar equipo", placeholder="Filtrar por nombre...", label_visibility="collapsed")
    equipos_filtrados = (
        [e for e in equipos if busqueda.strip().upper() in e["nombre"].upper()]
        if busqueda.strip() else equipos
    )
    if busqueda.strip() and not equipos_filtrados:
        st.caption("Sin resultados.")
    renderizar_tarjetas_equipos(equipos_filtrados)

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
        fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)

        if fase_actual:
            fase_id = fase_actual["id"]
            es_fase_progresion = fase_actual["orden"] > 1

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
                if st.button("Añadir", use_container_width=True):
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
                            use_container_width=True,
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

    fase_sel = st.selectbox("Fase", [f["nombre"] for f in fases])
    fase_actual = next(f for f in fases if f["nombre"] == fase_sel)
    fase_id     = fase_actual["id"]
    num_vueltas = fase_actual.get("num_vueltas") or 1

    tiene_partidos = hay_partidos_fase(fase_id)

    # ── Generar / Regenerar / Sincronizar ───────────────
    col_gen, col_sync, col_filtro = st.columns([2, 2, 3])
    with col_gen:
        lbl = "🔄 Regenerar partidos" if tiene_partidos else "⚡ Generar partidos"
        if st.button(lbl, type="primary", use_container_width=True):
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
            if st.button("🔗 Sincronizar equipos", use_container_width=True,
                         help="Actualiza los partidos con los equipos que ya han ocupado su plaza en el sorteo"):
                try:
                    with st.spinner("Sincronizando..."):
                        n = sincronizar_equipos_partidos_fase(fase_id)
                    st.success(f"✅ {n} partidos actualizados con equipos reales.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al sincronizar: {e}")

    filtro_campo = col_filtro.text_input(
        "Filtrar por campo", placeholder="Escribe el nombre del campo...",
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
            if filtro_campo.strip():
                partidos = [
                    p for p in partidos
                    if filtro_campo.strip().lower() in (p.get("campo") or "").lower()
                ]
                if not partidos:
                    continue

            with st.expander(f"**{info['nombre']}** — {len(partidos)} partido(s)", expanded=True):
                df_vista = pd.DataFrame([
                    {
                        "Jornada":   p["jornada"],
                        "Local":     p["nombre_local"],
                        "Visitante": p["nombre_visitante"],
                        "Fecha":     pd.to_datetime(p["fecha"]).date() if p.get("fecha") else None,
                        "Hora":      p.get("hora") or "",
                        "Campo":     p.get("campo") or "",
                        "Goles L":   p.get("resultado_local"),
                        "Goles V":   p.get("resultado_visitante"),
                    }
                    for p in partidos
                ])

                edited = st.data_editor(
                    df_vista,
                    column_config={
                        "Jornada":   st.column_config.NumberColumn(disabled=True, width="small"),
                        "Local":     st.column_config.TextColumn(disabled=True),
                        "Visitante": st.column_config.TextColumn(disabled=True),
                        "Fecha":     st.column_config.DateColumn(width="medium", format="DD/MM/YYYY"),
                        "Hora":      st.column_config.TextColumn(width="small", help="Formato HH:MM"),
                        "Campo":     st.column_config.TextColumn(width="medium"),
                        "Goles L":   st.column_config.NumberColumn(min_value=0, step=1, width="small"),
                        "Goles V":   st.column_config.NumberColumn(min_value=0, step=1, width="small"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_partidos_{grupo_id}",
                )

                if st.button("Guardar cambios", key=f"guardar_{grupo_id}", type="primary"):
                    updates = []
                    for i, row in edited.iterrows():
                        goles_l = row["Goles L"]
                        goles_v = row["Goles V"]
                        fecha   = row["Fecha"]
                        updates.append({
                            "id":                  partidos[i]["id"],
                            "fecha":               str(fecha) if pd.notna(fecha) and fecha is not None else None,
                            "hora":                row["Hora"] or None,
                            "campo":               row["Campo"] or None,
                            "resultado_local":     int(goles_l) if pd.notna(goles_l) and goles_l != "" else None,
                            "resultado_visitante": int(goles_v) if pd.notna(goles_v) and goles_v != "" else None,
                        })
                    actualizar_partidos_batch(updates)
                    st.success("Guardado.")
                    st.rerun()

# -------------------------------------------------------
# AGENDA
# -------------------------------------------------------
if menu == "Agenda":
    st.subheader("Agenda de Partidos")

    # ── Carga previa de opciones de filtro ───────────────
    todos_torneos  = get_torneos()
    todos_campos   = get_campos_distintos()

    # ── Filtros ──────────────────────────────────────────
    hoy = datetime.date.today()
    fc1, fc2, fc3 = st.columns([1, 2, 2])
    fecha_sel = fc1.date_input("Fecha", value=hoy, format="DD/MM/YYYY")

    campos_sel = fc2.multiselect(
        "Campo(s)",
        options=todos_campos,
        placeholder="Todos los campos",
    )
    torneos_sel = fc3.multiselect(
        "Torneo(s)",
        options=[t["nombre"] for t in todos_torneos],
        placeholder="Todos los torneos",
    )

    torneo_ids_filtro = (
        [t["id"] for t in todos_torneos if t["nombre"] in torneos_sel]
        if torneos_sel else None
    )
    campos_filtro = campos_sel if campos_sel else None

    # ── Consulta ─────────────────────────────────────────
    with st.spinner("Cargando partidos..."):
        partidos = get_partidos_agenda(
            fecha_desde=fecha_sel,
            fecha_hasta=fecha_sel,
            campos=campos_filtro,
            torneo_ids=torneo_ids_filtro,
        )

    DIAS_ES   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    MESES_ES  = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    titulo_dia = f"{DIAS_ES[fecha_sel.weekday()]} {fecha_sel.day} de {MESES_ES[fecha_sel.month - 1]} de {fecha_sel.year}"
    st.markdown(f"### {titulo_dia}")
    st.markdown("---")

    if not partidos:
        st.info("No hay partidos programados para este día con los filtros seleccionados.")
        st.stop()

    # ── Agrupar por campo y listar ordenado por hora ──────
    por_campo = defaultdict(list)
    for p in sorted(partidos, key=lambda x: x.get("hora") or ""):
        por_campo[p.get("campo") or "Sin campo"].append(p)

    for campo_nombre, ps in sorted(por_campo.items()):
        st.markdown(f"#### 📍 {campo_nombre}")
        cols = st.columns(min(len(ps), 4))
        for i, p in enumerate(ps):
            hora   = p.get("hora") or "–"
            local  = p["nombre_local"]
            visit  = p["nombre_visitante"]
            torneo = p["nombre_torneo"]
            grupo  = p["nombre_grupo"]
            res_l  = p.get("resultado_local")
            res_v  = p.get("resultado_visitante")

            if res_l is not None and res_v is not None:
                marcador = f"{res_l} – {res_v}"
                marcador_html = f'<span style="color:#cc0000;font-weight:700;font-size:1rem;">{marcador}</span>'
            else:
                marcador_html = '<span style="color:#999;font-size:0.85rem;">vs</span>'

            cols[i % 4].markdown(
                f"""<div style="background:#ffffff;border:1px solid #d0d0d0;border-left:4px solid #cc0000;
                border-radius:4px;padding:10px 12px;margin-bottom:8px;font-size:0.83rem;line-height:1.6;">
                <div style="font-weight:700;font-size:0.95rem;color:#1a1a1a;">🕐 {hora}</div>
                <div style="margin:4px 0;">{local}</div>
                <div style="margin:2px 0;">{marcador_html}</div>
                <div style="margin:0 0 4px 0;">{visit}</div>
                <div style="font-size:0.72rem;color:#aaaaaa;">{torneo} · {grupo}</div>
                </div>""",
                unsafe_allow_html=True,
            )

# -------------------------------------------------------
# SORTEO
# -------------------------------------------------------
if menu == "Sorteo":
    seccion_sorteo_manual(supabase, torneo_id)