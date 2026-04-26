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
    """Devuelve todos los torneos ordenados por fecha de creación."""
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


def subir_equipos_batch(lista_equipos, torneo_id):
    """
    lista_equipos: lista de dicts [{'nombre': '...', 'escudo_url': '...'}, ...]
    Añade torneo_id a cada uno antes de insertar.
    """
    supabase = get_supabase()
    try:
        equipos_con_torneo = [{**e, "torneo_id": torneo_id} for e in lista_equipos]
        response = supabase.table("equipos").insert(equipos_con_torneo).execute()
        return response
    except Exception as e:
        return f"Error: {e}"


# -------------------------------------------------------
# FASES
# -------------------------------------------------------

def get_fases(torneo_id):
    """Devuelve las fases de un torneo ordenadas por 'orden'."""
    supabase = get_supabase()
    return (
        supabase.table("fases")
        .select("*")
        .eq("torneo_id", torneo_id)
        .order("orden")
        .execute()
        .data
    )


# -------------------------------------------------------
# GRUPOS
# -------------------------------------------------------

def get_grupos_por_fase(fase_id):
    """Devuelve todos los grupos de una fase dada."""
    supabase = get_supabase()
    return supabase.table("grupos").select("*").eq("fase_id", fase_id).execute().data


# -------------------------------------------------------
# PARTICIPANTES
# -------------------------------------------------------

def get_participantes_grupo(grupo_id):
    """Devuelve los participantes de un grupo, con datos del equipo anidados."""
    supabase = get_supabase()
    return (
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )
