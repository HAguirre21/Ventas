"""
Módulo de gestión de base de datos MySQL (XAMPP) para el Sistema de Facturación.
Maneja conexiones seguras, transacciones (commit/rollback) y operaciones CRUD para productos.
El stock y el costo de compra se almacenan en `stock`, compartida entre
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


def asegurar_esquema_utilidades() -> bool:
    """
    Verifica y crea automáticamente las tablas de ventas y columnas necesarias
    para el cálculo de utilidades si aún no existen en la base de datos.
    """
    conexion = obtener_conexion(intentos=1)
    if not conexion:
        return False

    cursor = None
    try:
        cursor = conexion.cursor()
        # 1. Asegurar columna 'costo' en productos y productos_costa
        for tabla in ["productos_costa", "productos"]:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = %s 
                  AND COLUMN_NAME = 'costo'
                """,
                (tabla,)
            )
            fila = cursor.fetchone()
            col_exists = fila[0] > 0 if fila else False
            if not col_exists:
                cursor.execute(f"ALTER TABLE `{tabla}` ADD COLUMN `costo` DECIMAL(12, 2) NOT NULL DEFAULT 0.00 AFTER `precio`")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'stock'
              AND COLUMN_NAME = 'costo'
            """
        )
        fila = cursor.fetchone()
        costo_stock_exists = fila[0] > 0 if fila else False
        if not costo_stock_exists:
            cursor.execute(
                "ALTER TABLE `stock` ADD COLUMN `costo` DECIMAL(12, 2) NOT NULL DEFAULT 0.00 AFTER `cantidad`"
            )
            cursor.execute(
                "UPDATE `stock` s JOIN `productos_costa` p "
                "ON LOWER(TRIM(s.concepto)) = LOWER(TRIM(p.concepto)) "
                "SET s.costo = COALESCE(p.costo, 0)"
            )
            cursor.execute(
                "UPDATE `stock` s JOIN `productos` p "
                "ON LOWER(TRIM(s.concepto)) = LOWER(TRIM(p.concepto)) "
                "SET s.costo = COALESCE(p.costo, 0) "
                "WHERE s.costo = 0 AND COALESCE(p.costo, 0) > 0"
            )

        for tabla in ["productos", "productos_costa"]:
            cursor.execute(
                f"INSERT IGNORE INTO `stock` (concepto, cantidad, costo) "
                f"SELECT concepto, 0, COALESCE(costo, 0) FROM `{tabla}`"
            )

        # 2. Asegurar tabla ventas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `ventas` (
                `id` int NOT NULL AUTO_INCREMENT,
                `cliente` varchar(150) NOT NULL DEFAULT 'Cliente General',
                `perfil` varchar(50) NOT NULL DEFAULT 'local',
                `total_venta` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `total_costo` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `utilidad` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `fecha_hora` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                KEY `idx_ventas_fecha` (`fecha_hora`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)

        # 3. Asegurar tabla detalle_ventas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `detalle_ventas` (
                `id` int NOT NULL AUTO_INCREMENT,
                `venta_id` int NOT NULL,
                `concepto` varchar(150) NOT NULL,
                `precio_unitario` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `costo_unitario` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `cantidad` int NOT NULL DEFAULT 1,
                `subtotal` decimal(12, 2) NOT NULL DEFAULT 0.00,
                `utilidad_linea` decimal(12, 2) NOT NULL DEFAULT 0.00,
                PRIMARY KEY (`id`),
                KEY `idx_detalle_venta_id` (`venta_id`),
                CONSTRAINT `fk_detalle_ventas_venta` FOREIGN KEY (`venta_id`) REFERENCES `ventas` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)

        conexion.commit()
        return True
    except Error as e:
        print(f"[DB Schema Setup] Error asegurando tablas de utilidades: {e}")
        try:
            conexion.rollback()
        except Exception:
            pass
        return False
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def verificar_conexion() -> Tuple[bool, str]:
    """
    Verifica si el servidor MySQL está activo y la base de datos existe
    utilizando la conexión protegida con auto-reconexión.
    Asegura automáticamente las tablas y columnas necesarias para utilidades.
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
            # Asegurar tablas requeridas (costo, ventas, detalle_ventas)
            asegurar_esquema_utilidades()
            return True, f"Conectado a '{db_name[0]}' en MySQL (XAMPP)"
        except Exception as e:
            try:
                conexion.close()
            except Exception:
                pass
            return False, f"No se pudo consultar la base de datos: {e}. Asegúrate de que Apache/MySQL estén iniciados en XAMPP."
    return False, "No se pudo conectar a MySQL tras varios intentos. Asegúrate de que Apache/MySQL estén iniciados en XAMPP."


