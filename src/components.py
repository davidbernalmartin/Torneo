import re
import time
import streamlit as st

from src.database import get_supabase


LOGO_TV_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"
_CUALQUIER = "Cualquier grupo"


# -------------------------------------------------------
# HELPERS HTML
# -------------------------------------------------------

def _html_tarjeta_dark(nombre_grupo, cuerpo_html, badge="", opacity="1", extra_style="", margin_bottom="4px"):
    return (
        f'<div style="background:#8b0000;border-radius:10px;overflow:hidden;'
        f'margin-bottom:{margin_bottom};opacity:{opacity};{extra_style}">'
        f'<div style="background:#cc0000;padding:8px 12px;'
        f'display:flex;align-items:center;gap:6px;">'
        f'<div style="width:6px;height:6px;border-radius:50%;'
        f'background:rgba(255,255,255,0.4);flex-shrink:0;"></div>'
        f'<span style="font-size:0.7rem;font-weight:700;color:white;'
        f'text-transform:uppercase;letter-spacing:0.06em;">{nombre_grupo}</span>'
        f'{badge}'
        f'</div>'
        f'<div style="padding:6px 10px 8px;">{cuerpo_html}</div>'
        f'</div>'
    )


# -------------------------------------------------------
# VISTA TV
# -------------------------------------------------------

def mostrar_grupo_tv(nombre_grupo_url):
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

        participantes = (
            supabase.table("participantes_grupo")
            .select("equipos(nombre, escudo_url)")
            .eq("grupo_id", grupo_id)
            .execute()
            .data
        ) or []

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

        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error en la visualización: {e}")


# -------------------------------------------------------
# CONFIGURADOR DE PROGRESIÓN VISUAL
# -------------------------------------------------------

