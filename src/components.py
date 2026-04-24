import streamlit as st
import time
from src.database import get_supabase

def seccion_sorteo_manual(supabase):
    """
    Gestiona el sorteo automático buscando la fase de orden 1.
    """
    st.subheader("Mesa de Sorteo (Fase Inicial)")

    # 1. Localizar automáticamente la fase de orden 1
    res_fase = supabase.table("fases").select("id, nombre").eq("orden", 1).execute()
    
    if not res_fase.data:
        st.error("No se ha encontrado ninguna fase con orden 1 en la base de datos.")
        return
    
    fase_inicial = res_fase.data[0]
    fase_id = fase_inicial['id']
    st.caption(f"Configurando sorteo para: **{fase_inicial['nombre']}**")

    # 2. Cargar grupos y filtrar por capacidad
    # Traemos el tipo_grupo para saber el límite de cada uno
    res_grupos = supabase.table("grupos").select("id, nombre, tipo_grupo").eq("fase_id", fase_id).execute()
    todos_los_grupos = res_grupos.data
    ids_grupos = [g['id'] for g in todos_los_grupos]

    # Contamos cuántos equipos hay ya asignados a CADA grupo
    res_p = supabase.table("participantes_grupo").select("grupo_id, equipo_id").in_("grupo_id", ids_grupos).execute()
    asignados_ids = [p['equipo_id'] for p in res_p.data]
    
    # Creamos un contador de ocupación
    from collections import Counter
    ocupacion_actual = Counter([p['grupo_id'] for p in res_p.data])

    # FILTRADO: Solo grupos que NO estén llenos
    grupos_disponibles = []
    for g in todos_los_grupos:
        cupo = g['tipo_grupo']
        actual = ocupacion_actual.get(g['id'], 0)
        if actual < cupo:
            # Guardamos cuántas plazas quedan para mostrarlo en el select
            g['plazas_libres'] = cupo - actual
            grupos_disponibles.append(g)

    # Equipos totales vs asignados
    res_e = supabase.table("equipos").select("id, nombre").execute()
    equipos_libres = [e for e in res_e.data if e['id'] not in asignados_ids]

    if not equipos_libres:
        st.success("¡Sorteo completado! Todos los equipos están en sus grupos.")
        return

    # 3. Interfaz de asignación
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 0.6])
        with c1:
            equipo_nombre = st.selectbox("Bola Equipo:", [""] + [e['nombre'] for e in equipos_libres])
        with c2:
            # El selector ahora solo muestra los grupos con sitio
            opciones_grupos = [""] + [f"{g['nombre']} ({g['plazas_libres']} huecos)" for g in grupos_disponibles]
            indice_defecto = 0
            if (len(opciones_grupos) != 0):
                indice_defecto = 1
            grupo_sel_display = st.selectbox("Bola Grupo:", opciones_grupos, index=indice_defecto)
        with c3:
            st.write("##")
            if st.button("CONFIRMAR", use_container_width=True, type="primary"):
                if equipo_nombre and grupo_sel_display:
                    # Limpiamos el nombre del grupo para buscarlo en la lista original
                    nombre_grupo_limpio = grupo_sel_display.split(" (")[0]
                    
                    id_e = next(e['id'] for e in equipos_libres if e['nombre'] == equipo_nombre)
                    id_g = next(g['id'] for g in grupos_disponibles if g['nombre'] == nombre_grupo_limpio)
                    
                    supabase.table("participantes_grupo").insert({
                        "grupo_id": id_g,
                        "equipo_id": id_e,
                        "puntos": 0, "goles": 0
                    }).execute()
                    
                    st.toast(f"Asignado: {equipo_nombre} al {nombre_grupo_limpio}")
                    st.rerun()

    if not grupos_disponibles:
        st.warning("⚠️ No quedan grupos con plazas disponibles. Revisa la configuración de la fase.")
    
    st.info(f"Faltan por asignar **{len(equipos_libres)}** equipos.")

