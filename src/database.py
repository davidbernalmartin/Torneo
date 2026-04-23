import streamlit as st
from supabase import create_client, Client

# Conexión usando los secretos de Streamlit
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_equipos():
    supabase = get_supabase()
    # Traemos todos los equipos ordenados por nombre
    response = supabase.table("equipos").select("*").order("nombre").execute()
    return response.data