def configurar_progresion_visual(grupos_destino, grupos_origen):
    supabase = get_supabase()

    def _num(nombre):
        m = re.search(r"\d+", nombre)
        return int(m.group()) if m else 0

    ids_destino = [g["id"] for g in grupos_destino]
    res_plazas = (
        supabase.table("participantes_grupo")
        .select("*")
        .in_("grupo_id", ids_destino)
        .execute()
    )
    plazas_por_grupo: dict = {}
    for p in res_plazas.data:
        plazas_por_grupo.setdefault(p["grupo_id"], []).append(p)

    grupos_origen_sorted = sorted(grupos_origen, key=lambda g: _num(g["nombre"]))

    for g_dest in grupos_destino:
        g_id = g_dest["id"]
        plazas = plazas_por_grupo.get(g_id, [])
        for i in range(g_dest["tipo_grupo"]):
            ss_key = f"pcfg_{g_id}_{i}"
            if ss_key not in st.session_state:
                plaza = plazas[i] if i < len(plazas) else None
                ref = plaza.get("referencia_origen") if plaza else None
                st.session_state[ss_key] = ref or _CUALQUIER

    def get_asignados(excluir_key=None):
        asignados = set()
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            for i in range(g_dest["tipo_grupo"]):
                k = f"pcfg_{g_id}_{i}"
                if k == excluir_key:
                    continue
                val = st.session_state.get(k, _CUALQUIER)
                if val and val != _CUALQUIER:
                    asignados.add(val)
        return asignados

    col_izq, col_sep, col_der = st.columns([5, 1, 5])

    with col_izq:
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase anterior</p>",
            unsafe_allow_html=True,
        )
        for g_orig in grupos_origen_sorted:
            nombre = g_orig["nombre"]
            asignado = nombre in get_asignados()
            badge = (
                "<span style='margin-left:auto;font-size:11px;color:#3B6D11;"
                "background:#EAF3DE;padding:2px 8px;border-radius:999px;'>"
                "&#10003; asignado</span>"
                if asignado else ""
            )
            filas = "".join(
                f"<div style='background:rgba(255,255,255,0.08);border-radius:5px;"
                f"padding:5px 8px;margin-bottom:4px;font-size:0.7rem;"
                f"color:rgba(255,255,255,0.6);'>{idx_f + 1}&#186; clasificado</div>"
                for idx_f in range(g_orig["tipo_grupo"])
            )
            st.markdown(
                _html_tarjeta_dark(
                    nombre, filas,
                    badge=badge,
                    opacity="0.4" if asignado else "1",
                    extra_style="filter:grayscale(0.4);" if asignado else "",
                    margin_bottom="8px",
                ),
                unsafe_allow_html=True,
            )

    with col_sep:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;"
            "height:100%;padding-top:60px;font-size:1.4rem;color:#888;'>→</div>",
            unsafe_allow_html=True,
        )

    with col_der:
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Nueva fase</p>",
            unsafe_allow_html=True,
        )
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            plazas = plazas_por_grupo.get(g_id, [])

            st.markdown(
                f"<div style='background:#8b0000;border-radius:10px 10px 0 0;"
                f"padding:8px 12px;display:flex;align-items:center;gap:6px;margin-bottom:2px;'>"
                f"<div style='width:6px;height:6px;border-radius:50%;"
                f"background:rgba(255,255,255,0.4);flex-shrink:0;'></div>"
                f"<span style='font-size:0.7rem;font-weight:700;color:white;"
                f"text-transform:uppercase;letter-spacing:0.06em;'>{g_dest['nombre']}</span></div>",
                unsafe_allow_html=True,
            )

            for i in range(g_dest["tipo_grupo"]):
                ss_key = f"pcfg_{g_id}_{i}"
                plaza = plazas[i] if i < len(plazas) else None
                ref_bd = plaza.get("referencia_origen") if plaza else None

                asignados_otros = get_asignados(excluir_key=ss_key)
                opciones = [_CUALQUIER] + sorted(
                    [g["nombre"] for g in grupos_origen if g["nombre"] not in asignados_otros],
                    key=_num,
                )

                if st.session_state[ss_key] not in opciones:
                    st.session_state[ss_key] = _CUALQUIER

                seleccion = st.selectbox(
                    f"Plaza {i+1}",
                    opciones,
                    key=ss_key,
                    label_visibility="collapsed",
                )

                if seleccion != ref_bd:
                    try:
                        payload = {
                            "grupo_id": g_id,
                            "referencia_origen": seleccion,
                            "equipo_id": None,
                            "es_local": i == 0,
                        }
                        if plaza:
                            supabase.table("participantes_grupo").update(payload).eq(
                                "id", plaza["id"]
                            ).execute()
                            if ref_bd and ref_bd != _CUALQUIER:
                                g_ant = next(
                                    (g for g in grupos_origen if g["nombre"] == ref_bd), None
                                )
                                if g_ant:
                                    supabase.table("grupos").update(
                                        {"siguiente_grupo_id": None}
                                    ).eq("id", g_ant["id"]).execute()
                        else:
                            supabase.table("participantes_grupo").insert(payload).execute()

                        if seleccion != _CUALQUIER:
                            g_orig_match = next(
                                (g for g in grupos_origen if g["nombre"] == seleccion), None
                            )
                            if g_orig_match:
                                supabase.table("grupos").update(
                                    {"siguiente_grupo_id": g_id}
                                ).eq("id", g_orig_match["id"]).execute()
                    except Exception as e:
                        st.error(f"Error al guardar plaza {i+1}: {e}")

            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)


# -------------------------------------------------------
# CUADRO DE PROGRESIÓN
# -------------------------------------------------------

