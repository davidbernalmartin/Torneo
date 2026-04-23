import streamlit as st
from src.database import get_supabase
import time

def renderizar_tarjeta_grupo(grupo, participantes):
    """
    Dibuja un solo grupo con sus participantes o huecos vacíos.
    """
    with st.container():
        # Cabecera: Nombre del grupo + Botón para TV (solo si no estamos en modo TV)
        col_t, col_b = st.columns([0.7, 0.3])
        col_t.markdown(f"### 📋 {grupo['nombre']}")
        
        # El link para la TV usando el nombre como parámetro
        url_tv = f"/?view=tv&grupo={grupo['nombre']}"
        col_b.link_button("📺 TV", url_tv, use_container_width=True)

        # Renderizar la lista
        for i in range(grupo['tipo_grupo']):
            if i < len(participantes):
                p = participantes[i]
                escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else "https://via.placeholder.com/30"
                nombre = p['equipos']['nombre']
                st.markdown(
                    f"""<div style="display: flex; align-items: center; padding: 5px; border-bottom: 1px solid #333;">
                        <img src="{escudo}" style="width: 25px; margin-right: 10px;">
                        <span>{nombre}</span>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"""<div style="padding: 5px; color: #666; font-style: italic; border-bottom: 1px solid #333; border-left: 3px dashed #444;">
                        👤 Esperando equipo...
                    </div>""", unsafe_allow_html=True)
        st.write("") # Espacio

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
