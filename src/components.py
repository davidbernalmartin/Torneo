import streamlit as st
from src.database import get_supabase

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
    # Consulta con Join para traer datos de equipos y grupos
    res = supabase.table("participantes_grupo")\
        .select("puntos, goles, equipo_id, equipos(nombre, escudo_url), grupos(nombre)")\
        .eq("grupo_id", grupo_id)\
        .order("puntos", desc=True).execute()
    
    if not res.data:
        st.error("No hay datos para este grupo.")
        return

    nombre_grupo = res.data[0]['grupos']['nombre']
    st.markdown(f"<h1 style='text-align: center; font-size: 4rem;'>{nombre_grupo}</h1>", unsafe_allow_html=True)
    
    tabla_html = """
    <table style="width:100%; border-collapse: collapse; font-size: 2.5rem; color: white;">
        <tr style="border-bottom: 2px solid #444; background-color: #1f2937;">
            <th style="padding: 20px; text-align: left;">Equipo</th>
            <th style="padding: 20px; text-align: center;">PTS</th>
            <th style="padding: 20px; text-align: center;">GF</th>
        </tr>
    """
    for p in res.data:
        equipo = p['equipos']['nombre']
        escudo = p['equipos']['escudo_url']
        tabla_html += f"""
        <tr style="border-bottom: 1px solid #333;">
            <td style="padding: 20px; display: flex; align-items: center;">
                <img src="{escudo}" style="width: 80px; margin-right: 20px;"> {equipo}
            </td>
            <td style="padding: 20px; text-align: center; font-weight: bold; color: #00e676;">{p['puntos']}</td>
            <td style="padding: 20px; text-align: center;">{p['goles']}</td>
        </tr>"""
    tabla_html += "</table>"
    st.markdown(tabla_html, unsafe_allow_html=True)
    
    import time
    time.sleep(30)
    st.rerun()
