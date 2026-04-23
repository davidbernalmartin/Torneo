import streamlit as st
import time
from src.database import get_supabase

def renderizar_tarjeta_grupo(grupo, participantes):
    """Vista para el Administrador (Cuadro Visual)"""
    with st.container():
        col_t, col_b = st.columns([0.7, 0.3])
        col_t.markdown(f"### 📋 {grupo['nombre']}")
        
        # El link para la TV usando el nombre como parámetro
        url_tv = f"/?view=tv&grupo={grupo['nombre']}"
        col_b.link_button("📺 TV", url_tv, use_container_width=True)

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
        st.write("")

def mostrar_grupo_tv(nombre_grupo_url):
    """Vista Gigante para la Televisión"""
    supabase = get_supabase()
    
    # 1. Buscamos el grupo por nombre
    info_grupo_res = supabase.table("grupos").select("id, nombre, tipo_grupo").eq("nombre", nombre_grupo_url).maybe_single().execute()
    
    if not info_grupo_res.data:
        st.error(f"Grupo '{nombre_grupo_url}' no encontrado.")
        return

    grupo_id = info_grupo_res.data['id']
    nombre_display = info_grupo_res.data['nombre']
    tipo_grupo = info_grupo_res.data['tipo_grupo']

    # 2. Buscamos participantes
    res_part = supabase.table("participantes_grupo").select("puntos, goles, equipos(nombre, escudo_url)").eq("grupo_id", grupo_id).order("puntos", desc=True).execute()
    participantes = res_part.data if res_part.data else []

    # RENDERIZADO GIGANTE
    st.markdown(f"<h1 style='text-align: center; font-size: 5rem; margin-bottom: 20px;'>{nombre_display}</h1>", unsafe_allow_html=True)
    
    tabla_html = """
    <table style="width:100%; border-collapse: collapse; font-size: 2.8rem; color: white; font-family: sans-serif;">
        <tr style="border-bottom: 3px solid #444; background-color: #1f2937;">
            <th style="padding: 25px; text-align: left;">Equipo</th>
            <th style="padding: 25px; text-align: center; width: 150px;">PTS</th>
            <th style="padding: 25px; text-align: center; width: 150px;">GF</th>
        </tr>
    """

    if participantes:
        for p in participantes:
            equipo = p['equipos']['nombre']
            escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else "https://via.placeholder.com/100"
            tabla_html += f"""
            <tr style="border-bottom: 1px solid #333;">
                <td style="padding: 25px; display: flex; align-items: center;">
                    <img src="{escudo}" style="width: 100px; height: 100px; margin-right: 30px; object-fit: contain;"> {equipo}
                </td>
                <td style="padding: 25px; text-align: center; font-weight: bold; color: #00e676;">{p['puntos']}</td>
                <td style="padding: 25px; text-align: center;">{p['goles']}</td>
            </tr>"""
    else:
        for i in range(tipo_grupo):
            tabla_html += f"""
            <tr style="border-bottom: 1px solid #333; opacity: 0.5;">
                <td style="padding: 25px; display: flex; align-items: center; color: #888; font-style: italic;">
                    <div style="width: 100px; height: 100px; margin-right: 30px; border: 2px dashed #555; border-radius: 50%;"></div>
                    Esperando Equipo {i+1}...
                </td>
                <td style="padding: 25px; text-align: center;">--</td>
                <td style="padding: 25px; text-align: center;">--</td>
            </tr>"""

    tabla_html += "</table>"
    st.markdown(tabla_html, unsafe_allow_html=True)
    
    time.sleep(30)
    st.rerun()

def renderizar_tarjetas_equipos(lista_equipos):
    if not lista_equipos:
        st.info("No hay equipos cargados.")
        return
    cols = st.columns(3)
    for idx, equipo in enumerate(lista_equipos):
        col_actual = cols[idx % 3]
        with col_actual:
            st.markdown(
                f"""<div style="border: 1px solid #464e5f; border-radius: 10px; padding: 15px; 
                margin-bottom: 15px; background-color: #1a1c24; text-align: center; min-height: 180px;">
                    <img src="{equipo['escudo_url'] if equipo['escudo_url'] else 'https://via.placeholder.com/100'}" 
                         style="max-width: 80px; max-height: 80px; border-radius: 50%; margin-bottom: 10px;">
                    <div style="font-weight: bold; font-size: 1.1em; color: white;">{equipo['nombre']}</div>
                </div>""", unsafe_allow_html=True)
