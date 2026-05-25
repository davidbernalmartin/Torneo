# Módulos de generación de PDFs del gestor de torneos RFFM.
from .agenda import generar_pdf_agenda
from .agenda_grid import generar_pdf_agenda_grid
from .grupos import generar_pdf_grupos
from .partidos import generar_pdf_partidos
from .tarjetas import generar_pdf_tarjetas

__all__ = [
    "generar_pdf_agenda",
    "generar_pdf_agenda_grid",
    "generar_pdf_grupos",
    "generar_pdf_partidos",
    "generar_pdf_tarjetas",
]
