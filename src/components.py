import streamlit as st
from src.database import get_supabase
import time

def renderizar_tarjetas_equipos(lista_equipos):
    if not lista_equipos:
        st.info("No hay equipos cargados todavía.")
        return
    cols = st.columns(3)
    for idx, equipo in enumerate(lista_equipos):
        col_actual = cols[idx % 3]
        with col_actual:
            st.markdown(
                f"""
                <div style="border: 1px solid #464e5f; border-radius: 10px; padding: 15px; 
                margin-bottom: 15px; background-color: #1a1c24; text-align: center; min-height: 180px;">
                    <img src="{equipo['escudo_url'] if equipo['escudo_url'] else 'https://via.placeholder.com/100'}" 
                         style="max-width: 80px; max-height: 80px; border-radius: 50%; margin-bottom: 10px;">
                    <div style="font-weight: bold; font-size: 1.1em; color: white;">{equipo['nombre']}</div>
                </div>
                """, unsafe_allow_html=True)

def renderizar_cuadro_vacio(lista_grupos):
    if not lista_grupos:
        st.info("No hay grupos configurados.")
        return
    cols_grupos = st.columns(2)
    for idx, grupo in enumerate(lista_grupos):
        col_actual = cols_grupos[idx % 2]
        with col_actual:
            st.markdown(f"### 📋 {grupo['nombre']}")
            for i in range(grupo['tipo_grupo']):
                st.markdown(
                    f"""<div style="border: 1px dashed #626771; border-radius: 5px; padding: 8px; 
                    margin-bottom: 5px; background-color: rgba(255, 255, 255, 0.05); color: #888;">
                    👤 Hueco Equipo {i+1}</div>""", unsafe_allow_html=True)

def mostrar_grupo_tv(grupo_id):
    supabase = get_supabase()
    
    # 1. Intentamos obtener los participantes con sus datos de equipo
    res = supabase.table("participantes_grupo")\
        .select("puntos, goles, equipos(nombre, escudo_url), grupos(nombre, tipo_grupo)")\
        .eq("grupo_id", grupo_id)\
        .order("puntos", desc=True).execute()
    
    # 2. Variable para el nombre del grupo (la sacamos de la respuesta o consultamos si está vacío)
    if res.data:
        nombre_grupo = res.data[0]['grupos']['nombre']
        participantes = res.data
        tipo_grupo = res.data[0]['grupos']['tipo_grupo']
    else:
        info_grupo = supabase.table("grupos").select("nombre, tipo_grupo").eq("id", grupo_id).single().execute()
        nombre_grupo = info_grupo.data['nombre'] if info_grupo.data else "Grupo"
        tipo_grupo = info_grupo.data['tipo_grupo'] if info_grupo.data else 0
        participantes = []

    # Título Gigante
    st.markdown(f"<h1 style='text-align: center; font-size: 5rem; margin-bottom: 20px;'>{nombre_grupo}</h1>", unsafe_allow_html=True)
    
    # 3. Construcción de la Tabla
    tabla_html = """
    <table style="width:100%; border-collapse: collapse; font-size: 2.8rem; color: white; font-family: sans-serif;">
        <tr style="border-bottom: 3px solid #444; background-color: #1f2937;">
            <th style="padding: 25px; text-align: left;">Equipo</th>
            <th style="padding: 25px; text-align: center; width: 150px;">PTS</th>
            <th style="padding: 25px; text-align: center; width: 150px;">GF</th>
        </tr>
    """

    if participantes:
        # Renderizar equipos reales
        for p in participantes:
            equipo = p['equipos']['nombre']
            escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else "https://via.placeholder.com/80"
            tabla_html += f"""
            <tr style="border-bottom: 1px solid #333;">
                <td style="padding: 25px; display: flex; align-items: center;">
                    <img src="{escudo}" style="width: 100px; height: 100px; margin-right: 30px; object-fit: contain;"> {equipo}
                </td>
                <td style="padding: 25px; text-align: center; font-weight: bold; color: #00e676;">{p['puntos']}</td>
                <td style="padding: 25px; text-align: center;">{p['goles']}</td>
            </tr>
            """
    else:
        # Renderizar "Huecos vacíos" si no hay sorteo
        for i in range(tipo_grupo):
            tabla_html += f"""
            <tr style="border-bottom: 1px solid #333; opacity: 0.5;">
                <td style="padding: 25px; display: flex; align-items: center; color: #888; font-style: italic;">
                    <div style="width: 100px; height: 100px; margin-right: 30px; border: 2px dashed #555; border-radius: 50%;"></div>
                    Esperando Equipo {i+1}...
                </td>
                <td style="padding: 25px; text-align: center;">--</td>
                <td style="padding: 25px; text-align: center;">--</td>
            </tr>
            """

    tabla_html += "</table>"
    st.markdown(tabla_html, unsafe_allow_html=True)

    # 4. Footer de actualización
    st.markdown(f"""
        <div style="position: fixed; bottom: 20px; right: 20px; color: #555; font-size: 1.2rem;">
            Actualización automática activa...
        </div>
    """, unsafe_allow_html=True)

    # 5. Auto-refresco cada 30 segundos
    time.sleep(30)
    st.rerun()