def renderizar_cuadro_progresion(
    grupos_destino,
    grupos_origen,
    participantes_por_grupo_destino,
    participantes_por_grupo_origen,
    ya_asignados_ids,
    fases,
    fase_actual,
):
    supabase = get_supabase()

    def _fila_equipo(nombre, escudo, ya_paso):
        bg = "rgba(255,255,255,0.04)" if ya_paso else "white"
        color = "#aaa" if ya_paso else "#1a1a1a"
        opacity = "0.4" if ya_paso else "1"
        tick = "<span style='margin-left:auto;font-size:10px;color:#3B6D11;font-weight:700;flex-shrink:0;'>✓</span>" if ya_paso else ""
        img = (
            f'<img src="{escudo}" style="width:20px;height:20px;object-fit:contain;margin-right:8px;border-radius:3px;">'
            if escudo else '<div style="width:20px;margin-right:8px;"></div>'
        )
        return (
            f'<div style="display:flex;align-items:center;background:{bg};border-radius:5px;'
            f'padding:5px 8px;margin-bottom:4px;opacity:{opacity};">'
            f'{img}'
            f'<span style="font-size:0.72rem;font-weight:700;color:{color};text-transform:uppercase;'
            f'letter-spacing:0.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{nombre}</span>'
            f'{tick}</div>'
        )

    def _fila_hueco():
        return '<div style="border:1px dashed rgba(255,255,255,0.3);border-radius:5px;background:rgba(0,0,0,0.15);height:30px;margin-bottom:4px;"></div>'

    col_izq, col_sep, col_der = st.columns([5, 1, 5])

    with col_izq:
        st.markdown("<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase anterior</p>", unsafe_allow_html=True)
        for g_orig in grupos_origen:
            participantes = participantes_por_grupo_origen.get(g_orig["id"], [])
            cuerpo = "".join(
                _fila_equipo(
                    p["equipos"]["nombre"],
                    p["equipos"].get("escudo_url") or "",
                    p["equipo_id"] in ya_asignados_ids,
                )
                for p in participantes
                if p.get("equipo_id") and p.get("equipos")
            ) or '<div style="font-size:0.7rem;color:rgba(255,255,255,0.3);font-style:italic;padding:4px 0;">Sin equipos asignados</div>'
            st.markdown(_html_tarjeta_dark(g_orig["nombre"], cuerpo), unsafe_allow_html=True)

    with col_sep:
        st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:100%;padding-top:60px;font-size:1.4rem;color:#888;'>→</div>", unsafe_allow_html=True)

    with col_der:
        st.markdown("<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase actual</p>", unsafe_allow_html=True)
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            capacidad = g_dest["tipo_grupo"]
            participantes = participantes_por_grupo_destino.get(g_id, [])
            n_asignados = sum(1 for p in participantes if p.get("equipo_id"))
            grupo_lleno = n_asignados >= capacidad

            cuerpo = "".join(
                _fila_equipo(p["equipos"]["nombre"], p["equipos"].get("escudo_url") or "", False)
                for p in participantes
                if p.get("equipo_id") and p.get("equipos")
            ) + _fila_hueco() * (capacidad - n_asignados)

            st.markdown(_html_tarjeta_dark(g_dest["nombre"], cuerpo), unsafe_allow_html=True)

            if grupo_lleno:
                if st.button("⊘  Vaciar grupo", key=f"vaciar_{g_id}", use_container_width=True):
                    st.session_state[f"confirmar_vaciar_{g_id}"] = True
                if st.session_state.get(f"confirmar_vaciar_{g_id}", False):
                    st.warning(f"¿Borrar equipos de {g_dest['nombre']}?")
                    col_si, col_no = st.columns(2)
                    if col_si.button("Sí, vaciar", key=f"si_vaciar_{g_id}", type="primary"):
                        try:
                            supabase.table("participantes_grupo").update({"equipo_id": None}).eq("grupo_id", g_id).execute()
                            st.session_state.pop(f"confirmar_vaciar_{g_id}", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al vaciar: {e}")
                    if col_no.button("Cancelar", key=f"no_vaciar_{g_id}"):
                        st.session_state.pop(f"confirmar_vaciar_{g_id}", None)
                        st.rerun()
            else:
                plazas_vacias = [p for p in participantes if not p.get("equipo_id")]
                if not plazas_vacias:
                    st.caption("Sin plazas configuradas. Ve al Configurador.")
                else:
                    p_actual = plazas_vacias[0]
                    ref = p_actual.get("referencia_origen") or _CUALQUIER
                    try:
                        if ref == _CUALQUIER:
                            candidatos = [
                                p["equipos"]
                                for plist in participantes_por_grupo_origen.values()
                                for p in plist
                                if p.get("equipos") and p.get("equipo_id")
                                and p["equipo_id"] not in ya_asignados_ids
                            ]
                        else:
                            g_orig_match = next((g for g in grupos_origen if g["nombre"] == ref), None)
                            candidatos = [
                                p["equipos"]
                                for p in participantes_por_grupo_origen.get(
                                    g_orig_match["id"] if g_orig_match else -1, []
                                )
                                if p.get("equipos") and p.get("equipo_id")
                                and p["equipo_id"] not in ya_asignados_ids
                            ] if g_orig_match else []

                        opciones = ["— añadir equipo —"] + [c["nombre"] for c in candidatos]
                        seleccion = st.selectbox(
                            f"sel_{g_id}",
                            opciones,
                            key=f"sel_prog_cv_{g_id}",
                            label_visibility="collapsed",
                        )
                        if seleccion != opciones[0]:
                            e_id = next(c["id"] for c in candidatos if c["nombre"] == seleccion)
                            supabase.table("participantes_grupo").update({"equipo_id": e_id}).eq("id", p_actual["id"]).execute()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error cargando candidatos: {e}")

            st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)


