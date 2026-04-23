import streamlit as st
import pandas as pd
from src.database import subir_equipos_batch
from src.database import get_equipos

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
