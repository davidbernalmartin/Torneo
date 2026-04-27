import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# -------------------------------------------------------
# TORNEOS
# -------------------------------------------------------

def get_torneos():
    supabase = get_supabase()
    return supabase.table("torneos").select("*").order("created_at").execute().data


def crear_torneo(nombre, descripcion=""):
    supabase = get_supabase()
    return supabase.table("torneos").insert({
        "nombre": nombre,
        "descripcion": descripcion,
        "activo": True,
    }).execute().data


def eliminar_torneo(torneo_id):
    supabase = get_supabase()
    supabase.table("torneos").delete().eq("id", torneo_id).execute()


# -------------------------------------------------------
# EQUIPOS
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_equipos(torneo_id):
    supabase = get_supabase()
    return (
        supabase.table("equipos")
        .select("*")
        .eq("torneo_id", torneo_id)
        .order("nombre")
        .execute()
        .data
    )


def get_equipos_libres(torneo_id, ocupados_ids=None):
    supabase = get_supabase()
    equipos = (
        supabase.table("equipos")
        .select("id, nombre")
        .eq("eliminado", False)
        .eq("torneo_id", torneo_id)
        .execute()
        .data
    )
    if ocupados_ids:
        equipos = [e for e in equipos if e["id"] not in ocupados_ids]
    return equipos


def subir_equipos_batch(lista_equipos, torneo_id):
    supabase = get_supabase()
    try:
        equipos_con_torneo = [{**e, "torneo_id": torneo_id} for e in lista_equipos]
        result = supabase.table("equipos").insert(equipos_con_torneo).execute()
        st.cache_data.clear()
        return result
    except Exception as e:
        return f"Error: {e}"


# -------------------------------------------------------
# FASES
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_fases(torneo_id):
    supabase = get_supabase()
    return (
        supabase.table("fases")
        .select("*")
        .eq("torneo_id", torneo_id)
        .order("orden")
        .execute()
        .data
    )


def crear_fase(nombre, orden, torneo_id):
    supabase = get_supabase()
    result = supabase.table("fases").insert({
        "nombre": nombre,
        "orden": orden,
        "torneo_id": torneo_id,
    }).execute().data
    st.cache_data.clear()
    return result


# -------------------------------------------------------
# GRUPOS
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_grupos_por_fase(fase_id):
    supabase = get_supabase()
    return supabase.table("grupos").select("*").eq("fase_id", fase_id).execute().data


def crear_grupos(grupos_list):
    supabase = get_supabase()
    result = supabase.table("grupos").insert(grupos_list).execute().data
    st.cache_data.clear()
    return result


def actualizar_grupo(grupo_id, nombre, tipo_grupo, orden_cuadro):
    supabase = get_supabase()
    supabase.table("grupos").update({
        "nombre": nombre,
        "tipo_grupo": tipo_grupo,
        "orden_cuadro": orden_cuadro,
    }).eq("id", grupo_id).execute()
    st.cache_data.clear()


def eliminar_grupo(grupo_id):
    supabase = get_supabase()
    # Romper FK auto-referencial antes de borrar
    supabase.table("grupos").update({"siguiente_grupo_id": None}).eq("siguiente_grupo_id", grupo_id).execute()
    supabase.table("participantes_grupo").delete().eq("grupo_id", grupo_id).execute()
    supabase.table("grupos").delete().eq("id", grupo_id).execute()
    st.cache_data.clear()


def contar_grupos_fase(fase_id):
    supabase = get_supabase()
    res = supabase.table("grupos").select("id", count="exact").eq("fase_id", fase_id).execute()
    return res.count or 0


# -------------------------------------------------------
# PARTICIPANTES
# -------------------------------------------------------

def get_participantes_grupo(grupo_id):
    supabase = get_supabase()
    return (
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )


def get_participantes_grupos(ids_grupos):
    supabase = get_supabase()
    return (
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .in_("grupo_id", ids_grupos)
        .execute()
        .data
    )