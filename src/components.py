# src/components.py
import streamlit as st

def mostrar_grupo_tv(grupo_id):
    supabase = get_supabase()
    
    # 1. Obtener datos del grupo y sus participantes
    # Hacemos un join para traer el nombre del equipo y su escudo
    res = supabase.table("participantes_grupo")\
        .select("puntos, goles, equipo_id, equipos(nombre, escudo_url), grupos(nombre)")\
        .eq("grupo_id", grupo_id)\
        .order("puntos", desc=True)\
        .execute()
    
    if not res.data:
        st.error(f"No se encontraron datos para el grupo ID: {grupo_id}")
        return

    nombre_grupo = res.data[0]['grupos']['nombre']
    st.title(f"📍 {nombre_grupo}")
    st.write("---")

    # 2. Renderizar tabla gigante
    # Usamos HTML/CSS para controlar el tamaño exacto, ya que st.table es pequeño
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
        pts = p['puntos']
        gf = p['goles']
        
        tabla_html += f"""
        <tr style="border-bottom: 1px solid #333;">
            <td style="padding: 20px; display: flex; align-items: center;">
                <img src="{escudo}" style="width: 80px; margin-right: 20px;"> {equipo}
            </td>
            <td style="padding: 20px; text-align: center; font-weight: bold; color: #00e676;">{pts}</td>
            <td style="padding: 20px; text-align: center;">{gf}</td>
        </tr>
        """
    
    tabla_html += "</table>"
    st.markdown(tabla_html, unsafe_allow_html=True)

    # 3. Auto-refresco (importante para que la TV se actualice sola)
    import time
    time.sleep(30) # Espera 30 segundos
    st.rerun()

def mostrar_pantalla_tv():
    supabase = get_supabase()
    
    # 1. Seleccionamos qué grupo queremos proyectar
    # (Esto lo puedes guardar en una tabla de 'ajustes' en Supabase o usar un selector aquí)
    fases = supabase.table("fases").select("*").order("orden").execute().data
    
    if fases:
        # Para que sea automático, podrías elegir siempre el primer grupo de la fase actual
        # o dejar un selector oculto.
        st.title("🏆 Resultados en Tiempo Real")
        
        # Consultamos los grupos y sus participantes
        # NOTA: Aquí podrías añadir un st.empty() y un bucle para refresco automático
        # pero Streamlit ya refresca al detectar cambios en la DB si usas fragmentos.
        
        # Por ahora, mostramos un carrusel o un grupo específico
        grupos = supabase.table("grupos").select("*").execute().data
        
        for grupo in grupos:
            with st.container():
                st.header(f"📍 {grupo['nombre']}")
                # Aquí dibujarías la tabla de clasificación de ese grupo en grande
                # usando fuentes grandes para que se vea bien en la TV.
                renderizar_tabla_grande(grupo['id'])
                
        # Auto-refresh cada 30 segundos
        st.info("Actualizando automáticamente...")
        st.rerun()

def renderizar_cuadro_vacio(lista_grupos):
    """
    Dibuja los grupos con sus huecos vacíos según el tamaño definido (tipo_grupo).
    """
    if not lista_grupos:
        st.info("No hay grupos configurados para esta fase.")
        return

    # Usamos un grid para los grupos (por ejemplo, 2 por fila para que se vean bien los huecos)
    cols_grupos = st.columns(2)
    
    for idx, grupo in enumerate(lista_grupos):
        col_actual = cols_grupos[idx % 2]
        
        with col_actual:
            with st.container():
                # Cabecera del grupo
                c1, c2 = st.columns(2)
                width c1:
                    st.markdown(f"### 📋 {grupo['nombre']}")
                width c2:
                    # Dentro del bucle donde visualizas los grupos en el modo Administrador:
                    for grupo in grupos_res.data:
                        url_tv = f"https://tu-app.streamlit.app/?view=tv&grupo={grupo['id']}"
                        st.write(f"**{grupo['nombre']}**")
                        st.link_button(f"📺 Ver en TV", url_tv)
                # Generamos los huecos vacíos basados en 'tipo_grupo'
                for i in range(grupo['tipo_grupo']):
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px dashed #626771;
                            border-radius: 5px;
                            padding: 8px 15px;
                            margin-bottom: 5px;
                            background-color: rgba(255, 255, 255, 0.05);
                            color: #888;
                            font-style: italic;
                            display: flex;
                            justify-content: space-between;
                        ">
                            <span>👤 Hueco Equipo {i+1}</span>
                            <span>--</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                st.write("") # Espaciado entre grupos
                
def renderizar_tarjetas_equipos(lista_equipos):
    """
    Renderiza una lista de equipos en un grid de 3 columnas usando tarjetas.
    """
    if not lista_equipos:
        st.info("No hay equipos cargados todavía.")
        return

    # Usamos st.columns para crear el grid de 3
    cols = st.columns(3)
    
    for idx, equipo in enumerate(lista_equipos):
        # Seleccionamos la columna correspondiente usando el índice y el operador módulo
        col_actual = cols[idx % 3]
        
        with col_actual:
            # CSS para simular una tarjeta
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #464e5f;
                    border-radius: 10px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background-color: #1a1c24;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 180px;
                ">
                    <img src="{equipo['escudo_url'] if equipo['escudo_url'] else 'https://via.placeholder.com/100'}" 
                         style="max-width: 80px; max-height: 80px; border-radius: 50%; margin-bottom: 10px;">
                    <div style="
                        font-weight: bold;
                        font-size: 1.1em;
                        color: white;
                        margin-bottom: 5px;
                    ">
                        {equipo['nombre']}
                    </div>
                    {'<span style="color: #ff4b4b;">❌ Eliminado</span>' if equipo.get('eliminado') else '<span style="color: #00e676;">✅ En competición</span>'}
                </div>
                """,
                unsafe_allow_html=True
            )
