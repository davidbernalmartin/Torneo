import streamlit as st
import pandas as pd
from src.database import *
from src.logic import *
from src.components import *

# URL del escudo oficial
LOGO_RFFM_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/favicon_87ea61909c.png"

st.set_page_config(layout="wide")
query_params = st.query_params

if "view" in query_params and query_params["view"] == "tv":
    # Obtenemos el ID del grupo de la URL (si existe)
    # Ejemplo de URL: https://tu-app.app/?view=tv&grupo=5
    grupo_id_url = query_params.get("grupo")
    
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            .main {background-color: #0e1117; color: white;}
            h1, h2, h3 {text-align: center; font-size: 4rem !important;} /* Fuentes gigantes para TV */
        </style>
    """, unsafe_allow_html=True)

    if grupo_id_url:
        from src.components import mostrar_grupo_tv
        mostrar_grupo_tv(grupo_id_url)
    else:
        st.warning("⚠️ No se ha especificado ningún ID de grupo en la URL.")
    
    st.stop()

st.set_page_config(page_title="Gestor Torneo RFFM", layout="wide")

# Título con el logo integrado
st.markdown(
    f"""
    <div style="display: flex; align-items: center;">
        <img src="{LOGO_RFFM_URL}" style="width: 50px; margin-right: 15px;">
        <h1 style="margin: 0;">Gestión de Campeonato RFFM</h1>
    </div>
    """, 
    unsafe_allow_html=True
)

# Sidebar para navegación
menu = st.sidebar.selectbox("Menú", ["Dashboard", "Configurador", "Carga de Equipos", "Cuadro Visual", "Sorteo"])

if menu == "Dashboard":
    equipos = get_equipos()
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Total Equipos", len(equipos))
    col_e2.metric("En Competición", len([e for e in equipos if not e['eliminado']]))
    
    st.write("---")
    st.subheader("Plantilla de Equipos")
    
    # Llamamos al componente visual
    renderizar_tarjetas_equipos(equipos)

if menu == "Carga de Equipos":
    st.subheader("Importación Masiva de Equipos")
    
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
        st.subheader("Equipos actualmente en la Base de Datos")
        renderizar_tarjetas_equipos(get_equipos())

if menu == "Configurador":
    st.subheader("Definición de Grupos por Fase")
    supabase = get_supabase()
    
    # 1. Gestión de Fases (Sin cambios)
    with st.expander("➕ Crear Nueva Fase"):
        nueva_fase_nombre = st.text_input("Nombre de la fase (ej: Fase de grupos)")
        orden_fase = st.number_input("Orden", min_value=1, value=1)
        if st.button("Guardar Fase"):
            supabase.table("fases").insert({"nombre": nueva_fase_nombre, "orden": orden_fase}).execute()
            st.success("Fase creada")
            st.rerun()

    fases_res = supabase.table("fases").select("*").order("orden").execute()
    fases = fases_res.data
    
    if not fases:
        st.info("Crea una fase arriba para empezar.")
    else:
        fase_sel = st.selectbox("Selecciona la Fase a configurar", [f["nombre"] for f in fases])
        fase_actual = next((f for f in fases if f["nombre"] == fase_sel), None)
        
        if fase_actual:
            fase_id = fase_actual["id"]
            es_fase_progresion = fase_actual["orden"] > 1

            # 2. Creación de Grupos
            st.write("---")
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                num_grupos = st.number_input("Añadir N grupos", min_value=1, value=1)
            with col2:
                tamano_grupo = st.number_input("Equipos por grupo", min_value=1, value=4)
            with col3:
                st.write("Acción")
                if st.button("➕ Añadir"):
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
                    supabase.table("grupos").insert(nuevos_grupos).execute()
                    st.rerun()

            # 3. Visualización y Configuración de Progresión
            st.write("### Estructura y Origen de Plazas")
            grupos_res = supabase.table("grupos").select("*").eq("fase_id", fase_id).execute()
            
            if grupos_res.data:
                # Si es fase > 1, necesitamos saber qué grupos había en la fase anterior
                fase_anterior = next((f for f in fases if f["orden"] == fase_actual["orden"] - 1), None)
                grupos_anteriores = []
                if fase_anterior:
                    res_ant = supabase.table("grupos").select("nombre").eq("fase_id", fase_anterior["id"]).execute()
                    grupos_anteriores = [g['nombre'] for g in res_ant.data]

                for grupo in grupos_res.data:
                    with st.expander(f"⚙️ Configurar {grupo['nombre']} ({grupo['tipo_grupo']} plazas)"):
                        if not es_fase_progresion:
                            st.write("✅ Fase 1: Las plazas se llenan por sorteo aleatorio.")
                        else:
                            st.write(f"Define de dónde viene cada equipo para el **{grupo['nombre']}**:")
                            
                            # Consultamos si ya existen plazas configuradas para este grupo
                            res_plazas = supabase.table("participantes_grupo").select("*").eq("grupo_id", grupo['id']).execute()
                            plazas_actuales = res_plazas.data
                            
                            for i in range(grupo['tipo_grupo']):
                                col_p, col_o, col_pos = st.columns([1, 2, 2])
                                col_p.write(f"Plaza {i+1}")
                                
                                # Buscar si esta plaza ya tiene configuración
                                config_existente = plazas_actuales[i] if i < len(plazas_actuales) else None
                                
                                # Selectores para definir origen
                                orig_g = col_o.selectbox(f"Grupo Origen", grupos_anteriores, key=f"g_{grupo['id']}_{i}")
                                orig_pos = col_pos.selectbox(f"Clasificado", ["1º", "2º", "3º", "4º"], key=f"pos_{grupo['id']}_{i}")
                                
                                etiqueta_referencia = f"{orig_g} | {orig_pos}"
                                
                                if st.button(f"Vincular Plaza {i+1}", key=f"btn_{grupo['id']}_{i}"):
                                    # Si la plaza existe, actualizamos. Si no, insertamos (sin equipo_id aún)
                                    payload = {
                                        "grupo_id": grupo['id'],
                                        "referencia_origen": etiqueta_referencia,
                                        "equipo_id": None # Se llenará después manualmente
                                    }
                                    if config_existente:
                                        supabase.table("participantes_grupo").update(payload).eq("id", config_existente['id']).execute()
                                    else:
                                        supabase.table("participantes_grupo").insert(payload).execute()
                                    st.success(f"Plaza {i+1} vinculada a {etiqueta_referencia}")
                                    st.rerun()

                # Métricas informativas
                total_plazas = sum(g['tipo_grupo'] for g in grupos_res.data)
                st.info(f"Capacidad total de la fase: {total_plazas} equipos.")

if menu == "Cuadro Visual":
    st.subheader("Gestión de Equipos por Grupo")
    supabase = get_supabase()

    fases_res = supabase.table("fases").select("*").order("orden").execute()
    fases = fases_res.data
    
    if not fases:
        st.info("No hay fases configuradas.")
    else:
        fase_sel = st.selectbox("Seleccionar Fase", [f["nombre"] for f in fases])
        fase_actual = next(f for f in fases if f["nombre"] == fase_sel)
        fase_id = fase_actual["id"]
        es_progresion = fase_actual["orden"] > 1
        
        grupos_res = supabase.table("grupos").select("*").eq("fase_id", fase_id).execute()
        
        # --- GRID DE 3 COLUMNAS ---
        cols_grupos = st.columns(3)
        
        for idx, grupo in enumerate(grupos_res.data):
            with cols_grupos[idx % 3]:
                # Cabecera
                st.markdown(f"""
                    <div style="display: flex; align-items: center; justify-content: center; margin-top: 25px; margin-bottom: 10px;">
                        <img src="https://www.rffm.es/_next/image?url=https%3A%2F%2Frffm-cms.s3.eu-west-1.amazonaws.com%2Ffavicon_87ea61909c.png&w=48&q=75" style="width: 22px; margin-right: 8px;">
                        <h2 style="color: white; margin: 0; font-size: 1.2rem; font-weight: bold; text-transform: uppercase;">
                            {grupo['nombre']}
                        </h2>
                    </div>
                """, unsafe_allow_html=True)
                
                res_p = supabase.table("participantes_grupo").select("*, equipos(id, nombre, escudo_url)").eq("grupo_id", grupo['id']).execute()
                participantes = res_p.data
                
                for i in range(grupo['tipo_grupo']):
                    p_actual = participantes[i] if i < len(participantes) else None
                    
                    if p_actual and p_actual['equipo_id']:
                        # --- TARJETA EQUIPO (ALTURA 45PX) ---
                        nombre_equipo = p_actual['equipos']['nombre']
                        escudo = p_actual['equipos']['escudo_url']
                        st.markdown(f"""
                            <div style="background-color: white; border-radius: 8px; padding: 0 12px; margin-bottom: 8px; 
                                        display: flex; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #e60000;
                                        height: 45px; box-sizing: border-box;">
                                <img src="{escudo if escudo else ''}" style="width: 26px; height: 26px; object-fit: contain; margin-right: 10px; display: {'block' if escudo else 'none'};">
                                <span style="color: #1a1a1a; font-size: 0.9rem; font-weight: 800; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    {nombre_equipo}
                                </span>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # --- SELECTORES (ALTURA 45PX POR DEFECTO) ---
                        if not es_progresion:
                            # Lógica Fase 1
                            res_todos = supabase.table("equipos").select("id, nombre").eq("eliminado", False).execute()
                            res_ocupados = supabase.table("participantes_grupo").select("equipo_id").execute()
                            ocupados_ids = [o['equipo_id'] for o in res_ocupados.data if o['equipo_id']]
                            equipos_libres = [e for e in res_todos.data if e['id'] not in ocupados_ids]
                            
                            opciones = [f"➕ Plaza {i+1}"] + [e['nombre'] for e in equipos_libres]
                            # CLAVE: Capturamos el valor del selectbox
                            seleccion = st.selectbox(f"P{i+1}_{grupo['id']}", opciones, key=f"sel_{grupo['id']}_{i}", label_visibility="collapsed")
                            
                            if seleccion != opciones[0]:
                                e_id = next(e['id'] for e in equipos_libres if e['nombre'] == seleccion)
                                supabase.table("participantes_grupo").insert({
                                    "grupo_id": grupo['id'], "equipo_id": e_id, "referencia_origen": "Sorteo"
                                }).execute()
                                st.rerun()
                        else:
                            # Lógica Progresión
                            if p_actual and p_actual['referencia_origen']:
                                ref = p_actual['referencia_origen']
                                nombre_g_orig = ref.split(" | ")[0] if " | " in ref else None
                                if nombre_g_orig:
                                    f_ant = next(f for f in fases if f['orden'] == fase_actual['orden'] - 1)
                                    res_g_orig = supabase.table("grupos").select("id").eq("nombre", nombre_g_orig).eq("fase_id", f_ant['id']).execute()
                                    if res_g_orig.data:
                                        id_g_orig = res_g_orig.data[0]['id']
                                        res_cand = supabase.table("participantes_grupo").select("equipos(id, nombre)").eq("grupo_id", id_g_orig).execute()
                                        candidatos = [p['equipos'] for p in res_cand.data if p['equipos']]
                                        
                                        opciones = [f"🏆 {ref}"] + [c['nombre'] for c in candidatos]
                                        seleccion_prog = st.selectbox(f"C{i+1}_{grupo['id']}", opciones, key=f"sel_prog_{grupo['id']}_{i}", label_visibility="collapsed")
                                        
                                        if seleccion_prog != opciones[0]:
                                            e_id = next(c['id'] for c in candidatos if c['nombre'] == seleccion_prog)
                                            supabase.table("participantes_grupo").update({"equipo_id": e_id}).eq("id", p_actual['id']).execute()
                                            st.rerun()

if menu == "Sorteo":
    supabase = get_supabase()
    seccion_sorteo_manual(supabase)
