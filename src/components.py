import re
import time
import streamlit as st

from src.database import get_supabase


# Constante compartida para la vista TV
LOGO_TV_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"


# -------------------------------------------------------
# TARJETA DE GRUPO (vista escritorio)
# -------------------------------------------------------

def renderizar_tarjeta_grupo(grupo, participantes):
    """Tarjeta blanca minimalista con los equipos de un grupo."""
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"<h6 style='color: black;'>{grupo['nombre']}</h6>", unsafe_allow_html=True)

        for i in range(grupo["tipo_grupo"]):
            if i < len(participantes):
                p = participantes[i]
                escudo = p["equipos"]["escudo_url"] or ""
                nombre = p["equipos"]["nombre"]
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 8px; border-radius: 5px;
                                margin-bottom: 5px; display: flex; align-items: center;
                                border: 1px solid #eee;">
                        <img src="{escudo}" style="width: 20px; margin-right: 10px;">
                        <span style="color: black; font-weight: 500;">{nombre}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="padding: 8px; border: 1px dashed #ddd; border-radius: 5px;
                                margin-bottom: 5px; text-align: center; color: #aaa;
                                font-size: 0.8rem;">
                        Esperando equipo...
                    </div>
                """, unsafe_allow_html=True)


# -------------------------------------------------------
# VISTA TV
# -------------------------------------------------------

def mostrar_grupo_tv(nombre_grupo_url):
    """Vista para pantalla de TV: fichas blancas sobre fondo rojo."""
    supabase = get_supabase()

    try:
        res_grupo = (
            supabase.table("grupos")
            .select("id, nombre, tipo_grupo, fase_id")
            .eq("nombre", nombre_grupo_url)
            .execute()
        )

        if not res_grupo.data:
            st.error(f"Grupo '{nombre_grupo_url}' no encontrado.")
            return

        datos_grupo = res_grupo.data[0]
        grupo_id = datos_grupo["id"]
        fase_id = datos_grupo["fase_id"]
        nombre_display = datos_grupo["nombre"]
        tipo_grupo = datos_grupo["tipo_grupo"]

        # Cabecera con logo
        st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: center;
                        gap: 20px; width: 100%;">
                <img src="{LOGO_TV_URL}" style="width: 80px;">
                <h1 style="text-align: center; font-size: 5rem; margin: 20px 0;
                           color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                           line-height: 1;">
                    {nombre_display}
                </h1>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # Participantes
        res_part = (
            supabase.table("participantes_grupo")
            .select("equipos(nombre, escudo_url)")
            .eq("grupo_id", grupo_id)
            .execute()
        )
        participantes = res_part.data or []

        for i in range(tipo_grupo):
            if i < len(participantes):
                nombre_equipo = participantes[i]["equipos"]["nombre"]
                escudo = participantes[i]["equipos"]["escudo_url"]
                st.markdown(f"""
                    <div style="background-color: white; padding: 15px 40px;
                                border-radius: 15px; margin-bottom: 15px;
                                display: flex; align-items: center;
                                box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
                                border: 1px solid #eee;">
                        {f'<img src="{escudo}" style="height: 70px; width: 70px; object-fit: contain; margin-right: 30px;">' if escudo else ''}
                        <span style="font-size: 3.5rem; font-weight: 900; color: #1a1c24;
                                     text-transform: uppercase;">
                            {nombre_equipo}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="background-color: rgba(255,255,255,0.1); padding: 20px;
                                border: 3px dashed rgba(255,255,255,0.4);
                                border-radius: 15px; margin-bottom: 15px; text-align: center;">
                        <span style="font-size: 2.2rem; color: rgba(255,255,255,0.6);
                                     font-style: italic; font-weight: bold;">
                            ESPERANDO SORTEO...
                        </span>
                    </div>
                """, unsafe_allow_html=True)

        # Navegador de grupos
        st.write("---")
        res_hermanos = (
            supabase.table("grupos")
            .select("nombre")
            .eq("fase_id", fase_id)
            .execute()
        )

        if res_hermanos.data:
            def extraer_num(n):
                nums = re.findall(r"\d+", n)
                return int(nums[0]) if nums else 0

            nombres_ordenados = sorted(
                [g["nombre"] for g in res_hermanos.data], key=extraer_num
            )
            cols_nav = st.columns(len(nombres_ordenados))

            for idx, nombre_btn in enumerate(nombres_ordenados):
                num_solo = re.findall(r"\d+", nombre_btn)
                label = f"G{num_solo[0]}" if num_solo else nombre_btn[:2]
                es_actual = nombre_btn == nombre_grupo_url

                if cols_nav[idx].button(
                    label,
                    key=f"btn_nav_tv_{nombre_btn}",
                    use_container_width=True,
                    type="primary" if es_actual else "secondary",
                ):
                    st.query_params["grupo"] = nombre_btn
                    st.rerun()

        # Refresco automático
        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error en la visualización: {e}")


# -------------------------------------------------------
# TARJETA DE GRUPO MINIMALISTA (Cuadro Visual)
# -------------------------------------------------------

def renderizar_tarjeta_grupo_minimalista(
    grupo, participantes, equipos_libres, es_progresion, fases, fase_actual, supabase
):
    """
    Tarjeta dark/deportiva para el Cuadro Visual (opción A).
    Cabecera roja RFFM, cuerpo oscuro, filas de equipo sobre fondo semitransparente.
    Recibe los datos ya precargados — no hace consultas salvo al confirmar asignación.
    """
    # Cabecera roja + cuerpo oscuro (HTML puro, sin widgets)
    st.markdown(f"""
        <div style="
            background: #1a1c24;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 6px;
        ">
            <div style="
                background: #cc0000;
                padding: 10px 14px;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <div style="width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,0.35);flex-shrink:0;"></div>
                <span style="font-size:0.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">
                    {grupo['nombre']}
                </span>
            </div>
            <div style="padding: 8px 14px 4px;">
    """, unsafe_allow_html=True)

    # Filas de equipos ya asignados (HTML)
    for i in range(grupo["tipo_grupo"]):
        p_actual = participantes[i] if i < len(participantes) else None
        if p_actual and p_actual["equipo_id"]:
            nombre_equipo = p_actual["equipos"]["nombre"]
            escudo = p_actual["equipos"]["escudo_url"] or ""
            img_tag = f'<img src="{escudo}" style="width:22px;height:22px;object-fit:contain;margin-right:10px;border-radius:3px;">' if escudo else '<div style="width:22px;margin-right:10px;"></div>'
            st.markdown(f"""
                <div style="
                    display:flex;align-items:center;
                    background:rgba(255,255,255,0.07);
                    border-radius:6px;
                    padding:6px 10px;
                    margin-bottom:5px;
                ">
                    {img_tag}
                    <span style="font-size:0.78rem;font-weight:700;color:#fff;
                                 text-transform:uppercase;letter-spacing:0.03em;
                                 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {nombre_equipo}
                    </span>
                </div>
            """, unsafe_allow_html=True)

    # Cierre del div oscuro
    st.markdown("</div></div>", unsafe_allow_html=True)

    # Plazas vacías — widgets de Streamlit fuera del HTML
    for i in range(grupo["tipo_grupo"]):
        p_actual = participantes[i] if i < len(participantes) else None
        if not (p_actual and p_actual["equipo_id"]):
            if not es_progresion:
                opciones = [f"— Plaza {i+1}"] + [e["nombre"] for e in equipos_libres]
                seleccion = st.selectbox(
                    f"plaza_{grupo['id']}_{i}",
                    opciones,
                    key=f"sel_{grupo['id']}_{i}",
                    label_visibility="collapsed",
                )
                if seleccion != opciones[0]:
                    try:
                        e_id = next(e["id"] for e in equipos_libres if e["nombre"] == seleccion)
                        supabase.table("participantes_grupo").insert({
                            "grupo_id": grupo["id"],
                            "equipo_id": e_id,
                            "referencia_origen": "Sorteo",
                        }).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al asignar: {e}")
            else:
                if p_actual and p_actual.get("referencia_origen"):
                    ref = p_actual["referencia_origen"]
                    nombre_g_orig = ref.split(" | ")[0] if " | " in ref else None
                    if nombre_g_orig:
                        try:
                            f_ant = next(
                                f for f in fases if f["orden"] == fase_actual["orden"] - 1
                            )
                            res_g = (
                                supabase.table("grupos")
                                .select("id")
                                .eq("nombre", nombre_g_orig)
                                .eq("fase_id", f_ant["id"])
                                .execute()
                            )
                            if res_g.data:
                                res_cand = (
                                    supabase.table("participantes_grupo")
                                    .select("equipos(id, nombre)")
                                    .eq("grupo_id", res_g.data[0]["id"])
                                    .execute()
                                )
                                candidatos = [p["equipos"] for p in res_cand.data if p["equipos"]]
                                opciones = [f"🏆 {ref}"] + [c["nombre"] for c in candidatos]
                                sel = st.selectbox(
                                    f"prog_{grupo['id']}_{i}",
                                    opciones,
                                    key=f"sel_prog_{grupo['id']}_{i}",
                                    label_visibility="collapsed",
                                )
                                if sel != opciones[0]:
                                    try:
                                        e_id = next(c["id"] for c in candidatos if c["nombre"] == sel)
                                        supabase.table("participantes_grupo").update(
                                            {"equipo_id": e_id}
                                        ).eq("id", p_actual["id"]).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al asignar progresión: {e}")
                        except Exception as e:
                            st.error(f"Error cargando candidatos: {e}")


# -------------------------------------------------------
# TARJETAS DE EQUIPOS (vista escritorio)
# -------------------------------------------------------

def renderizar_tarjetas_equipos(lista_equipos):
    """Muestra todos los equipos en una cuadrícula de 4 columnas."""
    if not lista_equipos:
        st.info("No hay equipos cargados.")
        return

    cols = st.columns(4)

    for idx, equipo in enumerate(lista_equipos):
        escudo = equipo["escudo_url"] or "https://via.placeholder.com/100"
        with cols[idx % 4]:
            st.markdown(f"""
                <div style="background-color: white; border-radius: 12px; padding: 20px;
                            margin-bottom: 20px; text-align: center;
                            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
                            border: 1px solid #ddd; min-height: 160px;
                            display: flex; flex-direction: column;
                            align-items: center; justify-content: center;">
                    <img src="{escudo}"
                         style="width: 70px; height: 70px; object-fit: contain; margin-bottom: 12px;">
                    <div style="font-weight: 800; font-size: 1rem; color: #1a1c24;
                                text-transform: uppercase; line-height: 1.2;">
                        {equipo['nombre']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
