import streamlit as st
import uuid
import functools
import httpx
from supabase import create_client, Client
from typing import Any

_supabase_client: Client | None = None


def _reset_supabase() -> None:
    global _supabase_client
    _supabase_client = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        _supabase_client = create_client(url, key)
    return _supabase_client


def _db_retry(fn):
    """Reintenta una vez recreando el cliente si la conexión falla."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except httpx.ReadError:
            _reset_supabase()
            return fn(*args, **kwargs)
    return wrapper


def subir_escudo(fichero) -> str:
    """Sube un fichero de imagen al bucket 'escudos' y devuelve su URL pública."""
    supabase = get_supabase()
    ext = fichero.name.rsplit(".", 1)[-1].lower()
    nombre_unico = f"{uuid.uuid4()}.{ext}"
    supabase.storage.from_("escudos").upload(
        path=nombre_unico,
        file=fichero.getvalue(),
        file_options={"content-type": fichero.type, "upsert": "true"},
    )
    return supabase.storage.from_("escudos").get_public_url(nombre_unico)  # type: ignore[return-value]


# -------------------------------------------------------
# TORNEOS
# -------------------------------------------------------

@_db_retry
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


def set_visible_bracket(torneo_id, visible: bool):
    supabase = get_supabase()
    supabase.table("torneos").update({"visible_bracket": visible}).eq("id", torneo_id).execute()
    st.cache_data.clear()


def set_orden_menu(torneo_id, orden: int | None):
    supabase = get_supabase()
    supabase.table("torneos").update({"orden_menu": orden}).eq("id", torneo_id).execute()
    st.cache_data.clear()


def eliminar_torneo(torneo_id):
    supabase = get_supabase()

    # 1. Fases del torneo
    fases = supabase.table("fases").select("id").eq("torneo_id", torneo_id).execute().data
    fase_ids = [f["id"] for f in fases]

    if fase_ids:
        # 2. Grupos de esas fases
        grupos = supabase.table("grupos").select("id").in_("fase_id", fase_ids).execute().data
        grupo_ids = [g["id"] for g in grupos]

        if grupo_ids:
            # 3. Partidos y participantes de esos grupos
            supabase.table("partidos").delete().in_("grupo_id", grupo_ids).execute()
            supabase.table("participantes_grupo").delete().in_("grupo_id", grupo_ids).execute()

        # 4. Grupos
        supabase.table("grupos").delete().in_("fase_id", fase_ids).execute()

    # 5. Fases
    supabase.table("fases").delete().eq("torneo_id", torneo_id).execute()

    # 6. Equipos
    supabase.table("equipos").delete().eq("torneo_id", torneo_id).execute()

    # 7. Torneo
    supabase.table("torneos").delete().eq("id", torneo_id).execute()

    st.cache_data.clear()


# -------------------------------------------------------
# EQUIPOS
# -------------------------------------------------------

@st.cache_data(ttl=30)
@_db_retry
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


@_db_retry
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
@_db_retry
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
@_db_retry
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

@_db_retry
def get_participantes_grupo(grupo_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    return (  # type: ignore[return-value]
        supabase.table("participantes_grupo")
        .select("*, equipos(id, nombre, escudo_url)")
        .eq("grupo_id", grupo_id)
        .execute()
        .data
    )


@_db_retry
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

# Calendarios fijos por número de equipos (índices 0-based sobre la lista ordenada por posición)
# Cada tupla: (idx_local, idx_visitante, jornada)
_FIXED_SCHEDULE = {
    3: [
        (0, 2, 1),  # J1: E1 vs E3
        (1, 0, 2),  # J2: E2 vs E1
        (2, 1, 3),  # J3: E3 vs E2
    ],
    4: [
        (0, 2, 1),  # J1: E1 vs E3
        (3, 1, 1),  # J1: E4 vs E2
        (3, 2, 2),  # J2: E4 vs E3
        (1, 0, 2),  # J2: E2 vs E1
        (2, 1, 3),  # J3: E3 vs E2
        (0, 3, 3),  # J3: E1 vs E4
    ],
}


def _round_robin(equipo_ids, num_vueltas=1):
    """Genera el calendario de partidos respetando el orden de equipos recibido."""
    teams = list(equipo_ids)
    n = len(teams)
    if n < 2:
        return []

    schedule = _FIXED_SCHEDULE.get(n)
    if schedule:
        matches = [
            {"local": teams[l], "visitante": teams[v], "jornada": j}
            for l, v, j in schedule
            if teams[l] is not None and teams[v] is not None
        ]
        if num_vueltas == 2:
            max_j = max(j for _, _, j in schedule)
            matches += [
                {"local": m["visitante"], "visitante": m["local"],
                 "jornada": m["jornada"] + max_j}
                for m in matches
            ]
        return matches

    # Método del círculo para cualquier otro número de equipos
    if n % 2 == 1:
        teams.append(None)
        n += 1
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


def actualizar_duracion_fase(fase_id, duracion: int | None):
    supabase = get_supabase()
    supabase.table("fases").update({"duracion_partido": duracion}).eq("id", fase_id).execute()
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


def limpiar_resultados_grupo(grupo_id):
    """Borra los resultados de un grupo: partidos (tipo_grupo>2) y goles/penaltis (tipo_grupo=2)."""
    supabase = get_supabase()
    # tipo_grupo > 2: resultados en tabla partidos
    supabase.table("partidos").update({
        "resultado_local": None,
        "resultado_visitante": None,
        "penaltis_ganador_id": None,
    }).eq("grupo_id", grupo_id).execute()
    # tipo_grupo = 2: goles en participantes_grupo
    supabase.table("participantes_grupo").update({
        "goles": None,
    }).eq("grupo_id", grupo_id).execute()
    # tipo_grupo = 2: penaltis en grupos
    supabase.table("grupos").update({
        "penaltis": False,
        "penaltis_ganador_id": None,
    }).eq("id", grupo_id).execute()
    st.cache_data.clear()


def _label_placeholder(pos, grupo_nombre, feeders, n=None):
    """Etiqueta para un hueco sin equipo asignado."""
    if not feeders:
        return f"{grupo_nombre}_E{pos}"
    # How many teams each feeder contributes
    tpf = max(1, (n or len(feeders)) // len(feeders))
    feeder_idx = min((pos - 1) // tpf, len(feeders) - 1)
    rank = (pos - 1) % tpf + 1
    return f"{rank}º {feeders[feeder_idx]['nombre']}"


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
        real_ids = [p["equipo_id"] for p in sorted(parts, key=lambda p: p.get("posicion") or 0) if p.get("equipo_id")]

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
            n = tipo
            if n < 2:
                continue

            # Crear/actualizar filas NULL con posición y etiqueta
            null_parts = [p for p in parts if not p.get("equipo_id")]
            existing_pos = {p["posicion"] for p in null_parts if p.get("posicion")}
            for pos in range(1, n + 1):
                label = _label_placeholder(pos, g["nombre"], feeders, n)
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


@_db_retry
def get_partidos_fase(fase_id):
    """Devuelve {grupo_id: {nombre, orden_cuadro, partidos, partidos_siguiente}} con nombres resueltos."""
    supabase = get_supabase()
    grupos = supabase.table("grupos").select("id, nombre, orden_cuadro, siguiente_grupo_id").eq("fase_id", fase_id).execute().data
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

    # IDs de grupos de la siguiente fase referenciados por algún grupo actual
    sig_grupo_ids = list({g["siguiente_grupo_id"] for g in grupos if g.get("siguiente_grupo_id")})

    # Partidos de los grupos de la siguiente fase (puede estar vacío si aún no se han generado)
    partidos_sig = []
    sig_grupo_meta = {}
    sig_label_map = {}
    if sig_grupo_ids:
        partidos_sig = (
            supabase.table("partidos")
            .select("*")
            .in_("grupo_id", sig_grupo_ids)
            .order("jornada")
            .execute()
            .data
        )
        sig_grupos_data = supabase.table("grupos").select("id, nombre").in_("id", sig_grupo_ids).execute().data
        sig_grupo_meta = {g["id"]: g["nombre"] for g in sig_grupos_data}

        sig_parts = (
            supabase.table("participantes_grupo")
            .select("grupo_id, posicion, label")
            .in_("grupo_id", sig_grupo_ids)
            .execute()
            .data
        )
        sig_label_map = {
            (p["grupo_id"], p["posicion"]): (p.get("label") or f"E{p['posicion']}")
            for p in sig_parts if p.get("posicion")
        }

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

    # Nombres y escudos de equipos reales (todos los partidos juntos)
    all_partidos = partidos + partidos_sig
    eq_ids = list(
        {p["equipo_local_id"] for p in all_partidos if p.get("equipo_local_id")} |
        {p["equipo_visitante_id"] for p in all_partidos if p.get("equipo_visitante_id")}
    )
    eq_map = {}
    if eq_ids:
        for e in supabase.table("equipos").select("id, nombre, escudo_url").in_("id", eq_ids).execute().data:
            eq_map[e["id"]] = {"nombre": e["nombre"], "escudo_url": e.get("escudo_url")}

    def resolve_partido(p, gid, lmap):
        if p.get("equipo_local_id"):
            info = eq_map.get(p["equipo_local_id"], {})
            p["nombre_local"] = info.get("nombre", "?")
            p["escudo_local"] = info.get("escudo_url")
        else:
            p["nombre_local"] = lmap.get((gid, p.get("pos_local")), f"E{p.get('pos_local', '?')}")
            p["escudo_local"] = None
        if p.get("equipo_visitante_id"):
            info = eq_map.get(p["equipo_visitante_id"], {})
            p["nombre_visitante"] = info.get("nombre", "?")
            p["escudo_visitante"] = info.get("escudo_url")
        else:
            p["nombre_visitante"] = lmap.get((gid, p.get("pos_visitante")), f"E{p.get('pos_visitante', '?')}")
            p["escudo_visitante"] = None

    grupo_meta = {g["id"]: {"nombre": g["nombre"], "orden_cuadro": g.get("orden_cuadro"), "siguiente_grupo_id": g.get("siguiente_grupo_id")} for g in grupos}
    result = {}
    for p in partidos:
        gid = p["grupo_id"]
        resolve_partido(p, gid, label_map)
        result.setdefault(gid, {
            "nombre": grupo_meta[gid]["nombre"],
            "orden_cuadro": grupo_meta[gid]["orden_cuadro"],
            "siguiente_grupo_id": grupo_meta[gid]["siguiente_grupo_id"],
            "partidos": [],
            "partidos_siguiente": [],
        })
        result[gid]["partidos"].append(p)

    # Agrupar partidos de la siguiente fase por sig_grupo_id y asignarlos a sus grupos feeder
    sig_by_grupo = {}
    for p in partidos_sig:
        sgid = p["grupo_id"]
        resolve_partido(p, sgid, sig_label_map)
        p["_grupo_nombre"] = sig_grupo_meta.get(sgid, "")
        sig_by_grupo.setdefault(sgid, []).append(p)

    for gid, info in result.items():
        sgid = info.get("siguiente_grupo_id")
        if sgid and sgid in sig_by_grupo:
            info["partidos_siguiente"] = sig_by_grupo[sgid]

    return result


@_db_retry
def get_grupos_pdf_data(torneo_id):
    """Devuelve datos completos de grupos para el PDF de detalle de grupos."""
    supabase = get_supabase()
    fases = (
        supabase.table("fases").select("id, nombre, orden")
        .eq("torneo_id", torneo_id).order("orden").execute().data
    )
    if not fases:
        return []

    fases = [f for f in fases if f["orden"] == 1]
    fase_ids = [f["id"] for f in fases]

    grupos_raw = (
        supabase.table("grupos").select("id, nombre, tipo_grupo, orden_cuadro, fase_id")
        .in_("fase_id", fase_ids).execute().data
    )
    grupo_ids = [g["id"] for g in grupos_raw]
    if not grupo_ids:
        return []

    parts_all = (
        supabase.table("participantes_grupo").select("equipo_id, posicion, label, grupo_id")
        .in_("grupo_id", grupo_ids).execute().data
    )
    partidos_all = (
        supabase.table("partidos").select("*")
        .in_("grupo_id", grupo_ids).order("jornada").execute().data
    )

    all_eq_ids = list(
        {p["equipo_id"] for p in parts_all if p.get("equipo_id")}
        | {p["equipo_local_id"] for p in partidos_all if p.get("equipo_local_id")}
        | {p["equipo_visitante_id"] for p in partidos_all if p.get("equipo_visitante_id")}
    )
    eq_map = {}
    if all_eq_ids:
        for e in supabase.table("equipos").select("id, nombre, escudo_url").in_("id", all_eq_ids).execute().data:
            eq_map[e["id"]] = e

    parts_by_group = {}
    for p in parts_all:
        parts_by_group.setdefault(p["grupo_id"], []).append(p)
    partidos_by_group = {}
    for p in partidos_all:
        partidos_by_group.setdefault(p["grupo_id"], []).append(p)

    result = []
    for fase in fases:
        grupos_fase = [g for g in grupos_raw if g["fase_id"] == fase["id"]]
        if not grupos_fase:
            continue
        grupos_sorted = sorted(grupos_fase, key=lambda g: (g.get("orden_cuadro") or 9999, g["nombre"]))

        fase_grupos = []
        for g in grupos_sorted:
            gid = g["id"]
            parts = sorted(parts_by_group.get(gid, []), key=lambda p: p.get("posicion") or 0)
            partidos_raw = partidos_by_group.get(gid, [])

            label_map = {p.get("posicion"): (p.get("label") or f"E{p.get('posicion','?')}") for p in parts}

            equipos = []
            for p in parts:
                eq = eq_map.get(p["equipo_id"]) if p.get("equipo_id") else None
                equipos.append({
                    "posicion": p.get("posicion") or 0,
                    "nombre": eq["nombre"] if eq else (p.get("label") or ""),
                    "escudo_url": eq.get("escudo_url") if eq else None,
                })

            partidos = []
            for p in partidos_raw:
                if p.get("equipo_local_id"):
                    eq = eq_map.get(p["equipo_local_id"], {})
                    p["nombre_local"]  = eq.get("nombre", "?")
                    p["escudo_local"]  = eq.get("escudo_url")
                else:
                    p["nombre_local"]  = label_map.get(p.get("pos_local"), f"E{p.get('pos_local','?')}")
                    p["escudo_local"]  = None
                if p.get("equipo_visitante_id"):
                    eq = eq_map.get(p["equipo_visitante_id"], {})
                    p["nombre_visitante"]  = eq.get("nombre", "?")
                    p["escudo_visitante"]  = eq.get("escudo_url")
                else:
                    p["nombre_visitante"]  = label_map.get(p.get("pos_visitante"), f"E{p.get('pos_visitante','?')}")
                    p["escudo_visitante"]  = None
                partidos.append(p)

            fase_grupos.append({
                "nombre":     g["nombre"],
                "tipo_grupo": g.get("tipo_grupo") or 0,
                "equipos":    equipos,
                "partidos":   partidos,
            })

        if fase_grupos:
            result.append({
                "fase_nombre": fase["nombre"],
                "fase_orden":  fase["orden"],
                "grupos":      fase_grupos,
            })

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


def eliminar_partido(partido_id):
    supabase = get_supabase()
    supabase.table("partidos").delete().eq("id", partido_id).execute()
    st.cache_data.clear()


def actualizar_horario_partido(partido_id, fecha, hora, campo: str):
    """Actualiza fecha, hora y campo de un partido concreto."""
    supabase = get_supabase()
    data: dict = {}
    if fecha is not None:
        data["fecha"] = str(fecha)
    if hora is not None:
        data["hora"] = str(hora)[:5]
    if campo is not None:
        data["campo"] = campo.strip() or None
    if data:
        supabase.table("partidos").update(data).eq("id", partido_id).execute()
    st.cache_data.clear()


# -------------------------------------------------------
# AGENDA (multi-torneo)
# -------------------------------------------------------

@_db_retry
def get_campos_distintos():
    """Devuelve lista de campos únicos con partido asignado."""
    supabase = get_supabase()
    rows = supabase.table("partidos").select("campo").not_.is_("campo", "null").execute().data
    return sorted({r["campo"] for r in rows if r.get("campo")})


@_db_retry
def get_partidos_agenda(fecha_desde=None, fecha_hasta=None, campos=None, torneo_ids=None):
    """
    Devuelve lista de partidos con fecha asignada, enriquecidos con nombres de
    equipos, grupo y torneo. Filtros opcionales: rango de fechas, lista de campos,
    lista de torneo_ids.
    """
    supabase = get_supabase()

    # Construir mapa grupo_id → {torneo_nombre, grupo_nombre}
    fases_q = supabase.table("fases").select("id, torneo_id, duracion_partido, torneos(id, nombre)").execute().data
    if torneo_ids:
        fases_q = [f for f in fases_q if f["torneo_id"] in torneo_ids]
    if not fases_q:
        return []

    fase_ids = [f["id"] for f in fases_q]
    torneo_nombre_map  = {f["id"]: (f.get("torneos") or {}).get("nombre", "?") for f in fases_q}
    fase_torneo_id_map = {f["id"]: f["torneo_id"] for f in fases_q}
    fase_duracion_map  = {f["id"]: f.get("duracion_partido") for f in fases_q}

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
        g["id"]: {
            "grupo":     g["nombre"],
            "torneo":    torneo_nombre_map.get(g["fase_id"], "?"),
            "torneo_id": fase_torneo_id_map.get(g["fase_id"], ""),
            "duracion":  fase_duracion_map.get(g["fase_id"]),
        }
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
        for e in supabase.table("equipos").select("id, nombre, escudo_url").in_("id", eq_ids).execute().data:
            eq_map[e["id"]] = {"nombre": e["nombre"], "escudo_url": e.get("escudo_url")}

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
            info_l = eq_map.get(p["equipo_local_id"], {})
            p["nombre_local"]  = info_l.get("nombre", "?")
            p["escudo_local"]  = info_l.get("escudo_url")
        else:
            p["nombre_local"]  = label_map.get((gid, p.get("pos_local")), f"E{p.get('pos_local', '?')}")
            p["escudo_local"]  = None

        if p.get("equipo_visitante_id"):
            info_v = eq_map.get(p["equipo_visitante_id"], {})
            p["nombre_visitante"]  = info_v.get("nombre", "?")
            p["escudo_visitante"]  = info_v.get("escudo_url")
        else:
            p["nombre_visitante"]  = label_map.get((gid, p.get("pos_visitante")), f"E{p.get('pos_visitante', '?')}")
            p["escudo_visitante"]  = None
        p["nombre_torneo"]    = meta.get("torneo", "?")
        p["nombre_grupo"]     = meta.get("grupo", "")
        p["torneo_id"]        = meta.get("torneo_id", "")
        p["duracion_partido"] = meta.get("duracion")

    return partidos