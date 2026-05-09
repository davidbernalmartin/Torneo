import re
import streamlit as st

from src.database import get_supabase

_CUALQUIER_GRUPO = "Cualquier grupo"


def _cancelar_confirm(clave):
    st.session_state.pop(clave, None)


def _guardar_notas_grupo(grupo_id, clave):
    nuevas = st.session_state.get(clave, "") or None
    try:
        get_supabase().table("grupos").update({"notas": nuevas}).eq("id", grupo_id).execute()
    except Exception:
        pass


# Constante compartida para la vista TV
LOGO_TV_URL = "https://rffm-cms.s3.eu-west-1.amazonaws.com/large_favicon_87ea61909c.png"


# -------------------------------------------------------
# VISTA TV
# -------------------------------------------------------

def mostrar_grupo_tv(grupo_id_param, torneo_id=None):
    """Vista para pantalla de TV: fichas blancas sobre fondo rojo."""
    supabase = get_supabase()

    try:
        # ── Datos del grupo — búsqueda directa por ID ───────────────────────
        res_grupo = (
            supabase.table("grupos")
            .select("id, nombre, tipo_grupo, fase_id, notas")
            .eq("id", grupo_id_param)
            .limit(1)
            .execute()
        )
        if not res_grupo.data:
            st.error(f"Grupo no encontrado (id: {grupo_id_param}).")
            return

        datos_grupo    = res_grupo.data[0]
        grupo_id       = datos_grupo["id"]
        fase_id        = datos_grupo["fase_id"]
        nombre_display = datos_grupo["nombre"]
        tipo_grupo     = datos_grupo["tipo_grupo"]
        notas_grupo    = datos_grupo.get("notas") or ""

        # ── Cabecera estática ────────────────────────────────────────────────
        notas_tv_html = (
            f'<p style="text-align:center;color:rgba(255,255,255,0.8);'
            f'font-size:2rem;margin:-10px 0 20px;font-weight:400;">{notas_grupo}</p>'
            if notas_grupo else ""
        )
        st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:center;
                        gap:20px;width:100%;">
                <img src="{LOGO_TV_URL}" style="width:80px;">
                <h1 style="text-align:center;font-size:5rem;margin:20px 0;
                           color:white;text-shadow:2px 2px 4px rgba(0,0,0,0.3);
                           line-height:1;">
                    {nombre_display}
                </h1>
            </div>
            {notas_tv_html}
        """, unsafe_allow_html=True)

        st.write("")

        # ── Participantes — se refresca cada 3 s sin recargar la página ─────
        @st.fragment(run_every=3)
        def _participantes():
            res_part = (
                supabase.table("participantes_grupo")
                .select("equipo_id, created_at")
                .eq("grupo_id", grupo_id)
                .order("created_at", desc=False)
                .execute()
            )
            participantes_raw = res_part.data or []

            eq_ids = [p["equipo_id"] for p in participantes_raw if p.get("equipo_id")]

            eq_map = {}
            if eq_ids:
                res_eq = (
                    supabase.table("equipos")
                    .select("id, nombre, escudo_url")
                    .in_("id", eq_ids)
                    .execute()
                )
                eq_map = {e["id"]: e for e in (res_eq.data or [])}

            participantes = []
            for p in participantes_raw:
                eq = eq_map.get(p.get("equipo_id"))
                participantes.append({"equipo_id": p.get("equipo_id"), "equipo": eq})

            # Equipos asignados primero (orden created_at preservado), huecos al final.
            # sorted() es estable: la posición relativa de los asignados no cambia.
            participantes = sorted(participantes, key=lambda p: (0 if p.get("equipo") else 1))
            participantes = participantes[:tipo_grupo]

            for i in range(tipo_grupo):
                if i < len(participantes) and participantes[i].get("equipo"):
                    nombre_equipo = participantes[i]["equipo"]["nombre"]
                    escudo = participantes[i]["equipo"]["escudo_url"] or ""
                    img = (
                        f'<img src="{escudo}" style="height:80px;width:80px;'
                        f'object-fit:contain;margin-right:32px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.15));">'
                        if escudo else ""
                    )
                    st.markdown(f"""
                        <div style="background:white;padding:18px 48px;
                                    border-radius:12px;margin-bottom:12px;
                                    display:flex;align-items:center;
                                    justify-content:center;
                                    box-shadow:0 6px 24px rgba(0,0,0,0.35);">
                            {img}
                            <span style="font-size:3.5rem;font-weight:900;color:#1a0000;
                                         text-transform:uppercase;letter-spacing:0.02em;">
                                {nombre_equipo}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style="background:rgba(0,0,0,0.20);padding:22px 48px;
                                    border:2px dashed rgba(255,255,255,0.35);
                                    border-radius:12px;margin-bottom:12px;
                                    display:flex;align-items:center;justify-content:center;">
                            <span style="font-size:2rem;color:rgba(255,255,255,0.45);
                                         font-style:italic;font-weight:700;letter-spacing:0.08em;">
                                ESPERANDO SORTEO…
                            </span>
                        </div>
                    """, unsafe_allow_html=True)

        _participantes()

        # ── Navegador de grupos (solo fase orden=1) ─────────────────────────
        st.write("---")
        if torneo_id:
            res_fase1 = (
                supabase.table("fases")
                .select("id")
                .eq("torneo_id", torneo_id)
                .eq("orden", 1)
                .limit(1)
                .execute()
            )
            fase1_id = res_fase1.data[0]["id"] if res_fase1.data else None
        else:
            fase1_id = fase_id

        if fase1_id:
            res_hermanos = (
                supabase.table("grupos")
                .select("id, nombre, orden_cuadro")
                .eq("fase_id", fase1_id)
                .execute()
            )

            if res_hermanos.data:
                def extraer_num(n):
                    nums = re.findall(r"\d+", n)
                    return int(nums[0]) if nums else 0

                grupos_nav = sorted(
                    res_hermanos.data,
                    key=lambda g: (
                        g["orden_cuadro"] if g.get("orden_cuadro") is not None else float("inf"),
                        extraer_num(g["nombre"]),
                    ),
                )
                cols_nav = st.columns(len(grupos_nav))
                for idx, g_nav in enumerate(grupos_nav):
                    nombre_btn = g_nav["nombre"]
                    palabras = re.findall(r"[A-Za-zÀ-ÿ]+", nombre_btn)
                    primera = palabras[0][0].upper() if palabras else "G"
                    nums = re.findall(r"\d+", nombre_btn)
                    label = f"{primera}{nums[-1]}" if nums else primera
                    es_actual = g_nav["id"] == grupo_id

                    if cols_nav[idx].button(
                        label,
                        key=f"btn_nav_tv_{g_nav['id']}",
                        width='stretch',
                        type="primary" if es_actual else "secondary",
                    ):
                        st.query_params["grupo"] = g_nav["id"]
                        st.rerun()

    except Exception as e:
        st.error(f"Error en la visualización: {e}")


# -------------------------------------------------------
# CONFIGURADOR DE PROGRESIÓN VISUAL (lado a lado)
# -------------------------------------------------------

def configurar_progresion_visual(grupos_destino, grupos_origen, supabase, torneo_id=None):
    """
    Configurador de progresión con selectbox directo por plaza.
    Restricción: un grupo origen solo puede aparecer una vez.
    session_state controla el valor — no se pierde tras rerun.
    """
    def _num(nombre):
        m = re.search(r"\d+", nombre)
        return int(m.group()) if m else 0

    # ── Cargar plazas desde BD ───────────────────────────
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

    # Inicializar session_state desde BD (solo si no existe aún)
    for g_dest in grupos_destino:
        g_id = g_dest["id"]
        plazas = plazas_por_grupo.get(g_id, [])
        for i in range(g_dest["tipo_grupo"]):
            ss_key = f"pcfg_{g_id}_{i}"
            if ss_key not in st.session_state:
                plaza = plazas[i] if i < len(plazas) else None
                ref = plaza.get("referencia_origen") if plaza else None
                st.session_state[ss_key] = ref or _CUALQUIER_GRUPO

    # Grupos ya asignados según session_state (fuente de verdad)
    def get_asignados(excluir_key=None):
        asignados = set()
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            for i in range(g_dest["tipo_grupo"]):
                k = f"pcfg_{g_id}_{i}"
                if k == excluir_key:
                    continue
                val = st.session_state.get(k, _CUALQUIER_GRUPO)
                if val and val != _CUALQUIER_GRUPO:
                    asignados.add(val)
        return asignados

    col_izq, col_sep, col_der = st.columns([5, 1, 5])

    # ── IZQUIERDA ────────────────────────────────────────
    with col_izq:
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase anterior</p>",
            unsafe_allow_html=True,
        )
        for g_orig in grupos_origen_sorted:
            nombre = g_orig["nombre"]
            asignados = get_asignados()
            asignado = nombre in asignados
            opacidad = "0.4" if asignado else "1"
            grayscale = "filter:grayscale(0.4);" if asignado else ""
            badge = (
                "<span style='margin-left:auto;font-size:11px;color:#3B6D11;"
                "background:#EAF3DE;padding:2px 8px;border-radius:999px;'>"
                "&#10003; asignado</span>"
                if asignado else ""
            )
            filas = ""
            for idx_f in range(g_orig["tipo_grupo"]):
                filas += (
                    "<div style='background:rgba(255,255,255,0.08);border-radius:5px;"
                    "padding:5px 8px;margin-bottom:4px;font-size:0.7rem;"
                    "color:rgba(255,255,255,0.6);'>"
                    + str(idx_f + 1) + "&#186; clasificado</div>"
                )
            html_card = (
                "<div style='background:#8b0000;border-radius:10px;overflow:hidden;"
                "margin-bottom:8px;opacity:" + opacidad + ";" + grayscale + "'>"
                "<div style='background:#cc0000;padding:8px 12px;"
                "display:flex;align-items:center;gap:6px;'>"
                "<div style='width:6px;height:6px;border-radius:50%;"
                "background:rgba(255,255,255,0.4);flex-shrink:0;'></div>"
                "<span style='font-size:0.7rem;font-weight:700;color:white;"
                "text-transform:uppercase;letter-spacing:0.06em;'>"
                + nombre + "</span>" + badge +
                "</div>"
                "<div style='padding:6px 10px 8px;'>" + filas + "</div>"
                "</div>"
            )
            st.markdown(html_card, unsafe_allow_html=True)

    # ── SEPARADOR ────────────────────────────────────────
    with col_sep:
        st.markdown(
            "<div style='display:flex;align-items:center;justify-content:center;"
            "height:100%;padding-top:60px;font-size:1.4rem;color:#888;'>→</div>",
            unsafe_allow_html=True,
        )

    # ── DERECHA ──────────────────────────────────────────
    with col_der:
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Nueva fase</p>",
            unsafe_allow_html=True,
        )
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            plazas = plazas_por_grupo.get(g_id, [])

            # Cabecera tarjeta
            st.markdown(
                "<div style='background:#8b0000;border-radius:10px 10px 0 0;"
                "padding:8px 12px;display:flex;align-items:center;gap:6px;"
                "margin-bottom:2px;'>"
                "<div style='width:6px;height:6px;border-radius:50%;"
                "background:rgba(255,255,255,0.4);flex-shrink:0;'></div>"
                "<span style='font-size:0.7rem;font-weight:700;color:white;"
                "text-transform:uppercase;letter-spacing:0.06em;'>"
                + g_dest["nombre"] + "</span></div>",
                unsafe_allow_html=True,
            )

            for i in range(g_dest["tipo_grupo"]):
                ss_key = f"pcfg_{g_id}_{i}"
                plaza = plazas[i] if i < len(plazas) else None
                ref_bd = plaza.get("referencia_origen") if plaza else None

                # Opciones: Cualquier grupo + libres + el de esta plaza
                asignados_otros = get_asignados(excluir_key=ss_key)
                opciones = [_CUALQUIER_GRUPO] + sorted(
                    [g["nombre"] for g in grupos_origen
                     if g["nombre"] not in asignados_otros],
                    key=_num
                )

                # Si el valor actual no está en opciones, resetear
                if st.session_state[ss_key] not in opciones:
                    st.session_state[ss_key] = _CUALQUIER_GRUPO

                seleccion = st.selectbox(
                    f"Plaza {i+1}",
                    opciones,
                    key=ss_key,
                    label_visibility="collapsed",
                )

                # Guardar en BD si cambió respecto a lo que hay guardado
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
                            # Liberar siguiente_grupo_id del grupo anterior
                            if ref_bd and ref_bd != _CUALQUIER_GRUPO:
                                g_ant = next(
                                    (g for g in grupos_origen if g["nombre"] == ref_bd), None
                                )
                                if g_ant:
                                    supabase.table("grupos").update(
                                        {"siguiente_grupo_id": None}
                                    ).eq("id", g_ant["id"]).execute()
                        else:
                            supabase.table("participantes_grupo").insert({**payload, "puntos": 0, "goles": 0}).execute()

                        # Asignar siguiente_grupo_id al grupo origen
                        if seleccion != _CUALQUIER_GRUPO:
                            g_orig_match = next(
                                (g for g in grupos_origen if g["nombre"] == seleccion), None
                            )
                            if g_orig_match:
                                res = supabase.table("grupos").update(
                                    {"siguiente_grupo_id": g_id}
                                ).eq("id", g_orig_match["id"]).execute()
                                if not res.data:
                                    st.warning(f"No se pudo actualizar siguiente_grupo_id para {seleccion}")
                    except Exception as e:
                        st.error(f"Error al guardar plaza {i+1}: {e}")

            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

# -------------------------------------------------------

def renderizar_cuadro_progresion(
    grupos_destino,
    grupos_origen,
    participantes_por_grupo_destino,
    participantes_por_grupo_origen,
    ya_asignados_ids,
    fases,
    fase_actual,
    supabase,
):
    def _fila_equipo(nombre, escudo, ya_paso):
        bg = "rgba(255,255,255,0.04)" if ya_paso else "white"
        color = "#aaa" if ya_paso else "#1a1a1a"
        opacity = "0.4" if ya_paso else "1"
        tick = "<span style='margin-left:auto;font-size:10px;color:#3B6D11;font-weight:700;flex-shrink:0;'>✓</span>" if ya_paso else ""
        img = f'<img src="{escudo}" style="width:20px;height:20px;object-fit:contain;margin-right:8px;border-radius:3px;">' if escudo else '<div style="width:20px;margin-right:8px;"></div>'
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

    def _tarjeta(nombre_grupo, cuerpo_html, notas=""):
        notas_html = (
            f'<br/><em style="font-size:0.65rem;color:rgba(255,255,255,0.78);font-weight:400;letter-spacing:normal;text-transform:none;">{notas}</em>'
            if notas else ""
        )
        return (
            f'<div style="background:#8b0000;border-radius:10px;overflow:hidden;margin-bottom:4px;">'
            f'<div style="background:#cc0000;padding:8px 12px;display:flex;align-items:center;gap:6px;">'
            f'<div style="width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,0.4);flex-shrink:0;"></div>'
            f'<span style="font-size:0.7rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.06em;">{nombre_grupo}{notas_html}</span>'
            f'</div>'
            f'<div style="padding:6px 10px 8px;">{cuerpo_html}</div>'
            f'</div>'
        )

    col_izq, col_sep, col_der = st.columns([5, 1, 5])

    # ---- IZQUIERDA: fase anterior ----
    with col_izq:
        st.markdown("<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase anterior</p>", unsafe_allow_html=True)
        for g_orig in grupos_origen:
            participantes = participantes_por_grupo_origen.get(g_orig["id"], [])
            cuerpo = ""
            for p in participantes:
                if not p.get("equipo_id") or not p.get("equipos"):
                    continue
                cuerpo += _fila_equipo(
                    p["equipos"]["nombre"],
                    p["equipos"].get("escudo_url") or "",
                    p["equipo_id"] in ya_asignados_ids,
                )
            if not cuerpo:
                cuerpo = '<div style="font-size:0.7rem;color:rgba(255,255,255,0.3);font-style:italic;padding:4px 0;">Sin equipos asignados</div>'
            st.markdown(_tarjeta(g_orig["nombre"], cuerpo, g_orig.get("notas") or ""), unsafe_allow_html=True)

    # ---- SEPARADOR ----
    with col_sep:
        st.markdown("<div style='display:flex;align-items:center;justify-content:center;height:100%;padding-top:60px;font-size:1.4rem;color:#888;'>→</div>", unsafe_allow_html=True)

    # ---- DERECHA: fase actual ----
    with col_der:
        st.markdown("<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:#888;margin-bottom:10px;'>Fase actual</p>", unsafe_allow_html=True)
        for g_dest in grupos_destino:
            g_id = g_dest["id"]
            capacidad = g_dest["tipo_grupo"]
            participantes = participantes_por_grupo_destino.get(g_id, [])
            n_asignados = sum(1 for p in participantes if p.get("equipo_id"))
            grupo_lleno = n_asignados >= capacidad

            # Construir cuerpo HTML de la tarjeta destino
            cuerpo = ""
            for p in participantes:
                if p.get("equipo_id") and p.get("equipos"):
                    cuerpo += _fila_equipo(p["equipos"]["nombre"], p["equipos"].get("escudo_url") or "", False)
            for _ in range(capacidad - n_asignados):
                cuerpo += _fila_hueco()

            st.markdown(_tarjeta(g_dest["nombre"], cuerpo, g_dest.get("notas") or ""), unsafe_allow_html=True)

            # Vaciar o selectbox
            if grupo_lleno:
                if st.button("⊘  Vaciar grupo", key=f"vaciar_{g_id}", width='stretch'):
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
                    col_no.button(
                        "Cancelar",
                        key=f"no_vaciar_{g_id}",
                        on_click=_cancelar_confirm,
                        args=[f"confirmar_vaciar_{g_id}"],
                    )
            else:
                plazas_vacias = [p for p in participantes if not p.get("equipo_id")]
                if not plazas_vacias:
                    st.caption("Sin plazas configuradas. Ve al Configurador.")
                else:
                    p_actual = plazas_vacias[0]
                    ref = p_actual.get("referencia_origen") or _CUALQUIER_GRUPO
                    try:
                        if ref == _CUALQUIER_GRUPO:
                            todos_ant = [
                                p for plist in participantes_por_grupo_origen.values()
                                for p in plist
                                if p.get("equipos") and p.get("equipo_id")
                                and p["equipo_id"] not in ya_asignados_ids
                            ]
                            candidatos = [p["equipos"] for p in todos_ant]
                        else:
                            g_orig_match = next((g for g in grupos_origen if g["nombre"] == ref), None)
                            candidatos = [
                                p["equipos"]
                                for p in participantes_por_grupo_origen.get(g_orig_match["id"] if g_orig_match else -1, [])
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
                            e_match = next((c for c in candidatos if c["nombre"] == seleccion), None)
                            if e_match:
                                supabase.table("participantes_grupo").update({"equipo_id": e_match["id"]}).eq("id", p_actual["id"]).execute()
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error cargando candidatos: {e}")

            notas_key = f"notas_{g_id}"
            if notas_key not in st.session_state:
                st.session_state[notas_key] = g_dest.get("notas") or ""
            st.text_input(
                "notas_input",
                key=notas_key,
                on_change=_guardar_notas_grupo,
                args=[g_id, notas_key],
                placeholder="📍 Campo · ⏰ Hora · 👤 Árbitro...",
                label_visibility="collapsed",
            )
            st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

# -------------------------------------------------------
# -------------------------------------------------------
# TARJETA DE GRUPO — dark/deportiva, un botón por grupo
# -------------------------------------------------------

def renderizar_tarjeta_grupo_minimalista(
    grupo, participantes, equipos_libres, es_progresion, fases, fase_actual, supabase
):
    """
    Tarjeta dark/deportiva.
    - Grupo incompleto → botón "＋ Asignar equipos" + un único selectbox que inserta
      de uno en uno hasta llenar el grupo.
    - Grupo completo   → botón "Vaciar grupo" con confirmación.
    """
    grupo_id = grupo["id"]
    capacidad = grupo["tipo_grupo"]
    asignados = [p for p in participantes if p and p.get("equipo_id")]
    grupo_lleno = len(asignados) >= capacidad
    notas = grupo.get("notas") or ""

    notas_html = (
        f'<br/><em style="font-size:0.65rem;color:rgba(255,255,255,0.78);'
        f'font-weight:400;letter-spacing:normal;text-transform:none;">{notas}</em>'
        if notas else ""
    )

    # Equipos asignados primero, huecos al final — evita que filas nulas anteriores
    # bloqueen el acceso por índice a equipos recién añadidos.
    participantes = sorted(participantes, key=lambda p: (0 if p and p.get("equipo_id") else 1))

    # --- Tarjeta HTML ---
    st.markdown(f"""
        <div style="background:#8b0000;border-radius:12px;overflow:hidden;margin-bottom:4px;">
            <div style="background:#cc0000;padding:10px 14px;display:flex;align-items:center;gap:8px;">
                <div style="width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,0.35);flex-shrink:0;"></div>
                <span style="font-size:0.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:0.07em;">
                    {grupo['nombre']}{notas_html}
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
            col_equipo, col_rm = st.columns([11, 1])
            with col_equipo:
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
            with col_rm:
                if st.button("✕", key=f"rm_{grupo_id}_{i}", help=f"Quitar {nombre_equipo}"):
                    try:
                        supabase.table("participantes_grupo").delete().eq("id", p_actual["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al quitar: {e}")
        else:
            st.markdown("""
                <div style="border:1px dashed rgba(255,255,255,0.3);border-radius:6px;
                            background:rgba(0,0,0,0.15);height:34px;margin-bottom:5px;"></div>
            """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    # --- Botón único ---
    if grupo_lleno:
        if st.button("⊘  Vaciar grupo", key=f"vaciar_{grupo_id}", width='stretch'):
            st.session_state[f"confirmar_vaciar_{grupo_id}"] = True

        if st.session_state.get(f"confirmar_vaciar_{grupo_id}", False):
            st.warning(f"¿Borrar todos los equipos de {grupo['nombre']}?")
            col_si, col_no = st.columns(2)
            if col_si.button("Sí, vaciar", key=f"si_vaciar_{grupo_id}", type="primary"):
                try:
                    if es_progresion:
                        # Conservar referencia_origen; solo quitar el equipo asignado
                        supabase.table("participantes_grupo").update({"equipo_id": None}).eq("grupo_id", grupo_id).execute()
                    else:
                        # En sorteo no hay referencia_origen que preservar; borrar filas
                        # para que el siguiente INSERT empiece desde cero sin filas huérfanas
                        supabase.table("participantes_grupo").delete().eq("grupo_id", grupo_id).execute()
                    st.session_state.pop(f"confirmar_vaciar_{grupo_id}", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al vaciar: {e}")
            col_no.button(
                "Cancelar",
                key=f"no_vaciar_{grupo_id}",
                on_click=_cancelar_confirm,
                args=[f"confirmar_vaciar_{grupo_id}"],
            )
    else:
        # Grupo incompleto — selectbox directo, sin botón ni label
        if not es_progresion:
            opciones = ["— añadir equipo —"] + [e["nombre"] for e in equipos_libres]
            seleccion = st.selectbox(
                f"sel_label_{grupo_id}",
                opciones,
                key=f"sel_{grupo_id}",
                label_visibility="collapsed",
            )
            if seleccion != opciones[0]:
                try:
                    e_match = next((e for e in equipos_libres if e["nombre"] == seleccion), None)
                    if not e_match:
                        st.error("Equipo no encontrado. Recarga la página e inténtalo de nuevo.")
                    else:
                        supabase.table("participantes_grupo").insert({
                            "grupo_id": grupo_id,
                            "equipo_id": e_match["id"],
                            "referencia_origen": "Sorteo",
                            "puntos": 0,
                            "goles":  0,
                        }).execute()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al asignar: {e}")
        else:
            plazas_vacias = [
                (i, participantes[i] if i < len(participantes) else None)
                for i in range(capacidad)
                if not (i < len(participantes) and participantes[i] and participantes[i].get("equipo_id"))
            ]
            for i, p_actual in plazas_vacias:
                if p_actual and p_actual.get("referencia_origen"):
                    ref = p_actual["referencia_origen"]
                    try:
                        f_ant = next(f for f in fases if f["orden"] == fase_actual["orden"] - 1)
                        if ref == _CUALQUIER_GRUPO:
                            # Todos los equipos de la fase anterior no asignados aún
                            grupos_ant = (
                                supabase.table("grupos")
                                .select("id")
                                .eq("fase_id", f_ant["id"])
                                .execute()
                                .data
                            )
                            ids_grupos_ant = [g["id"] for g in grupos_ant]
                            ya_asignados = set()
                            res_cand = (
                                supabase.table("participantes_grupo")
                                .select("equipos(id, nombre)")
                                .in_("grupo_id", ids_grupos_ant)
                                .execute()
                            )
                            candidatos = [
                                p["equipos"] for p in res_cand.data
                                if p["equipos"] and p["equipos"]["id"] not in ya_asignados
                            ]
                        else:
                            # Solo equipos del grupo origen configurado
                            res_g = (
                                supabase.table("grupos")
                                .select("id")
                                .eq("nombre", ref)
                                .eq("fase_id", f_ant["id"])
                                .execute()
                            )
                            if not res_g.data:
                                st.warning(f"Grupo '{ref}' no encontrado en la fase anterior.")
                                continue
                            res_cand = (
                                supabase.table("participantes_grupo")
                                .select("equipos(id, nombre)")
                                .eq("grupo_id", res_g.data[0]["id"])
                                .execute()
                            )
                            candidatos = [p["equipos"] for p in res_cand.data if p["equipos"]]

                        opciones = ["— elige equipo —"] + [c["nombre"] for c in candidatos]
                        sel = st.selectbox(
                            f"Plaza {i + 1}",
                            opciones,
                            key=f"sel_prog_{grupo_id}_{i}",
                            label_visibility="collapsed",
                        )
                        if sel != opciones[0]:
                            try:
                                e_match = next((c for c in candidatos if c["nombre"] == sel), None)
                                if not e_match:
                                    st.error("Equipo no encontrado. Recarga la página e inténtalo de nuevo.")
                                else:
                                    supabase.table("participantes_grupo").update(
                                        {"equipo_id": e_match["id"]}
                                    ).eq("id", p_actual["id"]).execute()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error al asignar: {e}")
                    except Exception as e:
                        st.error(f"Error cargando candidatos: {e}")

    # --- Campo de notas editable ---
    notas_key = f"notas_{grupo_id}"
    if notas_key not in st.session_state:
        st.session_state[notas_key] = notas
    st.text_input(
        "notas_input",
        key=notas_key,
        on_change=_guardar_notas_grupo,
        args=[grupo_id, notas_key],
        placeholder="📍 Campo · ⏰ Hora · 👤 Árbitro...",
        label_visibility="collapsed",
    )

# -------------------------------------------------------
# TARJETAS DE EQUIPOS (vista escritorio)
# -------------------------------------------------------

def renderizar_tarjetas_equipos(lista_equipos, editable=False, on_edit=None):
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
                            margin-bottom: 4px; text-align: center;
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
            if editable and on_edit:
                if st.button("✏️ Editar", key=f"edit_eq_{equipo['id']}", width='stretch'):
                    on_edit(equipo)