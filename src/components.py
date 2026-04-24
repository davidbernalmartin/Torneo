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
