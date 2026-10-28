"""
Módulo centralizado de acceso a Sybase.
"""
import logging
import pyodbc
from contextlib import contextmanager
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_connection_string():
    dsn = getattr(settings, 'SYBASE_DSN', '')
    user = getattr(settings, 'SYBASE_USER', '')
    pwd = getattr(settings, 'SYBASE_PWD', '')
    if not all([dsn, user, pwd]):
        raise RuntimeError(
            "Faltan credenciales de Sybase. Verifica el archivo .env "
            "(SYBASE_DSN, SYBASE_USER, SYBASE_PWD)."
        )
    return f"DSN={dsn};UID={user};PWD={pwd};"


def obtener_conexion_maestra():
    return pyodbc.connect(_get_connection_string())


@contextmanager
def cursor_maestra(commit=False):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        yield cursor
        if commit:
            conexion.commit()
    except pyodbc.Error:
        logger.exception("Error de Sybase en cursor_maestra")
        if conexion:
            try:
                conexion.rollback()
            except Exception:
                pass
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conexion:
            try:
                conexion.close()
            except Exception:
                pass


def safe_str_id(valor):
    """
    Convierte un valor numérico a string limpio.
    Sybase usa el PUNTO como separador de miles, no como decimal:
    - "1001"   → "1001"
    - "1.001"  → "1001"  (separador de miles, 3 dígitos después del punto)
    - "28.080" → "28080" (separador de miles)
    - "1.0"    → "1"     (decimal real, 1 dígito)
    - "1.50"   → "1"     (decimal real, 2 dígitos)
    """
    if valor is None:
        return ''
    s = str(valor).strip()
    if '.' in s:
        entero, decimal = s.split('.', 1)
        # Si decimales son exactamente 3 dígitos = separador de miles Sybase
        if len(decimal) == 3:
            return entero + decimal
        # Menos de 3 dígitos = decimal real (.0, .5, .25)
        return entero
    return s


def safe_str(valor, default=''):
    if valor is None:
        return default
    return str(valor).strip()