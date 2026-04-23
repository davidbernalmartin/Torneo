import streamlit as st
import pandas as pd
from src.database import *

st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

st.title("🏆 Gestión de Campeonato RFFM")

# Sidebar para navegación
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual"])

if menu == "Dashboard":
    st.write(f"Bienvenido David. Tienes {len(get_equipos())} equipos cargados.")
    # Aquí irá un resumen de la fase actual

if menu == "Carga de Equipos":
    st.subheader("🚀 Importación Masiva de Equipos")
    
    archivo = st.file_uploader("Sube tu Excel o CSV", type=['xlsx', 'csv'])
    
    if archivo:
        # Leer según el formato
        if archivo.name.endswith('xlsx'):
            df = pd.read_excel(archivo)
        else:
            df = pd.read_csv(archivo)
            
        st.write("### Vista previa de tus equipos")
        st.dataframe(df, use_container_width=True)
        
        # Validación simple de columnas
        columnas_ok = 'nombre' in df.columns and 'escudo_url' in df.columns
        
        if columnas_ok:
            if st.button("Confirmar y subir a Supabase"):
                # Convertimos el DataFrame a una lista de diccionarios
                equipos_dict = df[['nombre', 'escudo_url']].to_dict(orient='records')
                
                with st.spinner("Subiendo 101 equipos..."):
                    resultado = subir_equipos_batch(equipos_dict)
                    
                if isinstance(resultado, str):
                    st.error(resultado)
                else:
                    st.success(f"¡{len(equipos_dict)} equipos cargados con éxito!")
        else:
            st.error("El archivo debe tener las columnas: 'nombre' y 'escudo_url'")

if menu == "Configurador":
    st.subheader("⚙️ Definición de Grupos por Fase")
    
    # 1. Obtener fases existentes
    supabase = get_supabase()
    fases_res = supabase.table("fases").select("*").order("orden").execute()
    fases = fases_res.data
    
    if not fases:
        st.warning("Primero crea una fase (ej. 'Primera Ronda') en la base de datos.")
    else:
        fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        fase_id = next(f["id"] for f in fases if f["nombre"] == fase_sel)
        
        st.write("---")
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            num_grupos = st.number_input("Número de grupos", min_value=1, value=1)
        with col2:
            tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
        with col3:
            st.write("Acción")
            if st.button("➕ Añadir"):
                # Generamos los grupos en la tabla 'grupos'
                nuevos_grupos = []
                for i in range(num_grupos):
                    nuevos_grupos.append({
                        "fase_id": fase_id,
                        "nombre": f"Grupo {i+1} ({fase_sel})",
                        "tipo_grupo": tamano_grupo
                    })
                
                supabase.table("grupos").insert(nuevos_grupos).execute()
                st.success(f"¡{num_grupos} grupos de {tamano_grupo} añadidos!")

    # 3. Visualización de lo configurado
    st.write("### Estructura actual de la Fase")
    grupos_res = supabase.table("grupos").select("*").eq("fase_id", fase_id).execute()
    if grupos_res.data:
        df_grupos = pd.DataFrame(grupos_res.data)
        st.dataframe(df_grupos[['nombre', 'tipo_grupo']], use_container_width=True)
        
        total_plazas = df_grupos['tipo_grupo'].sum()
        st.metric("Total plazas configuradas", f"{total_plazas} / 101")
