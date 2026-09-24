"""
Módulo de gestión de base de datos MySQL (XAMPP) para el Sistema de Facturación.
Maneja conexiones seguras, transacciones (commit/rollback) y operaciones CRUD para productos.
El stock (cantidad) se almacena en una tabla dedicada `stock`, compartida entre
todos los perfiles de productos (local y costa).
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

# Tabla centralizada de stock compartida entre todos los perfiles
STOCK_TABLE = "stock"


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


def _tabla_activa(perfil: Optional[str] = None) -> str:
    """Retorna un nombre de tabla controlado por la aplicacion."""
    perfil = perfil or _active_profile
    if perfil not in DB_PROFILES:
        raise ValueError(f"Perfil de base de datos no valido: {perfil}")
    return DB_PROFILES[perfil]["table"]


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


# ------------------------------------------------------------------
# CRUD de Stock centralizado
# ------------------------------------------------------------------

def obtener_todos_los_productos() -> List[Dict[str, Any]]:
    """
    Obtiene la lista completa de productos con su stock desde la tabla `stock`.
    El stock es compartido entre todos los perfiles mediante LEFT JOIN con `stock`.
    Retorna una lista de diccionarios con keys: 'id', 'concepto', 'precio', 'cantidad'.
    """
    productos = []
    conexion = obtener_conexion()
    if not conexion:
        return productos

    cursor = None
    tabla = _tabla_activa()
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            f"SELECT t.id, t.concepto, t.precio, COALESCE(s.cantidad, 0) AS cantidad "
            f"FROM `{tabla}` t "
            f"LEFT JOIN `{STOCK_TABLE}` s ON LOWER(TRIM(t.concepto)) = LOWER(TRIM(s.concepto)) "
            f"ORDER BY t.concepto ASC"
        )
        resultados = cursor.fetchall()
        for r in resultados:
            productos.append({
                "id": r["id"],
                "concepto": str(r["concepto"]).strip(),
                "precio": Decimal(str(r["precio"])),
                "cantidad": int(r["cantidad"]) if r.get("cantidad") is not None else 0
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


def obtener_stock_por_concepto(concepto: str) -> Optional[int]:
    """
    Obtiene el stock disponible desde la tabla centralizada `stock`.
    Es independiente del perfil activo, ya que el stock es compartido.
    """
    conexion = obtener_conexion()
    if not conexion:
        return None

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(
            f"SELECT cantidad FROM `{STOCK_TABLE}` WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s)) LIMIT 1",
            (concepto,)
        )
        resultado = cursor.fetchone()
        if resultado and resultado[0] is not None:
            return int(resultado[0])
    except Error as e:
        print(f"[DB Error] Error al obtener stock de '{concepto}': {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return None


def actualizar_stock(concepto: str, cantidad: int) -> Tuple[bool, str]:
    """
    Actualiza (o inserta) la entrada de stock para un concepto en la tabla `stock`.
    Usa INSERT ... ON DUPLICATE KEY UPDATE para un upsert seguro.
    Retorna (éxito: bool, mensaje: str).
    """
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP."

    cursor = None
    try:
        cursor = conexion.cursor()
        query = (
            f"INSERT INTO `{STOCK_TABLE}` (concepto, cantidad) VALUES (%s, %s) "
            f"ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad)"
        )
        cursor.execute(query, (str(concepto).strip(), int(cantidad)))
        conexion.commit()
        return True, f"Stock de '{concepto}' actualizado a {cantidad} unidades."
    except Error as e:
        conexion.rollback()
        return False, f"Error al actualizar stock en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def descontar_stock_productos(items_vendidos: List[Any]) -> Tuple[bool, str]:
    """
    Descuenta la cantidad vendida en la tabla centralizada `stock`.
    Al ser una tabla única, el stock queda sincronizado automáticamente
    para todos los perfiles (local y costa).
    Acepta objetos con atributos 'concepto' y 'cantidad' o diccionarios.
    """
    if not items_vendidos:
        return True, "No hay productos para descontar stock."

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos para descontar stock."

    cursor = None
    try:
        cursor = conexion.cursor()
        for item in items_vendidos:
            if isinstance(item, dict):
                concepto = item.get("concepto")
                cantidad = item.get("cantidad", 0)
            else:
                concepto = getattr(item, "concepto", None)
                cantidad = getattr(item, "cantidad", 0)

            if concepto and cantidad > 0:
                # Descuenta de la tabla stock, nunca baja de 0
                query = (
                    f"UPDATE `{STOCK_TABLE}` "
                    f"SET cantidad = GREATEST(0, cantidad - %s) "
                    f"WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))"
                )
                cursor.execute(query, (int(cantidad), str(concepto).strip()))

        conexion.commit()
        return True, "Stock descontado correctamente en la Base de Datos."
    except Error as e:
        conexion.rollback()
        return False, f"Error al descontar stock en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()


# ------------------------------------------------------------------
# CRUD de Productos
# ------------------------------------------------------------------

def agregar_producto(concepto: str, precio: Decimal, cantidad: int = 0, perfil: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
    """
    Inserta un nuevo producto en las tablas local y costa, y crea/actualiza su
    entrada en la tabla centralizada `stock`. El perfil indicado se inserta
    primero y determina el ID retornado; si no se indica, usa el activo.
    Retorna (éxito: bool, mensaje: str, nuevo_id: int o None).
    """
    concepto = concepto.strip()
    if not concepto:
        return False, "El nombre del producto no puede estar vacío.", None
    if precio <= 0:
        return False, "El precio debe ser un valor mayor a cero.", None
    if cantidad < 0:
        return False, "La cantidad no puede ser un número negativo.", None

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP.", None

    cursor = None
    try:
        cursor = conexion.cursor()

        # 1. Insertar el producto en ambos catálogos dentro de la misma transacción
        tabla_principal = _tabla_activa(perfil)
        tablas_producto = [tabla_principal] + [perfil_data["table"] for perfil_data in DB_PROFILES.values()]
        nuevo_id = None
        for tabla in dict.fromkeys(tablas_producto):
            query_prod = f"INSERT INTO `{tabla}` (concepto, precio) VALUES (%s, %s)"
            cursor.execute(query_prod, (concepto, float(precio)))
            if tabla == tabla_principal:
                nuevo_id = cursor.lastrowid

        # 2. Crear o actualizar el registro en la tabla de stock centralizada
        query_stock = (
            f"INSERT INTO `{STOCK_TABLE}` (concepto, cantidad) VALUES (%s, %s) "
            f"ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad)"
        )
        cursor.execute(query_stock, (concepto, int(cantidad)))

        conexion.commit()
        return True, f"Producto '{concepto}' agregado exitosamente.", nuevo_id
    except Error as e:
        conexion.rollback()
        return False, f"Error al insertar en MySQL: {e}", None
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def actualizar_producto(id_producto: int, nuevo_concepto: str, nuevo_precio: Decimal, nueva_cantidad: int = 0) -> Tuple[bool, str]:
    """
    Actualiza el nombre y precio del producto en ambos catálogos, y sincroniza
    el stock en la tabla centralizada `stock`.
    Retorna (éxito: bool, mensaje: str).
    """
    nuevo_concepto = nuevo_concepto.strip()
    if not nuevo_concepto:
        return False, "El nombre del producto no puede estar vacío."
    if nuevo_precio <= 0:
        return False, "El precio debe ser un número positivo mayor a cero."
    if nueva_cantidad < 0:
        return False, "La cantidad no puede ser un número negativo."

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP."

    cursor = None
    try:
        cursor = conexion.cursor()

        # 1. Obtener concepto anterior para saber si existe el producto y si cambió el nombre
        cursor.execute(f"SELECT concepto FROM `{_tabla_activa()}` WHERE id = %s LIMIT 1", (id_producto,))
        fila = cursor.fetchone()

        # Validar existencia con el SELECT, NO con rowcount (rowcount=0 si valores no cambian)
        if not fila:
            return False, f"No se encontró el producto #{id_producto} para actualizar."

        concepto_anterior = str(fila[0]).strip()

        # 2. Actualizar ambos catálogos dentro de la misma transacción
        tabla_activa = _tabla_activa()
        for tabla_data in DB_PROFILES.values():
            tabla = tabla_data["table"]
            if tabla == tabla_activa:
                cursor.execute(
                    f"UPDATE `{tabla}` SET concepto = %s, precio = %s WHERE id = %s",
                    (nuevo_concepto, float(nuevo_precio), id_producto)
                )
            else:
                cursor.execute(
                    f"UPDATE `{tabla}` SET concepto = %s, precio = %s "
                    "WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                    (nuevo_concepto, float(nuevo_precio), concepto_anterior)
                )

        # 3. Si el nombre cambió, renombrar en la tabla stock también
        if concepto_anterior.lower() != nuevo_concepto.lower():
            cursor.execute(
                f"UPDATE `{STOCK_TABLE}` SET concepto = %s WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                (nuevo_concepto, concepto_anterior)
            )

        # 4. Upsert en stock con la cantidad indicada
        query_stock = (
            f"INSERT INTO `{STOCK_TABLE}` (concepto, cantidad) VALUES (%s, %s) "
            f"ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad)"
        )
        cursor.execute(query_stock, (nuevo_concepto, int(nueva_cantidad)))

        conexion.commit()
        return True, f"Producto #{id_producto} actualizado correctamente."
    except Error as e:
        conexion.rollback()
        return False, f"Error al actualizar en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def eliminar_producto(id_producto: int) -> Tuple[bool, str]:
    """
    Elimina un producto de ambos catálogos usando el ID del perfil activo
    para localizar el concepto correspondiente.
    Si el concepto ya no existe en ninguna tabla de productos, elimina
    también su entrada en la tabla de stock.
    Retorna (éxito: bool, mensaje: str).
    """
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP."

    cursor = None
    try:
        cursor = conexion.cursor()

        # 1. Obtener el concepto del producto antes de eliminarlo
        cursor.execute(f"SELECT concepto FROM `{_tabla_activa()}` WHERE id = %s LIMIT 1", (id_producto,))
        fila = cursor.fetchone()
        concepto = str(fila[0]).strip() if fila else None

        # 2. Eliminar de ambos catálogos dentro de la misma transacción
        tabla_activa = _tabla_activa()
        cursor.execute(f"DELETE FROM `{tabla_activa}` WHERE id = %s", (id_producto,))
        if cursor.rowcount == 0:
            conexion.rollback()
            return False, f"No se encontró el producto #{id_producto} en la base de datos."

        if concepto:
            for tabla_data in DB_PROFILES.values():
                tabla = tabla_data["table"]
                if tabla != tabla_activa:
                    cursor.execute(
                        f"DELETE FROM `{tabla}` WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                        (concepto,)
                    )

        # 3. Si el concepto ya no existe en ninguna tabla de productos, limpiar stock también
        if concepto:
            tablas = [p["table"] for p in DB_PROFILES.values()]
            existencias = 0
            for tabla in tablas:
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{tabla}` WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                    (concepto,)
                )
                resultado = cursor.fetchone()
                existencias += resultado[0] if resultado else 0

            if existencias == 0:
                cursor.execute(
                    f"DELETE FROM `{STOCK_TABLE}` WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                    (concepto,)
                )

        conexion.commit()
        return True, f"Producto #{id_producto} eliminado correctamente."
    except Error as e:
        conexion.rollback()
        return False, f"Error al eliminar en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()
