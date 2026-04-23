# src/components.py
import streamlit as st

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
                st.markdown(f"### 📋 {grupo['nombre']}")
                
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
