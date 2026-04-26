import streamlit as st
import pandas as pd

from src.database import (
    get_torneos,
    crear_torneo,
    eliminar_torneo,
    get_equipos,
    get_equipos_libres,
    subir_equipos_batch,
    get_fases,
    get_grupos_por_fase,
    get_participantes_grupos,
    crear_fase,
    crear_grupos,
    contar_grupos_fase,
)
from src.logic import seccion_sorteo_manual
from src.components import (
    renderizar_tarjetas_equipos,
    mostrar_grupo_tv,
    configurar_progresion_visual,
    renderizar_tarjeta_grupo_minimalista,
    renderizar_cuadro_progresion,
)

LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"

st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")


# -------------------------------------------------------
# AUTENTICACIÓN
# -------------------------------------------------------

def check_login():
    if st.session_state.get("authenticated"):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:24px;">
                <img src="{LOGO_RFFM_URL}" style="width:80px;margin-bottom:12px;">
                <h2 style="margin:0;font-size:1.5rem;text-align:center;">Gestión de Campeonato RFFM</h2>
                <p style="color:#888;margin:0;">Acceso restringido</p>
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


# -------------------------------------------------------
# MODO TV
# -------------------------------------------------------

query_params = st.query_params

if "view" in query_params and query_params["view"] == "tv":
    grupo_id_url = query_params.get("grupo")

    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            .main {background-color: #0e1117; color: white;}
            h1, h2, h3 {text-align: center; font-size: 4rem !important;}
        </style>
    """, unsafe_allow_html=True)

    if grupo_id_url:
        mostrar_grupo_tv(grupo_id_url)
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
# SIDEBAR: logout + selector de torneo + menú
# -------------------------------------------------------

if st.sidebar.button("🔒 Cerrar sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🏆 Torneo")

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
    torneo_actual = next(t for t in torneos if t["nombre"] == torneo_sel)

st.sidebar.markdown("---")

menu = st.sidebar.selectbox(
    "Menú",
    ["Torneos", "Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual", "Sorteo"],
)


# -------------------------------------------------------
# SECCIONES
# -------------------------------------------------------

def seccion_torneos():
    st.subheader("Gestión de Torneos")

    with st.expander("➕ Crear Nuevo Torneo", expanded=not torneos):
        nuevo_nombre = st.text_input("Nombre del torneo", placeholder="ej: Copa RFFM 2026")
        nueva_desc = st.text_input("Descripción (opcional)")
        if st.button("Crear torneo"):
            if nuevo_nombre.strip():
                try:
                    crear_torneo(nuevo_nombre.strip(), nueva_desc.strip())
                    st.success(f"Torneo '{nuevo_nombre}' creado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("El nombre no puede estar vacío.")

    if torneos:
        st.write("### Torneos existentes")
        for t in torneos:
            col_n, col_d, col_b = st.columns([3, 4, 1])
            col_n.markdown(f"**{t['nombre']}**")
            col_d.caption(t.get("descripcion") or "—")
            with st.expander(f"🔗 Enlaces — {t['nombre']}"):
                tid = t["id"]
                st.markdown("**Bracket dinámico** (gestión):")
                st.code(f"bracket.html?torneo={tid}", language=None)
                st.markdown("**Bracket de consulta** (solo lectura):")
                st.code(f"bracket-view.html?torneo={tid}", language=None)
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
                if c2.button("Cancelar", key=f"no_del_{t['id']}"):
                    st.session_state.pop(f"confirm_del_{t['id']}", None)
                    st.rerun()


def seccion_dashboard(torneo_id):
    equipos = get_equipos(torneo_id)
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e["eliminado"]]))

    st.write("---")
    st.subheader("Plantilla de Equipos")
    renderizar_tarjetas_equipos(equipos)


def seccion_carga_equipos(torneo_id):
    st.subheader("Importación Masiva de Equipos")

    archivo = st.file_uploader("Sube tu Excel o CSV", type=["xlsx", "csv"])

    if archivo:
        if archivo.name.endswith("xlsx"):
            df = pd.read_excel(archivo)
        else:
            df = pd.read_csv(archivo)

        st.write("### Vista previa de tus equipos")
        st.dataframe(df, use_container_width=True)

        columnas_ok = "nombre" in df.columns and "escudo_url" in df.columns

        if columnas_ok:
            if st.button("Confirmar y subir a Supabase"):
                equipos_dict = df[["nombre", "escudo_url"]].to_dict(orient="records")
                n = len(equipos_dict)

                with st.spinner(f"Subiendo {n} equipos..."):
                    resultado = subir_equipos_batch(equipos_dict, torneo_id)

                if isinstance(resultado, str):
                    st.error(resultado)
                else:
                    st.success(f"¡{n} equipos cargados con éxito!")
                    st.rerun()
        else:
            st.error("El archivo debe tener las columnas: 'nombre' y 'escudo_url'")

        st.write("---")
        st.subheader("Equipos actualmente en la Base de Datos")
        renderizar_tarjetas_equipos(get_equipos(torneo_id))


def seccion_configurador(torneo_id):
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
        return

    fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
    fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)

    if not fase_actual:
        return

    fase_id = fase_actual["id"]
    es_fase_progresion = fase_actual["orden"] > 1

    st.write("---")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        num_grupos = st.number_input("Añadir N grupos", min_value=1, value=1)
    with col2:
        tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
    with col3:
        st.write("Acción")
        if st.button("➕ Añadir"):
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
    grupos = get_grupos_por_fase(fase_id)

    if grupos:
        if not es_fase_progresion:
            st.info("Fase 1: las plazas se llenan por sorteo, no requiere configuración de origen.")
        else:
            fase_anterior = next(
                (f for f in fases if f["orden"] == fase_actual["orden"] - 1), None
            )
            grupos_fase_anterior = get_grupos_por_fase(fase_anterior["id"]) if fase_anterior else []
            configurar_progresion_visual(
                grupos_destino=grupos,
                grupos_origen=grupos_fase_anterior,
            )

        total_plazas = sum(g["tipo_grupo"] for g in grupos)
        st.info(f"Capacidad total de la fase: {total_plazas} equipos.")


def seccion_cuadro_visual(torneo_id):
    st.subheader("Gestión de Equipos por Grupo")

    fases = get_fases(torneo_id)

    if not fases:
        st.info("No hay fases configuradas.")
        return

    fase_sel = st.selectbox("Seleccionar Fase", [f["nombre"] for f in fases])
    fase_actual = next(f for f in fases if f["nombre"] == fase_sel)
    fase_id = fase_actual["id"]
    es_progresion = fase_actual["orden"] > 1

    grupos = get_grupos_por_fase(fase_id)
    ids_grupos = [g["id"] for g in grupos]

    todos_participantes = []
    if ids_grupos:
        try:
            todos_participantes = get_participantes_grupos(ids_grupos)
        except Exception as e:
            st.error(f"Error cargando participantes: {e}")

    participantes_por_grupo: dict = {}
    for p in todos_participantes:
        participantes_por_grupo.setdefault(p["grupo_id"], []).append(p)

    if not es_progresion:
        ocupados_ids = {p["equipo_id"] for p in todos_participantes if p["equipo_id"]}
        try:
            equipos_libres = get_equipos_libres(torneo_id, ocupados_ids)
        except Exception as e:
            st.error(f"Error cargando equipos libres: {e}")
            equipos_libres = []

        cols_grupos = st.columns(3)
        for idx, grupo in enumerate(grupos):
            participantes = participantes_por_grupo.get(grupo["id"], [])
            with cols_grupos[idx % 3]:
                renderizar_tarjeta_grupo_minimalista(
                    grupo=grupo,
                    participantes=participantes,
                    equipos_libres=equipos_libres,
                )
    else:
        fase_anterior = next(
            (f for f in fases if f["orden"] == fase_actual["orden"] - 1), None
        )
        grupos_fase_anterior = get_grupos_por_fase(fase_anterior["id"]) if fase_anterior else []
        ids_grupos_ant = [g["id"] for g in grupos_fase_anterior]

        participantes_fase_ant = []
        if ids_grupos_ant:
            try:
                participantes_fase_ant = get_participantes_grupos(ids_grupos_ant)
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
        )


# -------------------------------------------------------
# DESPACHO DEL MENÚ
# -------------------------------------------------------

if menu == "Torneos":
    seccion_torneos()
else:
    if not torneo_actual:
        st.warning("Selecciona o crea un torneo en el sidebar para continuar.")
        st.stop()

    torneo_id = torneo_actual["id"]
    st.caption(f"🏆 Torneo activo: **{torneo_actual['nombre']}**")

    if menu == "Dashboard":
        seccion_dashboard(torneo_id)
    elif menu == "Carga de Equipos":
        seccion_carga_equipos(torneo_id)
    elif menu == "Configurador":
        seccion_configurador(torneo_id)
    elif menu == "Cuadro Visual":
        seccion_cuadro_visual(torneo_id)
    elif menu == "Sorteo":
        seccion_sorteo_manual(torneo_id)