def renderizar_tarjeta_grupo(grupo, participantes):
    """Tarjeta blanca minimalista sobre fondo rojo plano"""
    # Este CSS asegura que el fondo de la tarjeta sea blanco puro
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # Texto negro para que resalte dentro del blanco
        st.markdown(f"<h6 style='color: black;'>{grupo['nombre']}</h6>", unsafe_allow_html=True)
        
        for i in range(grupo['tipo_grupo']):
            if i < len(participantes):
                p = participantes[i]
                escudo = p['equipos']['escudo_url'] if p['equipos']['escudo_url'] else ""
                nombre = p['equipos']['nombre']
                
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 8px; border-radius: 5px; margin-bottom: 5px; display: flex; align-items: center; border: 1px solid #eee;">
                        <img src="{escudo}" style="width: 20px; margin-right: 10px;">
                        <span style="color: black; font-weight: 500;">{nombre}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="padding: 8px; border: 1px dashed #ddd; border-radius: 5px; margin-bottom: 5px; text-align: center; color: #aaa; font-size: 0.8rem;">
                        Esperando equipo...
                    </div>
                """, unsafe_allow_html=True)
                    
def mostrar_grupo_tv(nombre_grupo_url):
    """Vista para la TV: Estilo blanco corporativo sobre fondo rojo"""
    supabase = get_supabase()
    LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"
    try:
        # 1. Buscar el grupo actual
        res_grupo = supabase.table("grupos").select("id, nombre, tipo_grupo, fase_id").eq("nombre", nombre_grupo_url).execute()
        
        if not res_grupo.data:
            st.error(f"Grupo '{nombre_grupo_url}' no encontrado.")
            return

        datos_grupo = res_grupo.data[0]
        grupo_id = datos_grupo['id']
        fase_id = datos_grupo['fase_id'] # Lo necesitamos para buscar los hermanos
        nombre_display = datos_grupo['nombre']
        tipo_grupo = datos_grupo['tipo_grupo']

        # Título con el logo integrado y centrado
        st.markdown(
            f"""
            <div style="
                display: flex; 
                align-items: center; 
                justify-content: center;
                gap: 20px;
                width: 100%;
            ">
                <img src="{LOGO_RFFM_URL}" style="width: 80px;"> <h1 style="
                    text-align: center; 
                    font-size: 5rem; 
                    margin: 20; 
                    color: white; 
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    line-height: 1;
                ">
                    {nombre_display}
                </h1>
            </div>
            """, 
            unsafe_allow_html=True
        )

        
        st.write("")

        # 2. Obtener participantes
        res_part = supabase.table("participantes_grupo").select("equipos(nombre, escudo_url)").eq("grupo_id", grupo_id).execute()
        participantes = res_part.data if res_part.data else []

        # 3. Dibujar las "Fichas Blancas"
        for i in range(tipo_grupo):
            if i < len(participantes):
                nombre_equipo = participantes[i]['equipos']['nombre']
                escudo = participantes[i]['equipos']['escudo_url']
                
                st.markdown(f"""
                    <div style="background-color: white; padding: 15px 40px; border-radius: 15px; margin-bottom: 15px; 
                                display: flex; align-items: center; justify-content: flex-start;
                                box-shadow: 0px 4px 15px rgba(0,0,0,0.2); border: 1px solid #eee;">
                        {f'<img src="{escudo}" style="height: 70px; width: 70px; object-fit: contain; margin-right: 30px;">' if escudo else ''}
                        <span style="font-size: 3.5rem; font-weight: 900; color: #1a1c24; text-transform: uppercase;">
                            {nombre_equipo}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="background-color: rgba(255,255,255,0.1); padding: 20px; border: 3px dashed rgba(255,255,255,0.4); 
                                border-radius: 15px; margin-bottom: 15px; text-align: center;">
                        <span style="font-size: 2.2rem; color: rgba(255,255,255,0.6); font-style: italic; font-weight: bold;">
                            ESPERANDO SORTEO...
                        </span>
                    </div>
                """, unsafe_allow_html=True)

        # --- 4. NAVEGADOR DE GRUPOS (Minitarjetas inferiores) ---
        st.write("---")
       # Obtenemos los grupos (mismo código que antes)
        res_hermanos = supabase.table("grupos").select("nombre").eq("fase_id", fase_id).execute()
        
        if res_hermanos.data:
            import re
            def extraer_num(n):
                nums = re.findall(r'\d+', n)
                return int(nums[0]) if nums else 0
            
            nombres_ordenados = sorted([g['nombre'] for g in res_hermanos.data], key=extraer_num)
            
            # --- LA CLAVE ESTÁ AQUÍ ---
            # Usamos un contenedor único para los botones para evitar duplicados
            nav_container = st.container()
            
            with nav_container:
                # Calculamos columnas dinámicamente según el número de grupos
                n_grupos = len(nombres_ordenados)
                cols_nav = st.columns(n_grupos)
                
                for idx, nombre_btn in enumerate(nombres_ordenados):
                    num_solo = re.findall(r'\d+', nombre_btn)
                    label = f"G{num_solo[0]}" if num_solo else nombre_btn[:2]
                    
                    es_actual = (nombre_btn == nombre_grupo_url)
                    
                    # Usamos una key muy específica para que Streamlit no se líe
                    if cols_nav[idx].button(label, key=f"btn_nav_tv_{nombre_btn}", use_container_width=True, type="primary" if es_actual else "secondary"):
                        st.query_params["grupo"] = nombre_btn
                        st.rerun()

        # 5. Refresco automático (Ojo: bajamos el tiempo si quieres que el cambio sea rápido)
        import time
        time.sleep(3) # 10 segundos es más razonable para que dé tiempo a leer
        st.rerun()

    except Exception as e:
        st.error(f"Error en la visualización: {e}")
        
def renderizar_tarjetas_equipos(lista_equipos):
    """
    Muestra la lista de equipos inscritos con el nuevo estilo de tarjetas blancas.
    """
    if not lista_equipos:
        st.info("No hay equipos cargados.")
        return

    # Usamos 4 columnas para que queden más compactas y se vea más profesional
    cols = st.columns(4)
    
    for idx, equipo in enumerate(lista_equipos):
        col_actual = cols[idx % 4]
        with col_actual:
            # Escudo por defecto si no hay URL
            escudo = equipo['escudo_url'] if equipo['escudo_url'] else 'https://via.placeholder.com/100'
            
            st.markdown(
                f"""
                <div style="
                    background-color: white; 
                    border-radius: 12px; 
                    padding: 20px; 
                    margin-bottom: 20px; 
                    text-align: center; 
                    box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
                    border: 1px solid #ddd;
                    min-height: 160px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                ">
                    <img src="{escudo}" 
                         style="width: 70px; height: 70px; object-fit: contain; margin-bottom: 12px;">
                    <div style="
                        font-weight: 800; 
                        font-size: 1rem; 
                        color: #1a1c24; 
                        text-transform: uppercase;
                        line-height: 1.2;
                    ">
                        {equipo['nombre']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
