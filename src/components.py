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
    """Vista Gigante para la Televisión corregida"""
    supabase = get_supabase()
    
    try:
        # 1. Buscamos el grupo
        res_grupo = supabase.table("grupos").select("id, nombre, tipo_grupo").eq("nombre", nombre_grupo_url).execute()
        
        if not res_grupo.data:
            st.error(f"Grupo '{nombre_grupo_url}' no encontrado.")
            return

        datos_grupo = res_grupo.data[0]
        grupo_id = datos_grupo['id']
        tipo_grupo = datos_grupo['tipo_grupo']

        # 2. Buscamos participantes
        res_part = supabase.table("participantes_grupo").select("puntos, goles, equipos(nombre, escudo_url)").eq("grupo_id", grupo_id).order("puntos", desc=True).execute()
        participantes = res_part.data if res_part.data else []

        # --- CONSTRUCCIÓN DEL STRING HTML (Todo en una variable) ---
        # Añadimos un contenedor con fondo oscuro y bordes redondeados para que parezca una tarjeta
        html_final = f"""
        <div style="background-color: #1a1c24; padding: 30px; border-radius: 15px; border: 1px solid #333;">
            <h1 style='text-align: center; font-size: 5rem; color: white; margin-bottom: 30px; font-family: sans-serif;'>
                {datos_grupo['nombre']}
            </h1>
            <table style="width:100%; border-collapse: collapse; font-size: 2.8rem; color: white; font-family: sans-serif;">
                <tr style="border-bottom: 3px solid #444; background-color: #1f2937;">
                    <th style="padding: 25px; text-align: left;">Equipo</th>
                    <th style="padding: 25px; text-align: center;">PTS</th>
                    <th style="padding: 25px; text-align: center;">GF</th>
                </tr>
        """

        if participantes:
            for p in participantes:
                escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else "https://via.placeholder.com/100"
                html_final += f"""
                <tr style="border-bottom: 1px solid #333;">
                    <td style="padding: 25px; display: flex; align-items: center;">
                        <img src="{escudo}" style="width: 100px; height: 100px; margin-right: 30px; object-fit: contain;">
                        <span style="font-weight: 500;">{p['equipos']['nombre']}</span>
                    </td>
                    <td style="padding: 25px; text-align: center; font-weight: bold; color: #00e676;">{p['puntos']}</td>
                    <td style="padding: 25px; text-align: center;">{p['goles']}</td>
                </tr>
                """
        else:
            # Renderizar huecos vacíos con estilo profesional
            for i in range(tipo_grupo):
                html_final += f"""
                <tr style="border-bottom: 1px solid #333; opacity: 0.4;">
                    <td style="padding: 25px; display: flex; align-items: center; color: #888;">
                        <div style="width: 100px; height: 100px; margin-right: 30px; border: 3px dashed #444; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">
                            E{i+1}
                        </div>
                        <span style="font-style: italic;">Esperando Equipo {i+1}...</span>
                    </td>
                    <td style="padding: 25px; text-align: center;">--</td>
                    <td style="padding: 25px; text-align: center;">--</td>
                </tr>
                """

        html_final += "</table></div>"

        # IMPORTANTE: Esto es lo que hace que se vea como tabla y no como texto
        st.markdown(html_final, unsafe_allow_html=True)
        
        # Refresco automático
        time.sleep(30)
        st.rerun()

    except Exception as e:
        st.error(f"Error en el renderizado: {e}")

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
