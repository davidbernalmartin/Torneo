import re
import random
import streamlit as st
from collections import Counter

from src.database import get_supabase, get_fases, get_grupos_por_fase


# -------------------------------------------------------
# SORTEO AUTOMÁTICO
# -------------------------------------------------------

def realizar_sorteo(fase_id, lista_grupos, torneo_id):
    """
    Reparte aleatoriamente los equipos no eliminados entre los grupos de la fase.
    Borra primero los participantes existentes en esos grupos (limpieza de seguridad).
    """
    supabase = get_supabase()

    equipos = (
        supabase.table("equipos")
        .select("id")
        .eq("eliminado", False)
        .eq("torneo_id", torneo_id)
        .execute()
        .data
    )
    random.shuffle(equipos)

    ids_grupos = [g["id"] for g in lista_grupos]
    supabase.table("participantes_grupo").delete().in_("grupo_id", ids_grupos).execute()

    participantes = []
    equipo_idx = 0

    for grupo in lista_grupos:
        for _ in range(grupo["tipo_grupo"]):
            if equipo_idx < len(equipos):
                participantes.append({
                    "grupo_id": grupo["id"],
                    "equipo_id": equipos[equipo_idx]["id"],
                    "puntos": 0,
                    "goles": 0,
                })
                equipo_idx += 1
            else:
                break

    if participantes:
        supabase.table("participantes_grupo").insert(participantes).execute()


# -------------------------------------------------------
# SECCIÓN SORTEO MANUAL (componente de página)
# -------------------------------------------------------

def seccion_sorteo_manual(supabase, torneo_id=None):
    """
    Gestiona el sorteo manual buscando automáticamente la fase de orden 1.
    """
    st.subheader("Mesa de Sorteo (Fase Inicial)")

    filtro_fase = supabase.table("fases").select("id, nombre").eq("orden", 1)
    if torneo_id:
        filtro_fase = filtro_fase.eq("torneo_id", torneo_id)
    res_fase = filtro_fase.execute()

    if not res_fase.data:
        st.error("No se ha encontrado ninguna fase con orden 1 en la base de datos.")
        return

    fase_inicial = res_fase.data[0]
    fase_id = fase_inicial["id"]
    st.caption(f"Configurando sorteo para: **{fase_inicial['nombre']}**")

    res_grupos = (
        supabase.table("grupos")
        .select("id, nombre, tipo_grupo")
        .eq("fase_id", fase_id)
        .execute()
    )
    def _num(n):
        m = re.search(r"\d+", n)
        return int(m.group()) if m else 0
    todos_los_grupos = sorted(res_grupos.data, key=lambda g: _num(g["nombre"]))
    ids_grupos = [g["id"] for g in todos_los_grupos]

    res_p = (
        supabase.table("participantes_grupo")
        .select("grupo_id, equipo_id")
        .in_("grupo_id", ids_grupos)
        .execute()
    )
    # Solo contar filas con equipo_id real (no NULL)
    asignados_ids = [p["equipo_id"] for p in res_p.data if p["equipo_id"]]
    ocupacion_actual = Counter([
        p["grupo_id"] for p in res_p.data if p["equipo_id"]
    ])

    grupos_disponibles = []
    for g in todos_los_grupos:
        actual = ocupacion_actual.get(g["id"], 0)
        if actual < g["tipo_grupo"]:
            g["plazas_libres"] = g["tipo_grupo"] - actual
            grupos_disponibles.append(g)

    eq_query = supabase.table("equipos").select("id, nombre")
    if torneo_id:
        eq_query = eq_query.eq("torneo_id", torneo_id)
    res_e = eq_query.execute()
    equipos_libres = [e for e in res_e.data if e["id"] not in asignados_ids]

    if not equipos_libres:
        st.success("¡Sorteo completado! Todos los equipos están en sus grupos.")
        return

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        with c1:
            equipo_nombre = st.selectbox(
                "Equipo:", [""] + [e["nombre"] for e in equipos_libres]
            )
        with c2:
            opciones_grupos = [""] + [
                f"{g['nombre']} ({g['plazas_libres']} huecos)" for g in grupos_disponibles
            ]
            indice_defecto = 1 if len(opciones_grupos) > 1 else 0
            grupo_sel_display = st.selectbox(
                "Grupo:", opciones_grupos, index=indice_defecto
            )
        with c3:
            if st.button("Confirmar", use_container_width=True, type="primary"):
                if equipo_nombre and grupo_sel_display:
                    nombre_grupo_limpio = grupo_sel_display.split(" (")[0]
                    e_match = next((e for e in equipos_libres if e["nombre"] == equipo_nombre), None)
                    g_match = next((g for g in grupos_disponibles if g["nombre"] == nombre_grupo_limpio), None)
                    if not e_match or not g_match:
                        st.error("Los datos han cambiado. Recarga la página e inténtalo de nuevo.")
                    else:
                        id_e, id_g = e_match["id"], g_match["id"]
                        try:
                            # Buscar si existe una plaza vacía (equipo_id NULL) en este grupo
                            plaza_vacia = supabase.table("participantes_grupo")                             .select("id")                             .eq("grupo_id", id_g)                             .is_("equipo_id", "null")                             .limit(1)                             .execute()

                            if plaza_vacia.data:
                                # Actualizar la primera plaza vacía existente
                                supabase.table("participantes_grupo")                                 .update({"equipo_id": id_e, "puntos": 0, "goles": 0})                                 .eq("id", plaza_vacia.data[0]["id"])                                 .execute()
                            else:
                                # Insertar nueva fila si no hay plazas vacías preexistentes
                                supabase.table("participantes_grupo").insert({
                                    "grupo_id": id_g,
                                    "equipo_id": id_e,
                                    "puntos": 0,
                                    "goles": 0,
                                }).execute()
                            st.toast(f"Asignado: {equipo_nombre} al {nombre_grupo_limpio}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al confirmar asignación: {e}")

    if not grupos_disponibles:
        st.warning("⚠️ No quedan grupos con plazas disponibles. Revisa la configuración de la fase.")

    st.info(f"Faltan por asignar **{len(equipos_libres)}** equipos.")
