import streamlit as st
from supabase import create_client, Client
from typing import Any


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# -------------------------------------------------------
# TORNEOS
# -------------------------------------------------------

def get_torneos() -> list[dict[str, Any]]:
    supabase = get_supabase()
    return supabase.table("torneos").select("*").order("created_at").execute().data  # type: ignore[return-value]


def crear_torneo(nombre: str, descripcion: str = "") -> list[dict[str, Any]]:
    supabase = get_supabase()
    return supabase.table("torneos").insert({  # type: ignore[return-value]
        "nombre": nombre,
        "descripcion": descripcion,
        "activo": True,
    }).execute().data


def eliminar_torneo(torneo_id):
    supabase = get_supabase()
    supabase.table("torneos").delete().eq("id", torneo_id).execute()
    st.cache_data.clear()


# -------------------------------------------------------
# EQUIPOS
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_equipos(torneo_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return (  # type: ignore[return-value]
        supabase.table("equipos")
        .select("*")
        .eq("torneo_id", torneo_id)
        .order("nombre")
        .execute()
        .data
    )


def get_equipos_libres(torneo_id: str, ocupados_ids: set[str] | None = None) -> list[dict[str, Any]]:
    supabase = get_supabase()
    equipos: list[dict[str, Any]] = (  # type: ignore[assignment]
        supabase.table("equipos")
        .select("id, nombre")
        .eq("eliminado", False)
        .eq("torneo_id", torneo_id)
        .execute()
        .data
    )
    if ocupados_ids:
        equipos = [e for e in equipos if e["id"] not in ocupados_ids]
    return equipos


def subir_equipos_batch(lista_equipos, torneo_id):
    supabase = get_supabase()
    try:
        equipos_con_torneo = [{**e, "torneo_id": torneo_id} for e in lista_equipos]
        result = supabase.table("equipos").insert(equipos_con_torneo).execute()
        st.cache_data.clear()
        return result
    except Exception as e:
        return f"Error: {e}"


def patch_equipo(equipo_id, campos: dict):
    """Actualiza solo los campos proporcionados (merge); no toca los que no vienen."""
    if not campos:
        return
    supabase = get_supabase()
    supabase.table("equipos").update(campos).eq("id", equipo_id).execute()
    st.cache_data.clear()


def update_equipo(equipo_id, nombre, escudo_url, competicion=None, grupo=None):
    supabase = get_supabase()
    supabase.table("equipos").update({
        "nombre":      nombre,
        "escudo_url":  escudo_url or None,
        "competicion": competicion or None,
        "grupo":       grupo or None,
    }).eq("id", equipo_id).execute()
    st.cache_data.clear()


# -------------------------------------------------------
# FASES
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_fases(torneo_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return (  # type: ignore[return-value]
        supabase.table("fases")
        .select("*")
        .eq("torneo_id", torneo_id)
        .order("orden")
        .execute()
        .data
    )


def crear_fase(nombre, orden, torneo_id):
    supabase = get_supabase()
    result = supabase.table("fases").insert({
        "nombre": nombre,
        "orden": orden,
        "torneo_id": torneo_id,
    }).execute().data
    st.cache_data.clear()
    return result


# -------------------------------------------------------
# GRUPOS
# -------------------------------------------------------

@st.cache_data(ttl=30)
def get_grupos_por_fase(fase_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return supabase.table("grupos").select("*").eq("fase_id", fase_id).execute().data  # type: ignore[return-value]


def crear_grupos(grupos_list):
    supabase = get_supabase()
    result = supabase.table("grupos").insert(grupos_list).execute().data
    st.cache_data.clear()
    return result


def actualizar_grupo(grupo_id, nombre, tipo_grupo, orden_cuadro):
    supabase = get_supabase()
    supabase.table("grupos").update({
        "nombre": nombre,
        "tipo_grupo": tipo_grupo,
        "orden_cuadro": orden_cuadro,
    }).eq("id", grupo_id).execute()
    st.cache_data.clear()


def eliminar_grupo(grupo_id):
    supabase = get_supabase()
    # Romper FK auto-referencial antes de borrar
    supabase.table("grupos").update({"siguiente_grupo_id": None}).eq("siguiente_grupo_id", grupo_id).execute()
    supabase.table("participantes_grupo").delete().eq("grupo_id", grupo_id).execute()
    supabase.table("grupos").delete().eq("id", grupo_id).execute()
    st.cache_data.clear()


def contar_grupos_fase(fase_id):
    supabase = get_supabase()
    res = supabase.table("grupos").select("id", count="exact").eq("fase_id", fase_id).execute()
    return res.count or 0


# -------------------------------------------------------
# PARTICIPANTES
# -------------------------------------------------------

def get_participantes_grupo(grupo_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return (  # type: ignore[return-value]
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )


def get_participantes_grupos(ids_grupos: list[str]) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return (  # type: ignore[return-value]
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .in_("grupo_id", ids_grupos)
        .order("created_at", desc=False)
        .execute()
        .data
    )


# -------------------------------------------------------
# PARTIDOS
# -------------------------------------------------------

def _round_robin(equipo_ids, num_vueltas=1):
    """Circle-method round-robin. Returns [{local, visitante, jornada}, ...]"""
    teams = list(equipo_ids)
    if len(teams) < 2:
        return []
    if len(teams) % 2 == 1:
        teams.append(None)          # bye
    n = len(teams)
    matches = []
    for r in range(n - 1):
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            if home is not None and away is not None:
                matches.append({"local": home, "visitante": away, "jornada": r + 1})
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    if num_vueltas == 2:
        num_jornadas_ida = n - 1
        matches += [
            {"local": m["visitante"], "visitante": m["local"],
             "jornada": m["jornada"] + num_jornadas_ida}
            for m in matches
        ]
    return matches


def actualizar_num_vueltas(fase_id, num_vueltas):
    supabase = get_supabase()
    supabase.table("fases").update({"num_vueltas": num_vueltas}).eq("id", fase_id).execute()
    st.cache_data.clear()


def set_fase_oculta_bracket(fase_id, oculta: bool):
    supabase = get_supabase()
    supabase.table("fases").update({"oculta_bracket": oculta}).eq("id", fase_id).execute()
    st.cache_data.clear()


def hay_partidos_fase(fase_id):
    supabase = get_supabase()
    grupos = supabase.table("grupos").select("id").eq("fase_id", fase_id).execute().data
    if not grupos:
        return False
    ids = [g["id"] for g in grupos]
    res = supabase.table("partidos").select("id", count="exact").in_("grupo_id", ids).execute()
    return (res.count or 0) > 0


def eliminar_partidos_fase(fase_id):
    supabase = get_supabase()
    grupos = supabase.table("grupos").select("id").eq("fase_id", fase_id).execute().data
    if not grupos:
        return
    ids = [g["id"] for g in grupos]
    supabase.table("partidos").delete().in_("grupo_id", ids).execute()
    st.cache_data.clear()


def _label_placeholder(pos, grupo_nombre, feeders):
    """Etiqueta para un hueco sin equipo asignado."""
    if feeders:
        if pos <= len(feeders):
            return f"1º {feeders[pos - 1]['nombre']}"
        return f"P{pos} {grupo_nombre}"
    return f"{grupo_nombre}_E{pos}"


def generar_partidos_fase(fase_id, num_vueltas):
    supabase = get_supabase()

    # Datos de la fase para conocer orden y torneo
    fase_data = supabase.table("fases").select("orden, torneo_id").eq("id", fase_id).execute().data
    if not fase_data:
        return 0
    fase_orden   = fase_data[0]["orden"]
    torneo_id    = fase_data[0]["torneo_id"]

    grupos = supabase.table("grupos").select("id, nombre, tipo_grupo, orden_cuadro").eq("fase_id", fase_id).execute().data

    # Para fases de progresión: mapa grupo_destino → [grupos_origen ordenados]
    feeder_map = {}
    if fase_orden > 1:
        prev = supabase.table("fases").select("id").eq("torneo_id", torneo_id).eq("orden", fase_orden - 1).execute().data
        if prev:
            prev_grupos = (
                supabase.table("grupos")
                .select("id, nombre, siguiente_grupo_id, orden_cuadro")
                .eq("fase_id", prev[0]["id"])
                .execute()
                .data
            )
            for pg in sorted(prev_grupos, key=lambda g: (g.get("orden_cuadro") or 9999, g["nombre"])):
                sid = pg.get("siguiente_grupo_id")
                if sid:
                    feeder_map.setdefault(sid, []).append(pg)

    total = 0
    for g in grupos:
        grupo_id  = g["id"]
        tipo      = g["tipo_grupo"] or 0
        feeders   = feeder_map.get(grupo_id, [])

        # Participantes reales ya asignados
        parts = (
            supabase.table("participantes_grupo")
            .select("id, equipo_id, posicion")
            .eq("grupo_id", grupo_id)
            .execute()
            .data
        )
        real_ids = [p["equipo_id"] for p in parts if p.get("equipo_id")]

        if real_ids:
            # ── Modo real: equipos ya asignados ──────────────────
            if len(real_ids) < 2:
                continue
            rows = [
                {
                    "grupo_id":            grupo_id,
                    "equipo_local_id":     m["local"],
                    "equipo_visitante_id": m["visitante"],
                    "pos_local":           None,
                    "pos_visitante":       None,
                    "jornada":             m["jornada"],
                }
                for m in _round_robin(real_ids, num_vueltas)
            ]
        else:
            # ── Modo placeholder ──────────────────────────────────
            n = len(feeders) if feeders else tipo
            if n < 2:
                continue

            # Crear/actualizar filas NULL con posición y etiqueta
            null_parts = [p for p in parts if not p.get("equipo_id")]
            existing_pos = {p["posicion"] for p in null_parts if p.get("posicion")}
            for pos in range(1, n + 1):
                label = _label_placeholder(pos, g["nombre"], feeders)
                if pos not in existing_pos:
                    supabase.table("participantes_grupo").insert({
                        "grupo_id": grupo_id,
                        "equipo_id": None,
                        "posicion":  pos,
                        "label":     label,
                        "puntos":    0,
                        "goles":     0,
                    }).execute()
                else:
                    # Actualizar label por si el nombre del grupo cambió
                    row = next(p for p in null_parts if p["posicion"] == pos)
                    supabase.table("participantes_grupo").update({"label": label}).eq("id", row["id"]).execute()

            rows = [
                {
                    "grupo_id":            grupo_id,
                    "equipo_local_id":     None,
                    "equipo_visitante_id": None,
                    "pos_local":           m["local"],
                    "pos_visitante":       m["visitante"],
                    "jornada":             m["jornada"],
                }
                for m in _round_robin(list(range(1, n + 1)), num_vueltas)
            ]

        supabase.table("partidos").insert(rows).execute()
        total += len(rows)

    st.cache_data.clear()
    return total


def sincronizar_equipos_partidos_grupo(grupo_id):
    """Rellena equipo_local/visitante_id en partidos placeholder cuando ya hay equipo en esa posición."""
    supabase = get_supabase()

    parts = (
        supabase.table("participantes_grupo")
        .select("equipo_id, posicion")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )
    pos_map = {p["posicion"]: p["equipo_id"] for p in parts if p.get("posicion") and p.get("equipo_id")}
    if not pos_map:
        return 0

    partidos = (
        supabase.table("partidos")
        .select("id, pos_local, pos_visitante, equipo_local_id, equipo_visitante_id")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )
    updated = 0
    for p in partidos:
        upd = {}
        if p.get("pos_local") and not p.get("equipo_local_id") and p["pos_local"] in pos_map:
            upd["equipo_local_id"] = pos_map[p["pos_local"]]
        if p.get("pos_visitante") and not p.get("equipo_visitante_id") and p["pos_visitante"] in pos_map:
            upd["equipo_visitante_id"] = pos_map[p["pos_visitante"]]
        if upd:
            supabase.table("partidos").update(upd).eq("id", p["id"]).execute()
            updated += 1

    st.cache_data.clear()
    return updated


def sincronizar_equipos_partidos_fase(fase_id):
    """Sincroniza todos los grupos de una fase."""
    supabase = get_supabase()
    grupos = supabase.table("grupos").select("id").eq("fase_id", fase_id).execute().data
    total = sum(sincronizar_equipos_partidos_grupo(g["id"]) for g in grupos)
    st.cache_data.clear()
    return total


def get_partidos_fase(fase_id):
    """Devuelve {grupo_id: {nombre, orden_cuadro, partidos}} con nombres resueltos (reales o placeholders)."""
    supabase = get_supabase()
    grupos = supabase.table("grupos").select("id, nombre, orden_cuadro").eq("fase_id", fase_id).execute().data
    if not grupos:
        return {}
    ids_grupos = [g["id"] for g in grupos]

    partidos = (
        supabase.table("partidos")
        .select("*")
        .in_("grupo_id", ids_grupos)
        .order("jornada")
        .execute()
        .data
    )
    if not partidos:
        return {}

    # Etiquetas placeholder: (grupo_id, posicion) → label
    all_parts = (
        supabase.table("participantes_grupo")
        .select("grupo_id, posicion, label")
        .in_("grupo_id", ids_grupos)
        .execute()
        .data
    )
    label_map = {
        (p["grupo_id"], p["posicion"]): (p.get("label") or f"E{p['posicion']}")
        for p in all_parts if p.get("posicion")
    }

    # Nombres de equipos reales
    eq_ids = [p for p in (
        {p["equipo_local_id"] for p in partidos if p.get("equipo_local_id")} |
        {p["equipo_visitante_id"] for p in partidos if p.get("equipo_visitante_id")}
    )]
    eq_map = {}
    if eq_ids:
        eq_map = {
            e["id"]: e["nombre"]
            for e in supabase.table("equipos").select("id, nombre").in_("id", eq_ids).execute().data
        }

    grupo_meta = {g["id"]: {"nombre": g["nombre"], "orden_cuadro": g.get("orden_cuadro")} for g in grupos}
    result = {}
    for p in partidos:
        gid = p["grupo_id"]
        if p.get("equipo_local_id"):
            p["nombre_local"] = eq_map.get(p["equipo_local_id"], "?")
        else:
            p["nombre_local"] = label_map.get((gid, p.get("pos_local")), f"E{p.get('pos_local', '?')}")

        if p.get("equipo_visitante_id"):
            p["nombre_visitante"] = eq_map.get(p["equipo_visitante_id"], "?")
        else:
            p["nombre_visitante"] = label_map.get((gid, p.get("pos_visitante")), f"E{p.get('pos_visitante', '?')}")

        result.setdefault(gid, {"nombre": grupo_meta[gid]["nombre"], "orden_cuadro": grupo_meta[gid]["orden_cuadro"], "partidos": []})
        result[gid]["partidos"].append(p)
    return result


def actualizar_partidos_batch(updates):
    """updates: [{id, campo, hora, resultado_local, resultado_visitante}, ...]"""
    supabase = get_supabase()
    for u in updates:
        pid = u.pop("id", None)
        if not pid:
            continue
        data = {k: v for k, v in u.items()}
        supabase.table("partidos").update(data).eq("id", pid).execute()


# -------------------------------------------------------
# AGENDA (multi-torneo)
# -------------------------------------------------------

def get_campos_distintos():
    """Devuelve lista de campos únicos con partido asignado."""
    supabase = get_supabase()
    rows = supabase.table("partidos").select("campo").not_.is_("campo", "null").execute().data
    return sorted({r["campo"] for r in rows if r.get("campo")})


def get_partidos_agenda(fecha_desde=None, fecha_hasta=None, campos=None, torneo_ids=None):
    """
    Devuelve lista de partidos con fecha asignada, enriquecidos con nombres de
    equipos, grupo y torneo. Filtros opcionales: rango de fechas, lista de campos,
    lista de torneo_ids.
    """
    supabase = get_supabase()

    # Construir mapa grupo_id → {torneo_nombre, grupo_nombre}
    fases_q = supabase.table("fases").select("id, torneo_id, torneos(id, nombre)").execute().data
    if torneo_ids:
        fases_q = [f for f in fases_q if f["torneo_id"] in torneo_ids]
    if not fases_q:
        return []

    fase_ids = [f["id"] for f in fases_q]
    torneo_nombre_map = {f["id"]: (f.get("torneos") or {}).get("nombre", "?") for f in fases_q}

    grupos_q = (
        supabase.table("grupos")
        .select("id, nombre, fase_id")
        .in_("fase_id", fase_ids)
        .execute()
        .data
    )
    if not grupos_q:
        return []

    grupo_meta = {
        g["id"]: {"grupo": g["nombre"], "torneo": torneo_nombre_map.get(g["fase_id"], "?")}
        for g in grupos_q
    }
    grupo_ids = list(grupo_meta.keys())

    # Query principal de partidos
    q = (
        supabase.table("partidos")
        .select("id, fecha, hora, campo, jornada, equipo_local_id, equipo_visitante_id, pos_local, pos_visitante, resultado_local, resultado_visitante, grupo_id")
        .in_("grupo_id", grupo_ids)
        .not_.is_("fecha", "null")
        .order("fecha")
        .order("hora")
    )
    if fecha_desde:
        q = q.gte("fecha", str(fecha_desde))
    if fecha_hasta:
        q = q.lte("fecha", str(fecha_hasta))
    if campos:
        # filtramos en cliente para soportar lista de valores
        pass

    partidos = q.execute().data

    if not partidos:
        return []

    # Filtro de campos en cliente (lista múltiple)
    if campos:
        partidos = [p for p in partidos if p.get("campo") in campos]
        if not partidos:
            return []

    # Resolver nombres de equipos (solo IDs reales, sin NULLs)
    eq_ids = list(
        {p["equipo_local_id"] for p in partidos if p.get("equipo_local_id")} |
        {p["equipo_visitante_id"] for p in partidos if p.get("equipo_visitante_id")}
    )
    eq_map = {}
    if eq_ids:
        eq_map = {
            e["id"]: e["nombre"]
            for e in supabase.table("equipos").select("id, nombre").in_("id", eq_ids).execute().data
        }

    # Etiquetas placeholder: (grupo_id, posicion) → label
    label_map = {}
    if grupo_ids:
        ph_parts = (
            supabase.table("participantes_grupo")
            .select("grupo_id, posicion, label")
            .in_("grupo_id", grupo_ids)
            .execute()
            .data
        )
        label_map = {
            (p["grupo_id"], p["posicion"]): (p.get("label") or f"E{p['posicion']}")
            for p in ph_parts if p.get("posicion")
        }

    for p in partidos:
        meta = grupo_meta.get(p["grupo_id"], {})
        gid  = p["grupo_id"]

        if p.get("equipo_local_id"):
            p["nombre_local"] = eq_map.get(p["equipo_local_id"], "?")
        else:
            p["nombre_local"] = label_map.get((gid, p.get("pos_local")), f"E{p.get('pos_local', '?')}")

        if p.get("equipo_visitante_id"):
            p["nombre_visitante"] = eq_map.get(p["equipo_visitante_id"], "?")
        else:
            p["nombre_visitante"] = label_map.get((gid, p.get("pos_visitante")), f"E{p.get('pos_visitante', '?')}")
        p["nombre_torneo"]    = meta.get("torneo", "?")
        p["nombre_grupo"]     = meta.get("grupo", "")

    return partidos