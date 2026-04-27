import io
import re as _re
import urllib.parse

import streamlit as st
import pandas as pd

from src.database import (
    get_supabase,
    get_torneos,
    crear_torneo,
    eliminar_torneo,
    get_equipos,
    subir_equipos_batch,
    get_fases,
    get_grupos_por_fase,
    get_participantes_grupo,
    crear_fase,
    crear_grupos,
    contar_grupos_fase,
    actualizar_grupo,
    eliminar_grupo,
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
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a0000", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- Constantes ---
LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"

# --- Configuración de página (solo una vez) ---
st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

# CSS global — corrige colores de alertas, botones y bordes de focus
st.markdown("""
<style>
/* Botones primarios — negro, legible sobre cualquier fondo */
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background-color: #1a1a1a !important;
    color: white !important;
    border: none !important;
}
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background-color: #333 !important;
    color: white !important;
}
/* Info/warning/success boxes — fondo oscuro, texto blanco */
div[data-testid="stNotification"] {
    background-color: rgba(0,0,0,0.25) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}
div[data-testid="stNotification"] p,
div[data-testid="stNotification"] li {
    color: white !important;
}
/* Quitar borde cyan de focus */
div[data-baseweb] *:focus {
    outline: none !important;
    box-shadow: none !important;
}
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: rgba(255,255,255,0.5) !important;
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
    /* Botón Entrar — negro sobre blanco para máximo contraste */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #1a1a1a !important;
        color: white !important;
        border: none !important;
    }
    div[data-testid="stForm"] button:hover {
        background-color: #333 !important;
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
                <h2 style="margin:0;font-size:1.5rem;text-align:center;color:white;">Gestión de Campeonato RFFM</h2>
                <p style="color:rgba(255,255,255,0.7);margin:0;font-size:0.9rem;">Acceso restringido</p>
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
    """Ordena grupos numéricamente por el número en su nombre."""
    def _num(n):
        m = _re.search(r"\d+", n)
        return int(m.group()) if m else 0
    return sorted(grupos, key=lambda g: _num(g["nombre"]))

# -------------------------------------------------------
# MODO TV
# -------------------------------------------------------
query_params = st.query_params

if "view" in query_params and query_params["view"] == "tv":
    grupo_id_url = query_params.get("grupo")
    torneo_id_tv = query_params.get("torneo")

    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            .main {background-color: #0e1117; color: white;}
            h1, h2, h3 {text-align: center; font-size: 4rem !important;}
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
    ["Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual", "Sorteo", "Ajustes"],
)

# -------------------------------------------------------
# AJUSTES
# -------------------------------------------------------
if menu == "Ajustes":
    st.subheader("Ajustes de Torneos")

    if torneos:
        st.write("### Torneos existentes")
        for t in torneos:
            col_n, col_d, col_b = st.columns([3, 4, 1])
            col_n.markdown(f"**{t['nombre']}**")
            col_d.caption(t.get("descripcion") or "—")
            with st.expander(f"Enlaces — {t['nombre']}"):
                tid = t["id"]
                url_gestion = f"bracket.html?torneo={tid}"
                url_vista   = f"bracket-view.html?torneo={tid}"

                st.markdown("**Bracket dinámico** (gestión):")
                st.code(url_gestion, language=None)

                st.markdown("**Bracket de consulta** (solo lectura):")
                st.code(url_vista, language=None)

                # Vista TV — obtener grupos de la fase 1 de este torneo
                fases_torneo = supabase.table("fases").select("id").eq("torneo_id", tid).eq("orden", 1).execute().data
                grupos_tv = []
                if fases_torneo:
                    grupos_tv = sorted(
                        supabase.table("grupos").select("nombre").eq("fase_id", fases_torneo[0]["id"]).execute().data,
                        key=lambda g: int(m.group()) if (m := _re.search(r"\d+", g["nombre"])) else 0
                    )
                if grupos_tv:
                    primer_grupo = grupos_tv[0]["nombre"]
                    url_tv = f"/?view=tv&grupo={urllib.parse.quote(primer_grupo)}&torneo={tid}"
                    st.markdown("**Vista TV** (pantalla de sorteo):")
                    col_tv_url, col_tv_btn = st.columns([4, 1])
                    col_tv_url.code(url_tv, language=None)
                    col_tv_btn.link_button("Abrir", url_tv, use_container_width=True)

                st.markdown("---")
                col_qr1, col_qr2 = st.columns(2)
                with col_qr1:
                    if st.button("QR — Vista pública", key=f"qr_view_{tid}", use_container_width=True):
                        st.session_state[f"show_qr_{tid}"] = "view"
                with col_qr2:
                    if st.button("QR — Gestión", key=f"qr_gest_{tid}", use_container_width=True):
                        st.session_state[f"show_qr_{tid}"] = "gest"

                qr_mode = st.session_state.get(f"show_qr_{tid}")
                if qr_mode:
                    qr_url  = url_vista if qr_mode == "view" else url_gestion
                    qr_label = "Vista pública" if qr_mode == "view" else "Gestión"
                    try:
                        qr_bytes = generar_qr(qr_url).getvalue()
                        col_img, col_txt = st.columns([1, 2])
                        with col_img:
                            st.image(qr_bytes, width=160)
                        with col_txt:
                            st.markdown(f"**{t['nombre']}**")
                            st.caption(f"{qr_label}")
                            st.caption(qr_url)
                            st.download_button(
                                "Descargar QR",
                                data=qr_bytes,
                                file_name=f"qr_{t['nombre'].replace(' ','_')}_{qr_mode}.png",
                                mime="image/png",
                                key=f"dl_qr_{tid}_{qr_mode}",
                            )
                    except Exception as e:
                        st.error(f"Error generando QR: {e}. Asegúrate de tener instalado qrcode[pil]")
            if col_b.button("🗑️", key=f"del_{t['id']}", help="Eliminar torneo y todos sus datos"):
                st.session_state[f"confirm_del_{t['id']}"] = True

            if st.session_state.get(f"confirm_del_{t['id']}", False):
                st.warning(
                    f"¿Eliminar **{t['nombre']}** y TODOS sus datos (fases, grupos, equipos)? "
                    "Esta acción no se puede deshacer."
                )
                c1, c2 = st.columns(2)
                if c1.button("Sí, eliminar", key=f"si_del_{t['id']}", type="primary"):
                    try:
                        eliminar_torneo(t["id"])
                        st.session_state.pop(f"confirm_del_{t['id']}", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                c2.button(
                    "Cancelar",
                    key=f"no_del_{t['id']}",
                    on_click=st.session_state.pop,
                    args=[f"confirm_del_{t['id']}", None],
                )

# Guard: todas las secciones requieren un torneo seleccionado
if not torneo_actual:
    st.warning("Selecciona o crea un torneo en el sidebar para continuar.")
    st.stop()
    torneo_id = torneo_actual["id"]
    st.caption(f"Torneo activo: **{torneo_actual['nombre']}**")

# -------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------
if menu == "Dashboard":
    equipos = get_equipos(torneo_id)
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e["eliminado"]]))

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
# CARGA DE EQUIPOS
# -------------------------------------------------------
if menu == "Carga de Equipos":
    st.subheader("Importación Masiva de Equipos")

    archivo = st.file_uploader("Sube tu Excel o CSV", type=["xlsx", "csv"])

    # ── Plantilla descargable ────────────────────────────
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
        # ── Lectura del fichero ───────────────────────────
        try:
            if archivo.name.endswith("xlsx"):
                df = pd.read_excel(archivo)
            else:
                df = pd.read_csv(archivo)
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")
            st.info("Asegúrate de que el archivo no está corrupto y es un Excel o CSV válido.")
            df = None

        if df is not None:
            st.write("### Vista previa del archivo")
            st.dataframe(df, use_container_width=True)

            # ── Validación de columnas ────────────────────
            tiene_nombre   = "nombre"     in df.columns
            tiene_escudo   = "escudo_url" in df.columns

            if not tiene_nombre or not tiene_escudo:
                faltantes = []
                if not tiene_nombre: faltantes.append("`nombre`")
                if not tiene_escudo: faltantes.append("`escudo_url`")

                st.error(f"Faltan las columnas obligatorias: {', '.join(faltantes)}")

                cols_encontradas = [f"`{c}`" for c in df.columns.tolist()]
                st.markdown(
                    f"**Columnas encontradas en tu archivo:** {', '.join(cols_encontradas) if cols_encontradas else '_(ninguna)_'}\n\n"
                    f"**Columnas requeridas:** `nombre`, `escudo_url`\n\n"
                    "Revisa que la primera fila del archivo contiene exactamente esos nombres (en minúsculas y sin espacios extra). "
                    "Despliega el panel de arriba para ver el formato correcto y descargar una plantilla."
                )

            elif df["nombre"].isna().all() or df.empty:
                st.error("El archivo está vacío o la columna `nombre` no tiene datos.")

            else:
                # ── Happy path ────────────────────────────
                nombres_existentes = {e["nombre"].strip().upper() for e in get_equipos(torneo_id)}
                df["_nuevo"] = ~df["nombre"].str.strip().str.upper().isin(nombres_existentes)
                duplicados  = df[~df["_nuevo"]]["nombre"].tolist()
                df_nuevos   = df[df["_nuevo"]].drop(columns=["_nuevo"])

                if duplicados:
                    st.warning(f"⚠️ Ya existen en el torneo y se omitirán: **{', '.join(duplicados)}**")

                if df_nuevos.empty:
                    st.error("Todos los equipos del archivo ya existen en el torneo. No hay nada que subir.")
                else:
                    label = f"Confirmar y subir {len(df_nuevos)} equipo(s)" if duplicados else "Confirmar y subir a Supabase"
                    if st.button(label):
                        equipos_dict = df_nuevos[["nombre", "escudo_url"]].to_dict(orient="records")
                        with st.spinner(f"Subiendo {len(equipos_dict)} equipos..."):
                            resultado = subir_equipos_batch(equipos_dict, torneo_id)
                        if isinstance(resultado, str):
                            st.error(resultado)
                        else:
                            st.success(f"¡{len(equipos_dict)} equipos cargados con éxito!")
                            st.rerun()

    st.write("---")
    st.subheader("Equipos actualmente en la Base de Datos")
    renderizar_tarjetas_equipos(get_equipos(torneo_id))

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

        todos_participantes = []
        if ids_grupos:
            try:
                todos_participantes = (
                    supabase.table("participantes_grupo")
                    .select("*, equipos(id, nombre, escudo_url)")
                    .in_("grupo_id", ids_grupos)
                    .execute()
                ).data
            except Exception as e:
                st.error(f"Error cargando participantes: {e}")

        participantes_por_grupo: dict = {}
        for p in todos_participantes:
            participantes_por_grupo.setdefault(p["grupo_id"], []).append(p)



        if not es_progresion:
            equipos_libres = []
            try:
                res_eq = (
                    supabase.table("equipos")
                    .select("id, nombre")
                    .eq("eliminado", False)
                    .eq("torneo_id", torneo_id)
                    .execute()
                )
                ocupados_ids = {p["equipo_id"] for p in todos_participantes if p["equipo_id"]}
                equipos_libres = [e for e in res_eq.data if e["id"] not in ocupados_ids]
            except Exception as e:
                st.error(f"Error cargando equipos libres: {e}")

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

            participantes_fase_ant = []
            if ids_grupos_ant:
                try:
                    participantes_fase_ant = (
                        supabase.table("participantes_grupo")
                        .select("*, equipos(id, nombre, escudo_url)")
                        .in_("grupo_id", ids_grupos_ant)
                        .execute()
                    ).data
                except Exception as e:
                    st.error(f"Error cargando fase anterior: {e}")

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
# SORTEO
# -------------------------------------------------------
if menu == "Sorteo":
    seccion_sorteo_manual(supabase, torneo_id)