# -------------------------------------------------------
# TARJETA DE GRUPO MINIMALISTA
# -------------------------------------------------------

def renderizar_tarjeta_grupo_minimalista(grupo, participantes, equipos_libres):
    supabase = get_supabase()
    grupo_id = grupo["id"]
    capacidad = grupo["tipo_grupo"]
    asignados = [p for p in participantes if p and p.get("equipo_id")]
    grupo_lleno = len(asignados) >= capacidad

    st.markdown(f"""
        <div style="background:#8b0000;border-radius:12px;overflow:hidden;margin-bottom:4px;">
            <div style="background:#cc0000;padding:10px 14px;display:flex;align-items:center;gap:8px;">
                <div style="width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,0.35);flex-shrink:0;"></div>
                <span style="font-size:0.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">
                    {grupo['nombre']}
                </span>
            </div>
            <div style="padding:8px 14px 8px;">
    """, unsafe_allow_html=True)

    for i in range(capacidad):
        p_actual = participantes[i] if i < len(participantes) else None
        if p_actual and p_actual.get("equipo_id"):
            nombre_equipo = p_actual["equipos"]["nombre"]
            escudo = p_actual["equipos"]["escudo_url"] or ""
            img_tag = (
                f'<img src="{escudo}" style="width:22px;height:22px;object-fit:contain;margin-right:10px;border-radius:3px;">'
                if escudo else
                '<div style="width:22px;margin-right:10px;"></div>'
            )
            st.markdown(f"""
                <div style="display:flex;align-items:center;background:white;
                            border-radius:6px;padding:6px 10px;margin-bottom:5px;">
                    {img_tag}
                    <span style="font-size:0.78rem;font-weight:700;color:#1a1a1a;text-transform:uppercase;
                                 letter-spacing:0.03em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {nombre_equipo}
                    </span>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="border:1px dashed rgba(255,255,255,0.3);border-radius:6px;
                            background:rgba(0,0,0,0.15);height:34px;margin-bottom:5px;"></div>
            """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    if grupo_lleno:
        if st.button("⊘  Vaciar grupo", key=f"vaciar_{grupo_id}", use_container_width=True):
            st.session_state[f"confirmar_vaciar_{grupo_id}"] = True

        if st.session_state.get(f"confirmar_vaciar_{grupo_id}", False):
            st.warning(f"¿Borrar todos los equipos de {grupo['nombre']}?")
            col_si, col_no = st.columns(2)
            if col_si.button("Sí, vaciar", key=f"si_vaciar_{grupo_id}", type="primary"):
                try:
                    supabase.table("participantes_grupo").update({"equipo_id": None}).eq("grupo_id", grupo_id).execute()
                    st.session_state.pop(f"confirmar_vaciar_{grupo_id}", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al vaciar: {e}")
            if col_no.button("Cancelar", key=f"no_vaciar_{grupo_id}"):
                st.session_state.pop(f"confirmar_vaciar_{grupo_id}", None)
                st.rerun()
    else:
        opciones = ["— añadir equipo —"] + [e["nombre"] for e in equipos_libres]
        seleccion = st.selectbox(
            f"sel_label_{grupo_id}",
            opciones,
            key=f"sel_{grupo_id}",
            label_visibility="collapsed",
        )
        if seleccion != opciones[0]:
            try:
                e_id = next(e["id"] for e in equipos_libres if e["nombre"] == seleccion)
                supabase.table("participantes_grupo").insert({
                    "grupo_id": grupo_id,
                    "equipo_id": e_id,
                    "referencia_origen": "Sorteo",
                }).execute()
                st.rerun()
            except Exception as e:
                st.error(f"Error al asignar: {e}")


# -------------------------------------------------------
# TARJETAS DE EQUIPOS
# -------------------------------------------------------

def renderizar_tarjetas_equipos(lista_equipos):
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
