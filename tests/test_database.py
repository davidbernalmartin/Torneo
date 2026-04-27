"""
Tests unitarios para src/database.py.
Supabase se mockea con un fluent-mock que soporta el encadenamiento
.table().select().eq().execute().data propio de supabase-py.
"""
from unittest.mock import MagicMock, patch

from src.database import (
    subir_equipos_batch,
    crear_fase,
    crear_grupos,
    actualizar_grupo,
    eliminar_grupo,
    contar_grupos_fase,
)


# ── Helper: factory de mocks ─────────────────────────────────────────────────

def _make_table_mock(data=None, count=0):
    """Mock de una tabla Supabase con soporte completo para encadenamiento fluent."""
    m = MagicMock()
    for method in ("select", "eq", "in_", "order", "limit", "insert", "update", "delete"):
        getattr(m, method).return_value = m
    m.execute.return_value = MagicMock(data=data or [], count=count)
    return m


def _make_sb(table_data=None):
    """
    Devuelve (mock_supabase, dict_tabla→mock).
    Cada nombre de tabla obtiene su propio mock, reutilizado en llamadas sucesivas.
    """
    table_data = table_data or {}
    table_mocks: dict = {}

    def _get(name):
        if name not in table_mocks:
            data = table_data.get(name, [])
            table_mocks[name] = _make_table_mock(data=data, count=len(data))
        return table_mocks[name]

    sb = MagicMock()
    sb.table.side_effect = _get
    return sb, table_mocks


# ── subir_equipos_batch ───────────────────────────────────────────────────────

def test_subir_batch_agrega_torneo_id_a_todos_los_equipos():
    """Todos los equipos del lote deben incluir torneo_id al insertarse en BD."""
    sb, t = _make_sb()
    equipos = [{"nombre": "Equipo A", "escudo_url": ""}, {"nombre": "Equipo B", "escudo_url": ""}]

    with patch("src.database.get_supabase", return_value=sb):
        subir_equipos_batch(equipos, "torneo-99")

    payload = t["equipos"].insert.call_args[0][0]
    assert len(payload) == 2
    assert all(e["torneo_id"] == "torneo-99" for e in payload)


def test_subir_batch_no_modifica_campos_originales():
    """Los campos nombre y escudo_url deben conservarse intactos."""
    sb, t = _make_sb()
    equipos = [{"nombre": "Real Madrid", "escudo_url": "https://rm.com/logo.png"}]

    with patch("src.database.get_supabase", return_value=sb):
        subir_equipos_batch(equipos, "t-1")

    payload = t["equipos"].insert.call_args[0][0]
    assert payload[0]["nombre"] == "Real Madrid"
    assert payload[0]["escudo_url"] == "https://rm.com/logo.png"


def test_subir_batch_retorna_string_si_supabase_lanza_excepcion():
    """Si Supabase falla, la función debe devolver un string con el error (no relanzar)."""
    sb, _ = _make_sb()
    sb.table("equipos").execute.side_effect = Exception("DB timeout")

    with patch("src.database.get_supabase", return_value=sb):
        result = subir_equipos_batch([{"nombre": "X", "escudo_url": ""}], "t-1")

    assert isinstance(result, str)
    assert "Error" in result


# ── crear_fase ────────────────────────────────────────────────────────────────

def test_crear_fase_inserta_nombre_orden_y_torneo_id():
    """La fila de fase creada debe incluir los tres campos obligatorios."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        crear_fase("Fase de grupos", 1, "torneo-abc")

    payload = t["fases"].insert.call_args[0][0]
    assert payload["nombre"] == "Fase de grupos"
    assert payload["orden"] == 1
    assert payload["torneo_id"] == "torneo-abc"


def test_crear_fase_permite_orden_mayor_que_uno():
    """Fases de eliminación (orden > 1) deben crearse con el orden correcto."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        crear_fase("Semifinales", 2, "t-x")

    payload = t["fases"].insert.call_args[0][0]
    assert payload["orden"] == 2


# ── crear_grupos ──────────────────────────────────────────────────────────────

