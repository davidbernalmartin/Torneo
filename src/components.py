import streamlit as st
import time
from src.database import get_supabase

def seccion_sorteo_manual(supabase):
    """
    Gestiona el sorteo automático buscando la fase de orden 1.
    """
    st.subheader("🔮 Mesa de Sorteo (Fase Inicial)")

    # 1. Localizar automáticamente la fase de orden 1
    res_fase = supabase.table("fases").select("id, nombre").eq("orden", 1).execute()
    
    if not res_fase.data:
        st.error("No se ha encontrado ninguna fase con orden 1 en la base de datos.")
        return
    
    fase_inicial = res_fase.data[0]
    fase_id = fase_inicial['id']
    st.caption(f"Configurando sorteo para: **{fase_inicial['nombre']}**")

    # 2. Cargar equipos libres (los que no están en ningún grupo de ESTA fase)
    # Primero sacamos los grupos de esta fase
    res_grupos = supabase.table("grupos").select("id, nombre").eq("fase_id", fase_id).execute()
    grupos = res_grupos.data
    ids_grupos = [g['id'] for g in grupos]

    # Ahora vemos qué equipos ya están metidos en esos grupos
    res_p = supabase.table("participantes_grupo").select("equipo_id").in_("grupo_id", ids_grupos).execute()
    asignados_ids = [p['equipo_id'] for p in res_p.data]

    # Equipos totales vs asignados
    res_e = supabase.table("equipos").select("id, nombre").execute()
    equipos_libres = [e for e in res_e.data if e['id'] not in asignados_ids]

    if not equipos_libres:
        st.success("🏁 ¡Sorteo completado! Todos los equipos están en sus grupos.")
        return

    # 3. Interfaz de asignación
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 0.6])
        with c1:
            equipo_nombre = st.selectbox("Bola Equipo:", [""] + [e['nombre'] for e in equipos_libres])
        with c2:
            grupo_nombre = st.selectbox("Bola Grupo:", [""] + [g['nombre'] for g in grupos])
        with c3:
            st.write("##")
            if st.button("CONFIRMAR 📥", use_container_width=True, type="primary"):
                if equipo_nombre and grupo_nombre:
                    id_e = next(e['id'] for e in equipos_libres if e['nombre'] == equipo_nombre)
                    id_g = next(g['id'] for g in grupos if g['nombre'] == grupo_nombre)
                    
                    supabase.table("participantes_grupo").insert({
                        "grupo_id": id_g,
                        "equipo_id": id_e,
                        "puntos": 0, "goles": 0
                    }).execute()
                    
                    st.toast(f"Asignado: {equipo_nombre} al {grupo_nombre}")
                    st.rerun()

    st.info(f"Faltan por asignar **{len(equipos_libres)}** equipos.")

def renderizar_tarjeta_grupo(grupo, participantes):
    """
    Dibuja una tarjeta de grupo con fondo blanco y letras negras.
    """
    # Usamos el contenedor nativo con un estilo CSS inyectado para forzar el blanco
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white !important;
            border-radius: 12px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # Título del grupo en negro
        st.markdown(f"<h3 style='color: black; margin-bottom: 0;'>📋 {grupo['nombre']}</h3>", unsafe_allow_html=True)
        
        # Botón sutil
        url_tv = f"/?view=tv&grupo={grupo['nombre']}"
        st.link_button("📺 Pantalla Completa", url_tv, use_container_width=True)
        
        st.write("") 

        # Lista de participantes
        for i in range(grupo['tipo_grupo']):
            if i < len(participantes):
                p = participantes[i]
                escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else "https://via.placeholder.com/30"
                nombre = p['equipos']['nombre']
                
                # Caja para equipo (Azul corporativo pero con texto legible sobre blanco)
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 5px; display: flex; align-items: center; border: 1px solid #ddd;">
                        <img src="{escudo}" style="width: 25px; height: 25px; margin-right: 10px; object-fit: contain;">
                        <span style="font-weight: bold; color: #1a1c24;">{nombre}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Caja para hueco vacío (Gris suave sobre blanco)
                st.markdown(
                    """
                    <div style="border: 1px dashed #ccc; padding: 10px; border-radius: 8px; margin-bottom: 5px; text-align: center; color: #999;">
                        <span style="font-size: 0.9rem; font-style: italic;">👤 Esperando equipo...</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
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
        time.sleep(5)
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
