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
    
    supabase = get_supabase()
    
    # 1. Gestión de Fases (Crear la fase si no existe)
    with st.expander("➕ Crear Nueva Fase"):
        nueva_fase_nombre = st.text_input("Nombre de la fase (ej: Primera Ronda)")
        orden_fase = st.number_input("Orden", min_value=1, value=1)
        if st.button("Guardar Fase"):
            supabase.table("fases").insert({"nombre": nueva_fase_nombre, "orden": orden_fase}).execute()
            st.success("Fase creada")
            st.rerun()

    # 2. Obtener fases existentes
    fases_res = supabase.table("fases").select("*").order("orden").execute()
    fases = fases_res.data
    
    if not fases:
        st.info("Crea una fase arriba para empezar a configurar grupos.")
    else:
        # Usamos un selectbox para elegir la fase
        fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        
        # BUSCAMOS EL ID de la fase seleccionada de forma segura
        fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)
        
        if fase_actual:
            fase_id = fase_actual["id"] # Ahora sí está definida de forma segura
            
            st.write("---")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                num_grupos = st.number_input("Número de grupos", min_value=1, value=1)
            with col2:
                tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
            with col3:
                st.write("Acción")
               if st.button("➕ Añadir"):
                    # 1. Inicializamos la lista para evitar NameError
                    nuevos_grupos = []
                    
                    try:
                        # 2. Consultar cuántos grupos hay ya en esta fase
                        res_conteo = supabase.table("grupos").select("id", count="exact").eq("fase_id", fase_id).execute()
                        total_existentes = res_conteo.count if res_conteo.count is not None else 0
                        
                        # 3. Generar la lista de nuevos registros
                        for i in range(num_grupos):
                            siguiente_numero = total_existentes + i + 1
                            nuevos_grupos.append({
                                "fase_id": fase_id,
                                "nombre": f"Grupo {siguiente_numero}", # Nombre más limpio
                                "tipo_grupo": tamano_grupo
                            })
                        
                        # 4. Solo ejecutamos si la lista tiene contenido
                        if nuevos_grupos:
                            supabase.table("grupos").insert(nuevos_grupos).execute()
                            st.success(f"¡Añadidos grupos del {total_existentes + 1} al {total_existentes + num_grupos}!")
                            st.rerun()
                        else:
                            st.error("No se generaron grupos para añadir.")
                            
                    except Exception as e:
                        st.error(f"Hubo un error al interactuar con Supabase: {e}")
    
                # 2. Insertar en Supabase
                supabase.table("grupos").insert(nuevos_grupos).execute()
                st.success(f"¡Añadidos grupos del {total_existentes + 1} al {total_existentes + num_grupos}!")
                st.rerun()

            # 3. Visualización de lo configurado (Solo si fase_id existe)
            st.write("### Estructura actual de la Fase")
            grupos_res = supabase.table("grupos").select("*").eq("fase_id", fase_id).execute()
            
            if grupos_res.data:
                df_grupos = pd.DataFrame(grupos_res.data)
                st.dataframe(df_grupos[['nombre', 'tipo_grupo']], use_container_width=True)
                
                total_plazas = df_grupos['tipo_grupo'].sum()
                st.metric("Total plazas configuradas", f"{total_plazas} / 101")
                
                if st.button("🗑️ Borrar todos los grupos de esta fase"):
                    supabase.table("grupos").delete().eq("fase_id", fase_id).execute()
                    st.warning("Grupos eliminados")
                    st.rerun()
