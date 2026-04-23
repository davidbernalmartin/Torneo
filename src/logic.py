import random
import streamlit as st
from src.database import get_supabase

def realizar_sorteo(fase_id, lista_grupos):
    supabase = get_supabase()
    
    # 1. Traemos solo los equipos que no están eliminados
    equipos = supabase.table("equipos").select("id").eq("eliminado", False).execute().data
    random.shuffle(equipos)

    # 2. Limpieza de seguridad
    ids_grupos = [g['id'] for g in lista_grupos]
    supabase.table("participantes_grupo").delete().in_("grupo_id", ids_grupos).execute()

    participantes = []
    equipo_idx = 0
    
    # 3. Lógica de llenado
    for grupo in lista_grupos:
        for _ in range(grupo['tipo_grupo']):
            if equipo_idx < len(equipos):
                participantes.append({
                    "grupo_id": grupo['id'],
                    "equipo_id": equipos[equipo_idx]['id'],
                    "puntos": 0,
                    "goles": 0
                })
                equipo_idx += 1
            else:
                break # No hay más equipos para repartir
