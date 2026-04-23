# Función de apoyo para el sorteo (puedes ponerla en src/logic.py después)
def realizar_sorteo(fase_id, lista_grupos):
    supabase = get_supabase()
    # 1. Obtener todos los equipos
    equipos = supabase.table("equipos").select("id").eq("eliminado", False).execute().data
    import random
    random.shuffle(equipos) # ¡Mezclamos!

    participantes = []
    equipo_idx = 0
    
    # 2. Ir llenando los grupos
    for grupo in lista_grupos:
        for _ in range(grupo['tipo_grupo']):
            if equipo_idx < len(equipos):
                participantes.append({
                    "grupo_id": grupo['id'],
                    "equipo_id": equipos[equipo_idx]['id']
                })
                equipo_idx += 1
    
    # 3. Subir a participantes_grupo
    if participantes:
        supabase.table("participantes_grupo").insert(participantes).execute()
        st.success("¡Sorteo completado y guardado!")
        st.rerun()
