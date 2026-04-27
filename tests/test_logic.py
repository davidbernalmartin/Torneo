"""
Tests unitarios para src/logic.py — lógica del sorteo automático.
"""
from unittest.mock import MagicMock, patch

from src.logic import realizar_sorteo


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_sb_sorteo(equipos_data=None):
    """
    Mock de Supabase para realizar_sorteo.
    - tabla 'equipos'             → devuelve equipos_data
    - tabla 'participantes_grupo' → soporta delete/in_/insert/execute
    """
    equipos_data = equipos_data or []

    eq_m = MagicMock(name="equipos")
    eq_m.select.return_value = eq_m
    eq_m.eq.return_value = eq_m
    eq_m.execute.return_value = MagicMock(data=equipos_data)

    part_m = MagicMock(name="participantes_grupo")
    part_m.delete.return_value = part_m
    part_m.in_.return_value = part_m
    part_m.insert.return_value = part_m
    part_m.execute.return_value = MagicMock(data=[])

    sb = MagicMock()
    sb.table.side_effect = lambda name: eq_m if name == "equipos" else part_m
    return sb, eq_m, part_m


# ── Filtrado de equipos ───────────────────────────────────────────────────────

def test_sorteo_filtra_equipos_por_torneo_id():
    """Solo deben participar equipos del torneo indicado — previene mezcla entre torneos."""
    sb, eq_m, _ = _make_sb_sorteo([{"id": "e1"}])

    with patch("src.logic.get_supabase", return_value=sb):
        realizar_sorteo("f1", [{"id": "g1", "tipo_grupo": 1}], "torneo-xyz")

    eq_m.eq.assert_any_call("torneo_id", "torneo-xyz")


def test_sorteo_excluye_equipos_eliminados():
    """Los equipos marcados como eliminados no deben entrar en el sorteo."""
    sb, eq_m, _ = _make_sb_sorteo([{"id": "e1"}])

    with patch("src.logic.get_supabase", return_value=sb):
        realizar_sorteo("f1", [{"id": "g1", "tipo_grupo": 1}], "t-1")

    eq_m.eq.assert_any_call("eliminado", False)


# ── Distribución entre grupos ─────────────────────────────────────────────────

def test_sorteo_distribuye_todos_los_equipos_entre_grupos():
    """Con suficientes equipos, todas las plazas de todos los grupos deben llenarse."""
    equipos = [{"id": f"e{i}"} for i in range(6)]
    grupos = [{"id": "g1", "tipo_grupo": 3}, {"id": "g2", "tipo_grupo": 3}]
    sb, _, part_m = _make_sb_sorteo(equipos_data=equipos)

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):   # desactivar aleatoriedad para resultados deterministas
            realizar_sorteo("f1", grupos, "t-1")

    payload = part_m.insert.call_args[0][0]
    assert len(payload) == 6
    assert sum(1 for p in payload if p["grupo_id"] == "g1") == 3
    assert sum(1 for p in payload if p["grupo_id"] == "g2") == 3


def test_sorteo_asigna_grupo_id_correcto_a_cada_participante():
    """Cada participante insertado debe tener el grupo_id del grupo al que pertenece."""
    equipos = [{"id": "eA"}, {"id": "eB"}]
    grupos = [{"id": "g-único", "tipo_grupo": 2}]
    sb, _, part_m = _make_sb_sorteo(equipos_data=equipos)

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):
            realizar_sorteo("f1", grupos, "t-1")

    payload = part_m.insert.call_args[0][0]
    assert all(p["grupo_id"] == "g-único" for p in payload)


# ── Casos límite ──────────────────────────────────────────────────────────────

def test_sorteo_no_inserta_nada_si_no_hay_equipos():
    """Si el torneo no tiene equipos, no se debe llamar a insert."""
    sb, _, part_m = _make_sb_sorteo(equipos_data=[])

    with patch("src.logic.get_supabase", return_value=sb):
        realizar_sorteo("f1", [{"id": "g1", "tipo_grupo": 3}], "t-vacio")

    part_m.insert.assert_not_called()


def test_sorteo_llena_solo_las_plazas_disponibles_si_faltan_equipos():
    """Si hay menos equipos que plazas, se llenan las que se pueden sin error."""
    equipos = [{"id": "e1"}, {"id": "e2"}]
    grupos = [{"id": "g1", "tipo_grupo": 5}]   # 5 plazas, solo 2 equipos
    sb, _, part_m = _make_sb_sorteo(equipos_data=equipos)

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):
            realizar_sorteo("f1", grupos, "t-1")

    payload = part_m.insert.call_args[0][0]
    assert len(payload) == 2


def test_sorteo_no_falla_si_hay_mas_equipos_que_plazas():
    """Si sobran equipos, se usan solo los necesarios sin error."""
    equipos = [{"id": f"e{i}"} for i in range(10)]
    grupos = [{"id": "g1", "tipo_grupo": 3}]   # solo 3 plazas
    sb, _, part_m = _make_sb_sorteo(equipos_data=equipos)

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):
            realizar_sorteo("f1", grupos, "t-1")

    payload = part_m.insert.call_args[0][0]
    assert len(payload) == 3


# ── Orden de operaciones ──────────────────────────────────────────────────────

def test_sorteo_borra_participantes_existentes_antes_de_insertar():
    """El DELETE debe ejecutarse antes que el INSERT para evitar duplicados."""
    sb, _, part_m = _make_sb_sorteo(equipos_data=[{"id": "e1"}, {"id": "e2"}])

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):
            realizar_sorteo("f1", [{"id": "g1", "tipo_grupo": 2}], "t-1")

    metodos = [c[0] for c in part_m.method_calls]
    assert metodos.index("delete") < metodos.index("insert"), (
        "El DELETE de participantes existentes debe hacerse antes que el INSERT"
    )


def test_sorteo_inicializa_puntos_y_goles_a_cero():
    """Los participantes nuevos deben empezar con puntos=0 y goles=0."""
    sb, _, part_m = _make_sb_sorteo(equipos_data=[{"id": "e1"}])

    with patch("src.logic.get_supabase", return_value=sb):
        with patch("random.shuffle"):
            realizar_sorteo("f1", [{"id": "g1", "tipo_grupo": 1}], "t-1")

    payload = part_m.insert.call_args[0][0]
    assert payload[0]["puntos"] == 0
    assert payload[0]["goles"] == 0