def test_crear_grupos_inserta_todos_los_grupos_en_una_sola_llamada():
    """El insert debe recibir la lista completa, no llamadas individuales."""
    sb, t = _make_sb()
    grupos = [
        {"fase_id": "f1", "nombre": "Grupo 1", "tipo_grupo": 4},
        {"fase_id": "f1", "nombre": "Grupo 2", "tipo_grupo": 4},
        {"fase_id": "f1", "nombre": "Grupo 3", "tipo_grupo": 3},
    ]

    with patch("src.database.get_supabase", return_value=sb):
        crear_grupos(grupos)

    t["grupos"].insert.assert_called_once_with(grupos)


# ── actualizar_grupo ──────────────────────────────────────────────────────────

def test_actualizar_grupo_pasa_los_tres_campos():
    """El update debe incluir nombre, tipo_grupo y orden_cuadro."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        actualizar_grupo("g-1", "Grupo A", 4, 2)

    payload = t["grupos"].update.call_args[0][0]
    assert payload == {"nombre": "Grupo A", "tipo_grupo": 4, "orden_cuadro": 2}


def test_actualizar_grupo_filtra_por_id_correcto():
    """El update debe aplicarse únicamente al grupo con el id indicado."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        actualizar_grupo("g-999", "X", 3, None)

    t["grupos"].eq.assert_called_with("id", "g-999")


def test_actualizar_grupo_acepta_orden_cuadro_none():
    """orden_cuadro puede ser None (grupo sin posición asignada en el bracket)."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        actualizar_grupo("g-2", "Grupo B", 4, None)

    payload = t["grupos"].update.call_args[0][0]
    assert payload["orden_cuadro"] is None


# ── eliminar_grupo ────────────────────────────────────────────────────────────

def test_eliminar_grupo_anula_fk_autorreferencial_antes_del_delete():
    """
    siguiente_grupo_id debe ponerse a NULL antes del DELETE.
    Esto evita el error FK 23503 que se producía al borrar un grupo
    referenciado por otro como 'siguiente_grupo_id'.
    """
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        eliminar_grupo("g-del")

    # La llamada update({"siguiente_grupo_id": None}) debe existir
    t["grupos"].update.assert_any_call({"siguiente_grupo_id": None})

    # Y debe producirse ANTES que el DELETE en la misma tabla
    metodos = [c[0] for c in t["grupos"].method_calls]
    assert metodos.index("update") < metodos.index("delete"), (
        "La FK auto-referencial debe anularse antes de ejecutar el DELETE en grupos"
    )


def test_eliminar_grupo_borra_participantes_del_grupo():
    """El DELETE en participantes_grupo debe filtrar por el grupo_id correcto."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        eliminar_grupo("g-x")

    t["participantes_grupo"].delete.assert_called_once()
    t["participantes_grupo"].eq.assert_called_with("grupo_id", "g-x")


def test_eliminar_grupo_borra_el_grupo_de_la_tabla_grupos():
    """El DELETE final debe ejecutarse sobre la tabla grupos."""
    sb, t = _make_sb()

    with patch("src.database.get_supabase", return_value=sb):
        eliminar_grupo("g-z")

    t["grupos"].delete.assert_called()
    t["grupos"].eq.assert_any_call("id", "g-z")


# ── contar_grupos_fase ────────────────────────────────────────────────────────

def test_contar_grupos_fase_devuelve_el_count_de_supabase():
    sb, _ = _make_sb()
    sb.table("grupos").execute.return_value = MagicMock(count=7)

    with patch("src.database.get_supabase", return_value=sb):
        result = contar_grupos_fase("fase-1")

    assert result == 7


def test_contar_grupos_fase_devuelve_cero_si_count_es_none():
    """Supabase puede devolver count=None si no se usa count='exact'."""
    sb, _ = _make_sb()
    sb.table("grupos").execute.return_value = MagicMock(count=None)

    with patch("src.database.get_supabase", return_value=sb):
        result = contar_grupos_fase("fase-1")

    assert result == 0
