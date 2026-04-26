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
)
from src.logic import seccion_sorteo_manual
from src.components import renderizar_tarjetas_equipos, mostrar_grupo_tv

# --- Constantes ---
LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"

# --- Configuración de página (solo una vez) ---
st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

# --- Cliente Supabase único ---
supabase = get_supabase()

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
# SELECTOR DE TORNEO (sidebar)
# -------------------------------------------------------
st.sidebar.markdown("## 🏆 Torneo")

torneos = get_torneos()

if not torneos:
    st.sidebar.info("No hay torneos. Crea uno primero.")
    torneo_actual = None
else:
    nombres_torneos = [t["nombre"] for t in torneos]

    # Persistir selección en session_state
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

# -------------------------------------------------------
# NAVEGACIÓN
# -------------------------------------------------------
menu = st.sidebar.selectbox(
    "Menú",
    ["Torneos", "Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual", "Sorteo"],
)

# -------------------------------------------------------
# TORNEOS
# -------------------------------------------------------
if menu == "Torneos":
    st.subheader("Gestión de Torneos")

    with st.expander("➕ Crear Nuevo Torneo", expanded=not torneos):
        nuevo_nombre = st.text_input("Nombre del torneo", placeholder="ej: Copa RFFM 2026")
        nueva_desc   = st.text_input("Descripción (opcional)")
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

# Guard: el resto de secciones requieren un torneo seleccionado
if menu != "Torneos":
    if not torneo_actual:
        st.warning("Selecciona o crea un torneo en el sidebar para continuar.")
        st.stop()
    torneo_id = torneo_actual["id"]
    st.caption(f"🏆 Torneo activo: **{torneo_actual['nombre']}**")

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
    renderizar_tarjetas_equipos(equipos)

# -------------------------------------------------------
# CARGA DE EQUIPOS
# -------------------------------------------------------
if menu == "Carga de Equipos":
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
                supabase.table("fases").insert({
                    "nombre": nueva_fase_nombre,
                    "orden": orden_fase,
                    "torneo_id": torneo_id,
                }).execute()
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
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                num_grupos = st.number_input("Añadir N grupos", min_value=1, value=1)
            with col2:
                tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
            with col3:
                st.write("Acción")
                if st.button("➕ Añadir"):
                    try:
                        res_conteo = (
                            supabase.table("grupos")
                            .select("id", count="exact")
                            .eq("fase_id", fase_id)
                            .execute()
                        )
                        total_existentes = res_conteo.count or 0
                        nuevos_grupos = [
                            {
                                "fase_id": fase_id,
                                "nombre": f"{fase_actual['nombre']} {total_existentes + i + 1}",
                                "tipo_grupo": tamano_grupo,
                            }
                            for i in range(num_grupos)
                        ]
                        supabase.table("grupos").insert(nuevos_grupos).execute()
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

                    from src.components import configurar_progresion_visual
                    configurar_progresion_visual(
                        grupos_destino=grupos,
                        grupos_origen=grupos_fase_anterior,
                        supabase=supabase,
                    )

                total_plazas = sum(g["tipo_grupo"] for g in grupos)
                st.info(f"Capacidad total de la fase: {total_plazas} equipos.")

            fase_siguiente = next(
                (f for f in fases if f["orden"] == fase_actual["orden"] + 1), None
            )
            if fase_siguiente:
                grupos_sig = get_grupos_por_fase(fase_siguiente["id"])
                if grupos and grupos_sig:
                    st.write("---")
                    st.write("### 🏆 Conexión al cuadro bracket")
                    st.caption(
                        f"Define a qué grupo de **{fase_siguiente['nombre']}** avanza "
                        f"el ganador de cada grupo de **{fase_actual['nombre']}**."
                    )
                    opciones_sig = {g["nombre"]: g["id"] for g in grupos_sig}
                    for g in grupos:
                        actual_sig_id = g.get("siguiente_grupo_id")
                        actual_sig_nombre = next(
                            (gs["nombre"] for gs in grupos_sig if gs["id"] == actual_sig_id), None
                        )
                        idx = list(opciones_sig.keys()).index(actual_sig_nombre) + 1 if actual_sig_nombre else 0
                        sel = st.selectbox(
                            f"Ganador de **{g['nombre']}** → va a:",
                            ["— sin asignar —"] + list(opciones_sig.keys()),
                            index=idx,
                            key=f"sig_{g['id']}",
                        )
                        nuevo_sig_id = opciones_sig.get(sel) if sel != "— sin asignar —" else None
                        if nuevo_sig_id != actual_sig_id:
                            try:
                                supabase.table("grupos").update(
                                    {"siguiente_grupo_id": nuevo_sig_id}
                                ).eq("id", g["id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar: {e}")

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

        grupos = get_grupos_por_fase(fase_id)
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

        from src.components import renderizar_tarjeta_grupo_minimalista, renderizar_cuadro_progresion

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
            grupos_fase_anterior = get_grupos_por_fase(fase_anterior["id"]) if fase_anterior else []
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
