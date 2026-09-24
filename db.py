"""
Módulo de gestión de base de datos MySQL (XAMPP) para el Sistema de Facturación.
Maneja conexiones seguras, transacciones (commit/rollback) y operaciones CRUD para productos.
"""

import time
import mysql.connector
from mysql.connector import Error
from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any


# Configuración por defecto para XAMPP MySQL con prevención de timeout
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "database": "facturacion",
    "connect_timeout": 10,
    "autocommit": True,
    "use_pure": True
}

DB_PROFILES = {
    "local": {"table": "productos", "label": "Ventas locales"},
    "costa": {"table": "productos_costa", "label": "Ventas de la costa"},
}
_active_profile = "local"


def seleccionar_perfil(perfil: str) -> None:
    """Selecciona la tabla de productos que usaran las operaciones siguientes."""
    global _active_profile
    if perfil not in DB_PROFILES:
        raise ValueError(f"Perfil de base de datos no valido: {perfil}")
    _active_profile = perfil


def obtener_perfil_actual() -> str:
    return _active_profile


def obtener_nombre_perfil() -> str:
    return DB_PROFILES[_active_profile]["label"]


def _configuracion_activa() -> dict:
    return DB_CONFIG.copy()


def _tabla_activa() -> str:
    """Retorna un nombre de tabla controlado por la aplicacion."""
    return DB_PROFILES[_active_profile]["table"]


def obtener_conexion(intentos: int = 3, delay: int = 1) -> Optional[mysql.connector.MySQLConnection]:
    """
    Establece y retorna una conexión activa a MySQL en XAMPP.
    Si la conexión inicial falla o expira por timeout, reintenta y aplica auto-reconexión.
    """
    for intento in range(1, intentos + 1):
        try:
            conexion = mysql.connector.connect(**_configuracion_activa())
            if conexion.is_connected():
                # Valida la salud de la conexión y reconecta automáticamente si caducó
                conexion.ping(reconnect=True, attempts=intentos, delay=delay)
                return conexion
        except (Error, Exception) as e:
            print(f"[DB Reconnect] Intento {intento}/{intentos} falló: {e}")
            if intento < intentos:
                time.sleep(delay)
    return None


def verificar_conexion() -> Tuple[bool, str]:
    """
    Verifica si el servidor MySQL está activo y la base de datos existe
    utilizando la conexión protegida con auto-reconexión.
    Retorna (True, "Conectado") o (False, mensaje_error).
    """
    conexion = obtener_conexion(intentos=3, delay=1)
    if conexion:
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()
            cursor.close()
            conexion.close()
            return True, f"Conectado a '{db_name[0]}' en MySQL (XAMPP)"
        except Exception as e:
            try:
                conexion.close()
            except Exception:
                pass
            return False, f"No se pudo consultar la base de datos: {e}. Asegúrate de que Apache/MySQL estén iniciados en XAMPP."
    return False, "No se pudo conectar a MySQL tras varios intentos. Asegúrate de que Apache/MySQL estén iniciados en XAMPP."


def obtener_todos_los_productos() -> List[Dict[str, Any]]:
    """
    Obtiene la lista completa de productos desde la base de datos.
    Retorna una lista de diccionarios con keys: 'id', 'concepto', 'precio'.
    """
    productos = []
    conexion = obtener_conexion()
    if not conexion:
        return productos

    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(f"SELECT id, concepto, precio FROM `{_tabla_activa()}` ORDER BY concepto ASC")
        resultados = cursor.fetchall()
        for r in resultados:
            productos.append({
                "id": r["id"],
                "concepto": str(r["concepto"]).strip(),
                "precio": Decimal(str(r["precio"]))
            })
    except Error as e:
        print(f"[DB Error] Error al obtener productos: {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return productos


def obtener_nombres_conceptos() -> List[str]:
    """
    Obtiene únicamente los nombres de los conceptos para autocompletado.
    """
    conceptos = []
    conexion = obtener_conexion()
    if not conexion:
        return conceptos

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(f"SELECT concepto FROM `{_tabla_activa()}` ORDER BY concepto ASC")
        resultados = cursor.fetchall()
        conceptos = [str(r[0]).strip() for r in resultados]
    except Error as e:
        print(f"[DB Error] Error al obtener conceptos: {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return conceptos


def obtener_precio_por_concepto(concepto: str) -> Optional[Decimal]:
    """
    Obtiene el precio de un producto según su concepto exacto.
    """
    conexion = obtener_conexion()
    if not conexion:
        return None

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(f"SELECT precio FROM `{_tabla_activa()}` WHERE concepto = %s LIMIT 1", (concepto,))
        resultado = cursor.fetchone()
        if resultado:
            return Decimal(str(resultado[0]))
    except Error as e:
        print(f"[DB Error] Error al obtener precio de '{concepto}': {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return None


def agregar_producto(concepto: str, precio: Decimal) -> Tuple[bool, str, Optional[int]]:
    """
    Inserta un nuevo producto en la base de datos MySQL con transacción.
    Retorna (éxito: bool, mensaje: str, nuevo_id: int o None).
    """
    concepto = concepto.strip()
    if not concepto:
        return False, "El nombre del producto no puede estar vacío.", None
    if precio <= 0:
        return False, "El precio debe ser un valor mayor a cero.", None

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP.", None

    cursor = None
    try:
        cursor = conexion.cursor()
        query = f"INSERT INTO `{_tabla_activa()}` (concepto, precio) VALUES (%s, %s)"
        cursor.execute(query, (concepto, float(precio)))
        conexion.commit()
        nuevo_id = cursor.lastrowid
        return True, f"Producto '{concepto}' agregado exitosamente.", nuevo_id
    except Error as e:
        conexion.rollback()
        return False, f"Error al insertar en MySQL: {e}", None
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def actualizar_producto(id_producto: int, nuevo_concepto: str, nuevo_precio: Decimal) -> Tuple[bool, str]:
    """
    Actualiza el nombre y precio de un producto existente identificado por su ID.
    Retorna (éxito: bool, mensaje: str).
    """
    nuevo_concepto = nuevo_concepto.strip()
    if not nuevo_concepto:
        return False, "El nombre del producto no puede estar vacío."
    if nuevo_precio <= 0:
        return False, "El precio debe ser un número positivo mayor a cero."

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP."

    cursor = None
    try:
        cursor = conexion.cursor()
        query = f"UPDATE `{_tabla_activa()}` SET concepto = %s, precio = %s WHERE id = %s"
        cursor.execute(query, (nuevo_concepto, float(nuevo_precio), id_producto))
        conexion.commit()

        if cursor.rowcount > 0:
            return True, f"Producto #{id_producto} actualizado correctamente."
        else:
            return False, f"No se encontró el producto #{id_producto} para actualizar."
    except Error as e:
        conexion.rollback()
        return False, f"Error al actualizar en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def eliminar_producto(id_producto: int) -> Tuple[bool, str]:
    """
    Elimina un producto de la base de datos por su ID.
    Retorna (éxito: bool, mensaje: str).
    """
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP."

    cursor = None
    try:
        cursor = conexion.cursor()
        query = f"DELETE FROM `{_tabla_activa()}` WHERE id = %s"
        cursor.execute(query, (id_producto,))
        conexion.commit()

        if cursor.rowcount > 0:
            return True, f"Producto #{id_producto} eliminado correctamente de MySQL."
        else:
            return False, f"No se encontró el producto #{id_producto} en la base de datos."
    except Error as e:
        conexion.rollback()
        return False, f"Error al eliminar en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()
