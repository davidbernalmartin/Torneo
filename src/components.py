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
    """Vista para la TV: Versión compacta con escudos"""
    supabase = get_supabase()
    
    try:
        # 1. Buscar el grupo
        res_grupo = supabase.table("grupos").select("id, nombre, tipo_grupo").eq("nombre", nombre_grupo_url).execute()
        
        if not res_grupo.data:
            st.error(f"Grupo '{nombre_grupo_url}' no encontrado.")
            return

        datos_grupo = res_grupo.data[0]
        grupo_id = datos_grupo['id']
        nombre_display = datos_grupo['nombre']
        tipo_grupo = datos_grupo['tipo_grupo']

        # Título ajustado (de 7rem a 4rem)
        st.markdown(f"""
            <h1 style='text-align: center; font-size: 4rem; margin-top: -40px; color: white;'>
                {nombre_display}
            </h1>
        """, unsafe_allow_html=True)
        
        st.write("---")

        # 2. Obtener participantes
        res_part = supabase.table("participantes_grupo").select("equipos(nombre, escudo_url)").eq("grupo_id", grupo_id).execute()
        participantes = res_part.data if res_part.data else []

        # 3. Dibujar las cajas (más pequeñas)
        for i in range(tipo_grupo):
            if i < len(participantes):
                # EQUIPO ASIGNADO
                nombre_equipo = participantes[i]['equipos']['nombre']
                escudo = participantes[i]['equipos']['escudo_url']
                
                st.markdown(f"""
                    <div style="
                        background-color: #1E88E5; 
                        padding: 10px 30px; 
                        border-radius: 12px; 
                        margin-bottom: 10px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        box-shadow: 0px 3px 8px rgba(0,0,0,0.3);
                    ">
                        {f'<img src="{escudo}" style="height: 60px; width: 60px; object-fit: contain; margin-right: 20px;">' if escudo else ''}
                        <span style="font-size: 2.8rem; font-weight: bold; color: white;">{nombre_equipo}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                # HUECO VACÍO (Más bajo)
                st.markdown(f"""
                    <div style="
                        padding: 15px; 
                        border: 3px dashed #555; 
                        border-radius: 12px; 
                        margin-bottom: 10px; 
                        text-align: center; 
                        opacity: 0.5;
                    ">
                        <span style="font-size: 2rem; color: #888; font-style: italic;">Esperando Sorteo...</span>
                    </div>
                """, unsafe_allow_html=True)

        # 4. Refresco automático
        import time
        time.sleep(20)
        st.rerun()

    except Exception as e:
        st.error(f"Error en la visualización: {e}")
        
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
