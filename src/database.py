import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# -------------------------------------------------------
# EQUIPOS
# -------------------------------------------------------

def get_equipos():
    supabase = get_supabase()
    response = supabase.table("equipos").select("*").order("nombre").execute()
    return response.data


def subir_equipos_batch(lista_equipos):
    """
    lista_equipos: lista de dicts [{'nombre': '...', 'escudo_url': '...'}, ...]
    Devuelve el response de Supabase o un string de error.
    """
    supabase = get_supabase()
    try:
        response = supabase.table("equipos").insert(lista_equipos).execute()
        return response
    except Exception as e:
        return f"Error: {e}"


# -------------------------------------------------------
# FASES
# -------------------------------------------------------

def get_fases():
    """Devuelve todas las fases ordenadas por su campo 'orden'."""
    supabase = get_supabase()
    return supabase.table("fases").select("*").order("orden").execute().data


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
