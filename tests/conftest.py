"""
Parchea streamlit ANTES de que se importen src.* para que los decoradores
@st.cache_data y @st.cache_resource funcionen como passthrough en los tests.
"""
import sys
from unittest.mock import MagicMock


class _FakeCacheData:
    """st.cache_data(ttl=...) actúa como decorador transparente; .clear() no hace nada."""
    def __call__(self, **kwargs):
        return lambda f: f

    def clear(self):
        pass


_st = MagicMock()
_st.cache_data = _FakeCacheData()
_st.cache_resource = lambda f: f   # @st.cache_resource sin paréntesis

sys.modules["streamlit"] = _st
