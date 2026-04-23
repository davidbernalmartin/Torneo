import streamlit as st
import pandas as pd
from src.database import *
from src.logic import *
from src.components import *

st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

st.title("🏆 Gestión de Campeonato RFFM")

# Sidebar para navegación
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual"])

if menu == "Dashboard":
    if menu == "Dashboard":
    equipos = get_equipos()
    st.subheader(f"📊 Resumen del Campeonato")
    
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e['eliminado']]))
    
    st.write("---")
    st.subheader("🛡️ Plantilla de Equipos")
    
    # Llamamos al componente visual
    renderizar_tarjetas_equipos(equipos)

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
                        st.rerun()
            else:
                st.error("El archivo debe tener las columnas: 'nombre' y 'escudo_url'")
    
        # --- AÑADE ESTO AL FINAL DE LA SECCIÓN DE CARGA ---
        st.write("---")
        st.subheader("👀 Equipos actualmente en la Base de Datos")
        renderizar_tarjetas_equipos(get_equipos())
        else:
            st.error("El archivo debe tener las columnas: 'nombre' y 'escudo_url'")

if menu == "Configurador":
    st.subheader("⚙️ Definición de Grupos por Fase")
    supabase = get_supabase()
    
    # 1. Gestión de Fases
    with st.expander("➕ Crear Nueva Fase"):
        nueva_fase_nombre = st.text_input("Nombre de la fase (ej: Fase de grupos)")
        orden_fase = st.number_input("Orden", min_value=1, value=1)
        if st.button("Guardar Fase"):
            supabase.table("fases").insert({"nombre": nueva_fase_nombre, "orden": orden_fase}).execute()
            st.success("Fase creada")
            st.rerun()

    # 2. Obtener fases existentes
    fases_res = supabase.table("fases").select("*").order("orden").execute()
    fases = fases_res.data
    
    if not fases:
        st.info("Crea una fase arriba para empezar.")
    else:
        fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)
        
        if fase_actual:
            fase_id = fase_actual["id"]
            
            st.write("---")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                num_grupos = st.number_input("Número de grupos", min_value=1, value=1)
            with col2:
                tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
            with col3:
                st.write("Acción")
                if st.button("➕ Añadir"):
                    try:
                        res_conteo = supabase.table("grupos").select("id", count="exact").eq("fase_id", fase_id).execute()
                        total_existentes = res_conteo.count if res_conteo.count is not None else 0
                        
                        nuevos_grupos = []
                        for i in range(num_grupos):
                            siguiente_numero = total_existentes + i + 1
                            nuevos_grupos.append({
                                "fase_id": fase_id,
                                "nombre": f"Grupo {siguiente_numero}",
                                "tipo_grupo": tamano_grupo
                            })
                        
                        if nuevos_grupos:
                            supabase.table("grupos").insert(nuevos_grupos).execute()
                            st.success(f"¡Añadidos!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            # 3. Visualización y Sorteo
            st.write("### Estructura actual de la Fase")
            grupos_res = supabase.table("grupos").select("*").eq("fase_id", fase_id).execute()
            
            # Dentro de if menu == "Configurador" -> Visualización
            if grupos_res.data:
                df_grupos = pd.DataFrame(grupos_res.data)
                total_plazas = df_grupos['tipo_grupo'].sum()
                
                # Consultamos cuántos equipos hay cargados realmente
                res_equipos = supabase.table("equipos").select("id", count="exact").eq("eliminado", False).execute()
                total_equipos_bd = res_equipos.count if res_equipos.count is not None else 0
                
                # Mostramos la comparativa real
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Equipos en BD", total_equipos_bd)
                col_m2.metric("Plazas en Grupos", f"{total_plazas} / {total_equipos_bd}")
            
                if total_plazas >= total_equipos_bd:
                    st.success("✅ Tienes plazas suficientes para todos los equipos cargados.")
                    if st.button("🎲 Lanzar Sorteo Aleatorio"):
                        with st.spinner("Distribuyendo equipos..."):
                            realizar_sorteo(fase_id, grupos_res.data)
                            st.rerun()
                else:
                    st.warning(f"⚠️ Faltan {total_equipos_bd - total_plazas} plazas por configurar.")