# ------------------------------------------------------------------
# CRUD de Stock centralizado y Catálogo
# ------------------------------------------------------------------

def obtener_todos_los_productos() -> List[Dict[str, Any]]:
    """
    Obtiene la lista completa de productos con su costo y stock desde la tabla `stock`.
    El stock es compartido entre todos los perfiles mediante LEFT JOIN con `stock`.
    Retorna una lista de diccionarios con keys: 'id', 'concepto', 'precio', 'costo', 'cantidad'.
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
            f"SELECT t.id, t.concepto, t.precio, COALESCE(s.costo, 0) AS costo, COALESCE(s.cantidad, 0) AS cantidad "
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
                "costo": Decimal(str(r.get("costo", 0) or 0)),
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


def obtener_costo_por_concepto(concepto: str) -> Decimal:
    """
    Obtiene el costo unitario de un producto según su concepto exacto.
    """
    conexion = obtener_conexion()
    if not conexion:
        return Decimal("0.00")

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(
            f"SELECT COALESCE(costo, 0) FROM `{STOCK_TABLE}` "
            "WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s)) LIMIT 1",
            (concepto,)
        )
        resultado = cursor.fetchone()
        if resultado and resultado[0] is not None:
            return Decimal(str(resultado[0]))
    except Error as e:
        print(f"[DB Error] Error al obtener costo de '{concepto}': {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return Decimal("0.00")


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

def agregar_producto(concepto: str, precio: Decimal, costo: Decimal = Decimal("0.00"), cantidad: int = 0, perfil: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
    """
    Inserta un nuevo producto en el catálogo indicado y crea/actualiza su
    entrada en la tabla centralizada `stock`. Si no se indica un perfil, usa el activo.
    Retorna (éxito: bool, mensaje: str, nuevo_id: int o None).
    """
    concepto = concepto.strip()
    if not concepto:
        return False, "El nombre del producto no puede estar vacío.", None
    if precio <= 0:
        return False, "El precio debe ser un valor mayor a cero.", None
    if costo < 0:
        return False, "El costo no puede ser un número negativo.", None
    if cantidad < 0:
        return False, "La cantidad no puede ser un número negativo.", None

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos MySQL en XAMPP.", None

    cursor = None
    try:
        cursor = conexion.cursor()

        # 1. Insertar el producto únicamente en el catálogo seleccionado
        tabla_principal = _tabla_activa(perfil)
        query_prod = f"INSERT INTO `{tabla_principal}` (concepto, precio, costo) VALUES (%s, %s, %s)"
        cursor.execute(query_prod, (concepto, float(precio), float(costo)))
        nuevo_id = cursor.lastrowid

        # 2. Crear o actualizar el registro en la tabla de stock centralizada
        query_stock = (
            f"INSERT INTO `{STOCK_TABLE}` (concepto, cantidad, costo) VALUES (%s, %s, %s) "
            f"ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad), costo = VALUES(costo)"
        )
        cursor.execute(query_stock, (concepto, int(cantidad), float(costo)))

        conexion.commit()
        return True, f"Producto '{concepto}' agregado exitosamente.", nuevo_id
    except Error as e:
        conexion.rollback()
        return False, f"Error al insertar en MySQL: {e}", None
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def actualizar_producto(id_producto: int, nuevo_concepto: str, nuevo_precio: Decimal, nuevo_costo: Decimal = Decimal("0.00"), nueva_cantidad: int = 0) -> Tuple[bool, str]:
    """
    Actualiza el nombre, precio y costo del producto en el catálogo activo, y
    sincroniza el stock en la tabla centralizada `stock`.
    Retorna (éxito: bool, mensaje: str).
    """
    nuevo_concepto = nuevo_concepto.strip()
    if not nuevo_concepto:
        return False, "El nombre del producto no puede estar vacío."
    if nuevo_precio <= 0:
        return False, "El precio debe ser un número positivo mayor a cero."
    if nuevo_costo < 0:
        return False, "El costo no puede ser un número negativo."
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

        # 2. Actualizar únicamente el catálogo activo
        tabla_activa = _tabla_activa()
        cursor.execute(
            f"UPDATE `{tabla_activa}` SET concepto = %s, precio = %s, costo = %s WHERE id = %s",
            (nuevo_concepto, float(nuevo_precio), float(nuevo_costo), id_producto)
        )

        # 3. Si el nombre cambió, conservar el stock anterior si otro catálogo
        # todavía contiene ese concepto.
        if concepto_anterior.lower() != nuevo_concepto.lower():
            otras_tablas = [
                perfil_data["table"]
                for perfil_data in DB_PROFILES.values()
                if perfil_data["table"] != tabla_activa
            ]
            concepto_en_otra_tabla = False
            for tabla in otras_tablas:
                cursor.execute(
                    f"SELECT COUNT(*) FROM `{tabla}` WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                    (concepto_anterior,)
                )
                resultado = cursor.fetchone()
                concepto_en_otra_tabla = concepto_en_otra_tabla or bool(resultado and resultado[0])

            if not concepto_en_otra_tabla:
                cursor.execute(
                    f"UPDATE `{STOCK_TABLE}` SET concepto = %s WHERE LOWER(TRIM(concepto)) = LOWER(TRIM(%s))",
                    (nuevo_concepto, concepto_anterior)
                )

        # 4. Upsert en stock con la cantidad indicada
        query_stock = (
            f"INSERT INTO `{STOCK_TABLE}` (concepto, cantidad, costo) VALUES (%s, %s, %s) "
            f"ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad), costo = VALUES(costo)"
        )
        cursor.execute(query_stock, (nuevo_concepto, int(nueva_cantidad), float(nuevo_costo)))

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
    Elimina un producto del catálogo activo usando su ID.
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

        # 2. Eliminar únicamente del catálogo activo
        tabla_activa = _tabla_activa()
        cursor.execute(f"DELETE FROM `{tabla_activa}` WHERE id = %s", (id_producto,))
        if cursor.rowcount == 0:
            conexion.rollback()
            return False, f"No se encontró el producto #{id_producto} en la base de datos."

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


# ------------------------------------------------------------------
# Módulo de Ventas y Utilidades Diarias
# ------------------------------------------------------------------

def registrar_venta(cliente: str, items: List[Any], perfil: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
    """
    Registra una factura/venta comercial en la base de datos calculando:
    total_venta, total_costo y la utilidad neta obtenida.
    Acepta objetos de tipo ItemFactura o diccionarios.
    Retorna (éxito: bool, mensaje: str, venta_id: int o None).
    """
    if not items:
        return False, "No hay productos en la factura para registrar la venta.", None

    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos para registrar la venta.", None

    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        perfil_actual = perfil or _active_profile
        tabla = _tabla_activa(perfil_actual)

        # 1. Obtener los costos unitarios actuales de los productos vendidos
        conceptos = []
        for it in items:
            c = getattr(it, "concepto", None) or (it.get("concepto") if isinstance(it, dict) else "")
            if c:
                conceptos.append(c.strip().lower())

        costos_dict: Dict[str, Decimal] = {}
        if conceptos:
            placeholders = ", ".join(["%s"] * len(conceptos))
            cursor.execute(
                f"SELECT LOWER(TRIM(concepto)) as nom, COALESCE(costo, 0) as costo "
                f"FROM `{STOCK_TABLE}` "
                f"WHERE LOWER(TRIM(concepto)) IN ({placeholders})",
                tuple(conceptos)
            )
            for row in cursor.fetchall():
                costos_dict[row["nom"]] = Decimal(str(row["costo"]))

        # 2. Calcular subtotales, costos y utilidades línea por línea
        total_venta = Decimal("0.00")
        total_costo = Decimal("0.00")
        items_procesados = []

        for it in items:
            if isinstance(it, dict):
                concepto = it.get("concepto", "")
                pu = Decimal(str(it.get("precio_unitario", 0)))
                cant = int(it.get("cantidad", 0))
            else:
                concepto = getattr(it, "concepto", "")
                pu = Decimal(str(getattr(it, "precio_unitario", 0)))
                cant = int(getattr(it, "cantidad", 0))

            subtotal = pu * Decimal(cant)
            costo_unitario = costos_dict.get(concepto.strip().lower(), Decimal("0.00"))
            costo_total_item = costo_unitario * Decimal(cant)
            utilidad_item = subtotal - costo_total_item

            total_venta += subtotal
            total_costo += costo_total_item

            items_procesados.append({
                "concepto": concepto,
                "precio_unitario": pu,
                "costo_unitario": costo_unitario,
                "cantidad": cant,
                "subtotal": subtotal,
                "utilidad_linea": utilidad_item,
            })

        utilidad_total = total_venta - total_costo

        # 3. Insertar encabezado en tabla `ventas`
        cursor.execute(
            """
            INSERT INTO `ventas` (cliente, perfil, total_venta, total_costo, utilidad, fecha_hora)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (
                cliente.strip() or "Cliente General",
                perfil_actual,
                float(total_venta),
                float(total_costo),
                float(utilidad_total),
            )
        )
        venta_id = cursor.lastrowid

        # 4. Insertar cada renglón en `detalle_ventas`
        for det in items_procesados:
            cursor.execute(
                """
                INSERT INTO `detalle_ventas`
                (venta_id, concepto, precio_unitario, costo_unitario, cantidad, subtotal, utilidad_linea)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    venta_id,
                    det["concepto"],
                    float(det["precio_unitario"]),
                    float(det["costo_unitario"]),
                    det["cantidad"],
                    float(det["subtotal"]),
                    float(det["utilidad_linea"]),
                )
            )

        conexion.commit()
        return True, f"Venta #{venta_id} guardada exitosamente (Utilidad: ${utilidad_total:,.2f}).", venta_id
    except Error as e:
        conexion.rollback()
        return False, f"Error al registrar venta en MySQL: {e}", None
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def obtener_utilidades_por_fecha(fecha: str) -> Dict[str, Any]:
    """
    Retorna métricas consolidadas e individuales (local y costa) y la lista de ventas
    para una fecha específica (formato 'YYYY-MM-DD').
    """
    res: Dict[str, Any] = {
        "fecha": fecha,
        "total_ventas": Decimal("0.00"),
        "total_costo": Decimal("0.00"),
        "total_utilidad": Decimal("0.00"),
        "margen_porcentaje": Decimal("0.00"),
        "cantidad_ventas": 0,
        "ventas": [],
        "local": {
            "total_ventas": Decimal("0.00"),
            "total_costo": Decimal("0.00"),
            "total_utilidad": Decimal("0.00"),
            "margen_porcentaje": Decimal("0.00"),
            "cantidad_ventas": 0,
            "ventas": []
        },
        "costa": {
            "total_ventas": Decimal("0.00"),
            "total_costo": Decimal("0.00"),
            "total_utilidad": Decimal("0.00"),
            "margen_porcentaje": Decimal("0.00"),
            "cantidad_ventas": 0,
            "ventas": []
        }
    }
    conexion = obtener_conexion()
    if not conexion:
        return res

    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, cliente, perfil, total_venta, total_costo, utilidad, fecha_hora
            FROM `ventas`
            WHERE DATE(fecha_hora) = %s
            ORDER BY fecha_hora DESC, id DESC
            """,
            (fecha,)
        )
        ventas_rows = cursor.fetchall()
        for v in ventas_rows:
            tv = Decimal(str(v["total_venta"]))
            tc = Decimal(str(v["total_costo"]))
            ut = Decimal(str(v["utilidad"]))
            perfil = str(v.get("perfil") or "local").strip().lower()

            res["total_ventas"] += tv
            res["total_costo"] += tc
            res["total_utilidad"] += ut
            
            f_hora = v.get("fecha_hora")
            hora_str = f_hora.strftime("%I:%M %p") if hasattr(f_hora, "strftime") else "--:--"
            
            venta_obj = {
                "id": v["id"],
                "cliente": v["cliente"],
                "perfil": v["perfil"],
                "total_venta": tv,
                "total_costo": tc,
                "utilidad": ut,
                "fecha_hora": f_hora,
                "hora": hora_str
            }
            res["ventas"].append(venta_obj)

            if perfil in ("local", "costa"):
                sub = res[perfil]
                sub["total_ventas"] += tv
                sub["total_costo"] += tc
                sub["total_utilidad"] += ut
                sub["ventas"].append(venta_obj)

        res["cantidad_ventas"] = len(res["ventas"])
        if res["total_ventas"] > Decimal("0.00"):
            res["margen_porcentaje"] = (res["total_utilidad"] / res["total_ventas"]) * Decimal("100.00")

        for k in ("local", "costa"):
            sub = res[k]
            sub["cantidad_ventas"] = len(sub["ventas"])
            if sub["total_ventas"] > Decimal("0.00"):
                sub["margen_porcentaje"] = (sub["total_utilidad"] / sub["total_ventas"]) * Decimal("100.00")

    except Error as e:
        print(f"[DB Error] Error al consultar utilidades de '{fecha}': {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return res


def obtener_detalle_venta(venta_id: int) -> List[Dict[str, Any]]:
    """
    Retorna el desglose de productos que componen una factura/venta.
    """
    detalles = []
    conexion = obtener_conexion()
    if not conexion:
        return detalles

    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, concepto, precio_unitario, costo_unitario, cantidad, subtotal, utilidad_linea
            FROM `detalle_ventas`
            WHERE venta_id = %s
            ORDER BY id ASC
            """,
            (venta_id,)
        )
        for d in cursor.fetchall():
            detalles.append({
                "id": d["id"],
                "concepto": d["concepto"],
                "precio_unitario": Decimal(str(d["precio_unitario"])),
                "costo_unitario": Decimal(str(d["costo_unitario"])),
                "cantidad": int(d["cantidad"]),
                "subtotal": Decimal(str(d["subtotal"])),
                "utilidad_linea": Decimal(str(d["utilidad_linea"])),
            })
    except Error as e:
        print(f"[DB Error] Error al obtener detalle de la venta #{venta_id}: {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return detalles


def obtener_resumen_dias_recientes(dias: int = 15, perfil: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna el balance agrupado por día de las fechas más recientes con ventas.
    Si se especifica perfil ('local' o 'costa'), filtra solo por ese catálogo.
    """
    resumen = []
    conexion = obtener_conexion()
    if not conexion:
        return resumen

    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        if perfil and perfil in ("local", "costa"):
            cursor.execute(
                """
                SELECT 
                    DATE(fecha_hora) AS fecha,
                    COUNT(id) AS cantidad_ventas,
                    COALESCE(SUM(total_venta), 0) AS total_ventas,
                    COALESCE(SUM(total_costo), 0) AS total_costo,
                    COALESCE(SUM(utilidad), 0) AS total_utilidad
                FROM `ventas`
                WHERE LOWER(TRIM(perfil)) = LOWER(TRIM(%s))
                GROUP BY DATE(fecha_hora)
                ORDER BY fecha DESC
                LIMIT %s
                """,
                (perfil, int(dias))
            )
        else:
            cursor.execute(
                """
                SELECT 
                    DATE(fecha_hora) AS fecha,
                    COUNT(id) AS cantidad_ventas,
                    COALESCE(SUM(total_venta), 0) AS total_ventas,
                    COALESCE(SUM(total_costo), 0) AS total_costo,
                    COALESCE(SUM(utilidad), 0) AS total_utilidad
                FROM `ventas`
                GROUP BY DATE(fecha_hora)
                ORDER BY fecha DESC
                LIMIT %s
                """,
                (int(dias),)
            )
        for r in cursor.fetchall():
            tv = Decimal(str(r["total_ventas"]))
            tc = Decimal(str(r["total_costo"]))
            ut = Decimal(str(r["total_utilidad"]))
            margen = (ut / tv * Decimal("100.00")) if tv > 0 else Decimal("0.00")
            resumen.append({
                "fecha": str(r["fecha"]),
                "cantidad_ventas": int(r["cantidad_ventas"]),
                "total_ventas": tv,
                "total_costo": tc,
                "total_utilidad": ut,
                "margen_porcentaje": margen,
            })
    except Error as e:
        print(f"[DB Error] Error al obtener resumen de días recientes: {e}")
    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return resumen


def eliminar_venta(venta_id: int) -> Tuple[bool, str]:
    """
    Elimina una venta registrada y su detalle asociado.
    """
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos."

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM `ventas` WHERE id = %s", (venta_id,))
        if cursor.rowcount == 0:
            conexion.rollback()
            return False, f"No se encontró la venta #{venta_id}."
        conexion.commit()
        return True, f"Venta #{venta_id} eliminada correctamente."
    except Error as e:
        conexion.rollback()
        return False, f"Error al eliminar venta en MySQL: {e}"
    finally:
        if cursor:
            cursor.close()
        conexion.close()
