import random
import streamlit as st
from src.database import get_supabase

def realizar_sorteo(fase_id, lista_grupos):
    supabase = get_supabase()
    
    # 1. Obtener todos los equipos que no estén eliminados
    equipos_res = supabase.table("equipos").select("id").eq("eliminado", False).execute()
    equipos = equipos_res.data
    
    if not equipos:
        st.error("No hay equipos cargados en la base de datos.")
        return

    # Mezclamos los equipos aleatoriamente
    random.shuffle(equipos)

    # 2. Limpiar sorteos anteriores de esta fase (opcional, para poder repetir)
    # Obtenemos los IDs de los grupos de esta fase
    ids_grupos = [g['id'] for g in lista_grupos]
    supabase.table("participantes_grupo").delete().in_("grupo_id", ids_grupos).execute()

    participantes = []
    equipo_idx = 0
    
    # 3. Ir repartiendo equipos en los huecos de los grupos
    for grupo in lista_grupos:
        # tipo_grupo nos dice cuántos equipos caben (2, 3, 4, 5...)
        for _ in range(grupo['tipo_grupo']):
            if equipo_idx < len(equipos):
                participantes.append({
                    "grupo_id": grupo['id'],
                    "equipo_id": equipos[equipo_idx]['id'],
                    "puntos": 0,
                    "goles": 0
                })
                equipo_idx += 1
    
    # 4. Inserción masiva en Supabase
    if participantes:
        try:
            supabase.table("participantes_grupo").insert(participantes).execute()
            st.success(f"✅ ¡Sorteo completado! Se han asignado {equipo_idx} equipos.")
        except Exception as e:
            st.error(f"Error al guardar el sorteo: {e}")
