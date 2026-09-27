

import flet as ft
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any

import db
import pdf_generator


class ItemFactura:
    """Modelo en memoria para los productos agregados a la factura en curso."""
    def __init__(self, concepto: str, precio_unitario: Decimal, cantidad: int):
        self.concepto = concepto
        self.precio_unitario = Decimal(precio_unitario)
        self.cantidad = int(cantidad)
        self.monto = self.precio_unitario * Decimal(self.cantidad)


def main(page: ft.Page):
    # 1. Configuración de Ventana y Tema Material Design 3
    page.title = "Sistema de Inventario y Facturación - Dulcería Loaiza"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL, use_material3=True)
    page.window.maximized = True 
    page.padding = 0
    page.scroll = None

    # 2. Estado de la Aplicación
    items_factura: List[ItemFactura] = []
    catalogo: List[Dict[str, Any]] = []
    gestionar_productos = True

    # 3. Helpers de UI (Notificaciones y Diálogos)
    def notify(mensaje: str, es_error: bool = False, es_advertencia: bool = False):
        color = ft.Colors.RED_700 if es_error else (ft.Colors.AMBER_800 if es_advertencia else ft.Colors.GREEN_700)
        icono = ft.Icons.ERROR_OUTLINE_ROUNDED if es_error else (ft.Icons.WARNING_AMBER_ROUNDED if es_advertencia else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED)
        snack = ft.SnackBar(
            content=ft.Row([ft.Icon(icono, color=ft.Colors.WHITE, size=20), ft.Text(mensaje, color=ft.Colors.WHITE, expand=True)]),
            bgcolor=color,
            duration=3000,
            open=True,
        )
        if snack not in page.overlay:
            page.overlay.append(snack)
        page.update()

    def open_dialog(dialog: ft.AlertDialog):
        if hasattr(page, "show_dialog"):
            page.show_dialog(dialog)
        else:
            if dialog not in page.overlay:
                page.overlay.append(dialog)
            dialog.open = True
            page.update()

    def close_dialog(dialog: ft.AlertDialog):
        if hasattr(page, "pop_dialog"):
            page.pop_dialog()
        else:
            dialog.open = False
            page.update()

    # 4. Estado de Conexión a MySQL en XAMPP
    status_icon = ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.GREY_400, size=12)
    status_text = ft.Text("Verificando Conexión...", size=13, weight=ft.FontWeight.W_500)
    database_mode_text = ft.Text("Ventas locales", size=11, color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600)

    banner_xampp = ft.Banner(
        bgcolor=ft.Colors.AMBER_50,
        leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_900, size=32),
        content=ft.Text("La base de datos no está activa. Iníciala y pulsa 'Reintentar'.", color=ft.Colors.AMBER_900, weight=ft.FontWeight.BOLD),
        actions=[ft.TextButton("Reintentar", icon=ft.Icons.REFRESH_ROUNDED, on_click=lambda e: reload_data(notify_ok=True))],
        visible=False,
    )

    def update_connection_ui(online: bool):
        status_icon.color = ft.Colors.GREEN_600 if online else ft.Colors.RED_600
        status_text.value = "Conectado" if online else "Desconectado"
        status_text.color = ft.Colors.GREEN_800 if online else ft.Colors.RED_800
        database_mode_text.value = db.obtener_nombre_perfil()
        banner_xampp.visible = not online
        page.update()

    def reload_data(notify_ok: bool = False):
        nonlocal catalogo
        online, msg = db.verificar_conexion()
        update_connection_ui(online)
        if online:
            catalogo = db.obtener_todos_los_productos()
            render_catalogo(catalogo)
            if notify_ok:
                notify("Base de datos y catálogo actualizado correctamente.")
        else:
            catalogo = []
            render_catalogo([])
            notify(msg, es_error=True)
        update_suggestions(None)
        page.update()

    # -------------------------------------------------------------
    # 5. Pestaña 1: Facturación / Ventas
    # -------------------------------------------------------------
    inp_concepto = ft.TextField(label="Concepto / Producto", prefix_icon=ft.Icons.SEARCH_ROUNDED, expand=True, border_radius=8, dense=True)
    inp_precio = ft.TextField(label="Precio Unitario ($)", prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED, width=170, read_only=True, border_radius=8, dense=True)
    inp_cantidad = ft.TextField(label="Cantidad", value="1", prefix_icon=ft.Icons.NUMBERS_ROUNDED, width=120, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, dense=True)

    suggestions_col = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO)
    suggestions_box = ft.Container(
        content=suggestions_col,
        visible=False,
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=8,
        padding=6,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK_12),
        height=180,
    )

    def select_suggestion(name: str):
        inp_concepto.value = name
        suggestions_box.visible = False
        precio = db.obtener_precio_por_concepto(name)
        inp_precio.value = f"{precio:.2f}" if precio is not None else "0.00"
        inp_cantidad.focus()
        page.update()

    def update_suggestions(e):
        q = inp_concepto.value.strip().lower()
        suggestions_col.controls.clear()
        if q and catalogo:
            matches = [p for p in catalogo if q in p["concepto"].lower()][:6]
            for m in matches:
                stock_val = m.get("cantidad", 0)
                suggestions_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT_ROUNDED, size=16, color=ft.Colors.PRIMARY),
                                ft.Text(m["concepto"], size=13, weight=ft.FontWeight.W_500),
                            ], spacing=8),
                            ft.Container(
                                content=ft.Text(f"Stock: {stock_val}", size=11, color=ft.Colors.BLUE_GREY_700, weight=ft.FontWeight.W_600),
                                bgcolor=ft.Colors.BLUE_GREY_50,
                                border_radius=4,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border_radius=6,
                        ink=True,
                        on_click=lambda ev, name=m["concepto"]: select_suggestion(name),
                    )
                )
            suggestions_box.visible = bool(matches)
        else:
            suggestions_box.visible = False
        page.update()

    inp_concepto.on_change = update_suggestions

    table_invoice = ft.DataTable(
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        heading_row_color=ft.Colors.PRIMARY_CONTAINER,
        heading_row_height=42,
        data_row_min_height=42,
        column_spacing=24,
        columns=[
            ft.DataColumn(ft.Text("No.", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Producto / Concepto", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Precio Unitario", weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Cantidad", weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Subtotal", weight=ft.FontWeight.BOLD), numeric=True),
            ft.DataColumn(ft.Text("Acción", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
    )

    empty_invoice_box = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.SHOPPING_BAG_OUTLINED, size=44, color=ft.Colors.GREY_400),
                ft.Text("No hay productos en la factura actual.", color=ft.Colors.GREY_600, size=14, weight=ft.FontWeight.W_500),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        padding=30,
        alignment=ft.Alignment.CENTER,
    )

    lbl_total = ft.Text("$0.00", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
    lbl_badge_items = ft.Text("0 ítems", size=13, color=ft.Colors.GREY_700)

    def render_invoice():
        table_invoice.rows.clear()
        total = Decimal("0.00")
        for idx, item in enumerate(items_factura, start=1):
            total += item.monto
            def remove_item(ev, it=item):
                items_factura.remove(it)
                render_invoice()
                notify(f"Se quitó '{it.concepto}' de la factura.")

            table_invoice.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(item.concepto, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(f"${item.precio_unitario:,.2f}")),
                        ft.DataCell(ft.Text(str(item.cantidad))),
                        ft.DataCell(ft.Text(f"${item.monto:,.2f}", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=ft.Colors.RED_600, tooltip="Quitar", on_click=remove_item)),
                    ]
                )
            )
        lbl_total.value = f"${total:,.2f}"
        lbl_badge_items.value = f"{len(items_factura)} ítem(s)"
        table_invoice.visible = len(items_factura) > 0
        empty_invoice_box.visible = len(items_factura) == 0
        page.update()

    def add_to_invoice(e):
        concepto = inp_concepto.value.strip()
        if not concepto:
            notify("Selecciona o escribe un producto.", es_advertencia=True)
            inp_concepto.focus()
            return
        try:
            precio = Decimal(inp_precio.value.strip() or "0")
            if precio <= 0:
                notify("El precio debe ser mayor a 0.", es_error=True)
                return
            cantidad = int(inp_cantidad.value.strip() or "0")
            if cantidad <= 0:
                notify("La cantidad debe ser al menos 1.", es_advertencia=True)
                return
        except (InvalidOperation, ValueError):
            notify("Valores numéricos inválidos.", es_error=True)
            return

        # Validación informativa de stock
        prod_cat = next((p for p in catalogo if p["concepto"].lower() == concepto.lower()), None)
        if prod_cat:
            stock_disp = prod_cat.get("cantidad", 0)
            ya_agregado = sum(it.cantidad for it in items_factura if it.concepto.lower() == concepto.lower())
            if ya_agregado + cantidad > stock_disp:
                notify(f"Atención: Stock disponible ({stock_disp}) es menor a la cantidad total facturada ({ya_agregado + cantidad}).", es_advertencia=True)

        items_factura.append(ItemFactura(concepto, precio, cantidad))
        inp_concepto.value = ""
        inp_precio.value = ""
        inp_cantidad.value = "1"
        suggestions_box.visible = False
        render_invoice()
        notify(f"'{concepto}' agregado a la factura.")
        inp_concepto.focus()

    def generate_pdf_action(e):
        if not items_factura:
            notify("Agrega al menos un producto a la factura.", es_advertencia=True)
            return

        client_name = ft.TextField(
            label="Nombre del cliente",
            hint_text="Escribe el nombre del cliente",
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            autofocus=True,
        )

        def confirm_pdf(ev, dialog):
            nombre = client_name.value.strip()
            if not nombre:
                notify("Escribe el nombre del cliente.", es_advertencia=True)
                client_name.focus()
                return
            close_dialog(dialog)
            ok, res = pdf_generator.generar_factura_pdf(items_factura, {"nombre": nombre})
            if ok:
                ok_stock, msg_stock = db.descontar_stock_productos(items_factura)
                ok_venta, msg_venta, venta_id = db.registrar_venta(nombre, items_factura, db.obtener_perfil_actual())
                items_factura.clear()
                render_invoice()
                reload_data()
                reload_utilidades()
                if ok_stock and ok_venta:
                    notify(f"Factura generada, venta #{venta_id} registrada en utilidades y stock descontado exitosamente.")
                else:
                    notify(f"Factura generada. Stock: {msg_stock} | Venta: {msg_venta}", es_advertencia=True)
            else:
                notify(f"Error al generar PDF: {res}", es_error=True)

        client_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, color=ft.Colors.TEAL_700),
                ft.Text("Datos del cliente", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Container(content=client_name, width=380),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: close_dialog(client_dialog)),
                ft.FilledButton("Generar factura", icon=ft.Icons.PICTURE_AS_PDF_ROUNDED, on_click=lambda ev: confirm_pdf(ev, client_dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(client_dialog)

    # -------------------------------------------------------------
    # 6. Pestaña 2: Catálogo de Productos (MySQL CRUD)
    # -------------------------------------------------------------
    inp_search_cat = ft.TextField(
        hint_text="Buscar por nombre o ID...",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        expand=True,
        border_radius=10,
        dense=True,
    )

    lbl_cat_count = ft.Text("", size=12, color=ft.Colors.GREY_600, italic=True)

    table_catalogo = ft.DataTable(
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
        heading_row_height=46,
        data_row_min_height=46,
        column_spacing=28,
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Nombre del Producto", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Stock", weight=ft.FontWeight.BOLD, size=13), numeric=True),
            ft.DataColumn(ft.Text("Costo Compra", weight=ft.FontWeight.BOLD, size=13), numeric=True),
            ft.DataColumn(ft.Text("Precio Venta", weight=ft.FontWeight.BOLD, size=13), numeric=True),
            ft.DataColumn(ft.Text("Utilidad Unit.", weight=ft.FontWeight.BOLD, size=13), numeric=True),
            ft.DataColumn(ft.Text("Acciones", weight=ft.FontWeight.BOLD, size=13)),
        ],
        rows=[],
    )

    empty_catalogo_box = ft.Container(
        content=ft.Column([ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=44, color=ft.Colors.GREY_400), ft.Text("No se encontraron productos.", color=ft.Colors.GREY_600)], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=30,
        alignment=ft.Alignment.CENTER,
    )

    def open_create_modal(e):
        if not gestionar_productos:
            notify("La base de datos de la costa esta en modo solo consulta.", es_advertencia=True)
            return
        name_field = ft.TextField(label="Nombre del Producto", border_radius=8, autofocus=True)
        qty_field = ft.TextField(label="Cantidad en Stock", value="0", border_radius=8, prefix_icon=ft.Icons.NUMBERS_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)
        cost_field = ft.TextField(label="Costo Unitario ($) [Compra]", value="0.00", border_radius=8, prefix_icon=ft.Icons.MONETIZATION_ON_OUTLINED, keyboard_type=ft.KeyboardType.NUMBER)
        price_field = ft.TextField(label="Precio Unitario ($) [Venta]", border_radius=8, prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)

        def save_new(ev, dlg):
            nom = name_field.value.strip()
            pr_str = price_field.value.strip()
            cost_str = cost_field.value.strip()
            qty_str = qty_field.value.strip()

            if not nom or not pr_str:
                notify("Completa todos los campos obligatorios.", es_advertencia=True)
                return
            try:
                pr = Decimal(pr_str)
                if pr <= 0:
                    notify("El precio debe ser positivo.", es_error=True)
                    return
            except Exception:
                notify("Precio inválido.", es_error=True)
                return
            try:
                cost = Decimal(cost_str or "0")
                if cost < 0:
                    notify("El costo no puede ser negativo.", es_error=True)
                    return
            except Exception:
                notify("Costo inválido.", es_error=True)
                return
            try:
                qty = int(qty_str or "0")
                if qty < 0:
                    notify("La cantidad no puede ser negativa.", es_error=True)
                    return
            except Exception:
                notify("Cantidad inválida.", es_error=True)
                return
            ok, msj, new_id = db.agregar_producto(nom, pr, cost, qty)
            if ok:
                close_dialog(dlg)
                reload_data()
                notify(f"Producto '{nom}' creado exitosamente (ID #{new_id}).")
            else:
                notify(msj, es_error=True)

        dlg_create = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.ADD_BOX_ROUNDED, color=ft.Colors.PRIMARY), ft.Text("Nuevo Producto", weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Container(content=ft.Column([name_field, qty_field, cost_field, price_field], spacing=10, tight=True), width=420),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: close_dialog(dlg_create)),
                ft.FilledButton("Guardar", icon=ft.Icons.SAVE_ROUNDED, on_click=lambda ev: save_new(ev, dlg_create)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(dlg_create)

    def open_edit_modal(prod: Dict[str, Any]):
        if not gestionar_productos:
            notify("Activa el modo de gestion para modificar productos.", es_advertencia=True)
            return
        name_field = ft.TextField(label="Nombre del Producto", value=prod["concepto"], border_radius=8, autofocus=True)
        qty_field = ft.TextField(label="Cantidad en Stock", value=str(prod.get("cantidad", 0)), border_radius=8, prefix_icon=ft.Icons.NUMBERS_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)
        cost_val = prod.get("costo", Decimal("0.00"))
        cost_field = ft.TextField(label="Costo Unitario ($) [Compra]", value=f"{cost_val:.2f}", border_radius=8, prefix_icon=ft.Icons.MONETIZATION_ON_OUTLINED, keyboard_type=ft.KeyboardType.NUMBER)
        price_field = ft.TextField(label="Precio Unitario ($) [Venta]", value=f"{prod['precio']:.2f}", border_radius=8, prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)

        def save_edit(ev, dlg):
            nom = name_field.value.strip()
            pr_str = price_field.value.strip()
            cost_str = cost_field.value.strip()
            qty_str = qty_field.value.strip()

            if not nom:
                notify("El nombre no puede estar vacío.", es_advertencia=True)
                return
            try:
                pr = Decimal(pr_str)
                if pr <= 0:
                    notify("El precio debe ser positivo.", es_error=True)
                    return
            except Exception:
                notify("Precio inválido.", es_error=True)
                return
            try:
                cost = Decimal(cost_str or "0")
                if cost < 0:
                    notify("El costo no puede ser negativo.", es_error=True)
                    return
            except Exception:
                notify("Costo inválido.", es_error=True)
                return
            try:
                qty = int(qty_str or "0")
                if qty < 0:
                    notify("La cantidad no puede ser negativa.", es_error=True)
                    return
            except Exception:
                notify("Cantidad inválida.", es_error=True)
                return
            ok, msj = db.actualizar_producto(prod["id"], nom, pr, cost, qty)
            if ok:
                close_dialog(dlg)
                reload_data()
                notify(f"Producto #{prod['id']} actualizado en la Base de Datos.")
            else:
                notify(msj, es_error=True)

        dlg_edit = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.EDIT_ROUNDED, color=ft.Colors.PRIMARY), ft.Text(f"Editar Producto #{prod['id']}", weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Container(content=ft.Column([name_field, qty_field, cost_field, price_field], spacing=10, tight=True), width=420),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: close_dialog(dlg_edit)),
                ft.FilledButton("Guardar Cambios", icon=ft.Icons.CHECK_ROUNDED, on_click=lambda ev: save_edit(ev, dlg_edit)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(dlg_edit)

    def open_delete_modal(prod: Dict[str, Any]):
        if not gestionar_productos:
            notify("Activa el modo de gestion para eliminar productos.", es_advertencia=True)
            return
        def confirm_del(ev, dlg):
            ok, msj = db.eliminar_producto(prod["id"])
            close_dialog(dlg)
            if ok:
                reload_data()
                notify(f"Producto '{prod['concepto']}' eliminado de la Base de Datos.")
            else:
                notify(msj, es_error=True)

        dlg_del = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED_600), ft.Text("Confirmar Eliminación", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Text(f"¿Deseas eliminar permanentemente '{prod['concepto']}' (ID #{prod['id']}) de la Base de Datos?", size=14),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: close_dialog(dlg_del)),
                ft.FilledButton("Eliminar", icon=ft.Icons.DELETE_FOREVER_ROUNDED, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE), on_click=lambda ev: confirm_del(ev, dlg_del)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(dlg_del)

    def render_catalogo(prods_to_show: List[Dict[str, Any]]):
        table_catalogo.rows.clear()
        puede_gestionar = gestionar_productos
        for p in prods_to_show:
            costo_val = Decimal(str(p.get("costo", 0) or 0))
            precio_val = Decimal(str(p.get("precio", 0) or 0))
            utilidad_val = precio_val - costo_val
            pct = (utilidad_val / precio_val * 100) if precio_val > 0 else Decimal(0)

            table_catalogo.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"#{p['id']}", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.INDIGO_700),
                                bgcolor=ft.Colors.INDIGO_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Row([
                                ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=16, color=ft.Colors.GREY_500),
                                ft.Text(p["concepto"], weight=ft.FontWeight.W_500, size=13),
                            ], spacing=6)
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(str(p.get("cantidad", 0)), weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.BLUE_GREY_800),
                                bgcolor=ft.Colors.BLUE_GREY_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"${costo_val:,.2f}", weight=ft.FontWeight.W_600, size=13, color=ft.Colors.BLUE_GREY_800),
                                bgcolor=ft.Colors.BLUE_GREY_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"${precio_val:,.2f}", weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.INDIGO_900),
                                bgcolor=ft.Colors.INDIGO_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    f"${utilidad_val:,.2f} ({pct:.0f}%)",
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    color=ft.Colors.GREEN_800 if utilidad_val >= 0 else ft.Colors.RED_800,
                                ),
                                bgcolor=ft.Colors.GREEN_50 if utilidad_val >= 0 else ft.Colors.RED_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.Button(
                                        "Editar",
                                        icon=ft.Icons.EDIT_ROUNDED,
                                        height=34,
                                        style=ft.ButtonStyle(
                                            bgcolor=ft.Colors.INDIGO_50,
                                            color=ft.Colors.INDIGO_700,
                                            overlay_color=ft.Colors.INDIGO_100,
                                            elevation=0,
                                            shape=ft.RoundedRectangleBorder(radius=8),
                                        ),
                                        on_click=lambda ev, item=p: open_edit_modal(item),
                                    ),
                                    ft.Button(
                                        "Eliminar",
                                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                        height=34,
                                        style=ft.ButtonStyle(
                                            bgcolor=ft.Colors.RED_50,
                                            color=ft.Colors.RED_700,
                                            overlay_color=ft.Colors.RED_100,
                                            elevation=0,
                                            shape=ft.RoundedRectangleBorder(radius=8),
                                        ),
                                        on_click=lambda ev, item=p: open_delete_modal(item),
                                    ),
                                ],
                                spacing=6,
                                disabled=not puede_gestionar,
                            )
                        ),
                    ]
                )
            )
        table_catalogo.visible = len(prods_to_show) > 0
        empty_catalogo_box.visible = len(prods_to_show) == 0
        q = inp_search_cat.value.strip()
        lbl_cat_count.value = f"Mostrando {len(prods_to_show)} de {len(catalogo)} producto(s)" if q else ""
        page.update()

    def filter_catalogo_event(e):
        q = inp_search_cat.value.strip().lower()
        filtered = [p for p in catalogo if q in p["concepto"].lower() or q == str(p["id"])] if q else catalogo
        render_catalogo(filtered)

    inp_search_cat.on_change = filter_catalogo_event

    # -------------------------------------------------------------
    # 7. Ensamblado del Layout Principal
    # -------------------------------------------------------------
    page.bgcolor = ft.Colors.BLUE_GREY_50

    invoice_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Column([ft.Text("Nueva factura", size=28, weight=ft.FontWeight.BOLD), ft.Text("Crea tu factura en pocos pasos", color=ft.Colors.BLUE_GREY_700)], spacing=3),
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.TODAY_ROUNDED, size=17, color=ft.Colors.TEAL_700), ft.Text("Facturas del día", color=ft.Colors.TEAL_800, weight=ft.FontWeight.W_600)], spacing=8), padding=ft.Padding.symmetric(horizontal=14, vertical=9), bgcolor=ft.Colors.TEAL_50, border_radius=20),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Column([
                    ft.Container(content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.ADD_SHOPPING_CART_ROUNDED, color=ft.Colors.TEAL_700), ft.Text("Añadir productos", size=17, weight=ft.FontWeight.BOLD)], spacing=8),
                        ft.Text("Busca un producto del catálogo y define la cantidad.", size=12, color=ft.Colors.BLUE_GREY_600),
                        ft.Row([inp_concepto, inp_precio, inp_cantidad], spacing=10),
                        ft.Row([ft.Container(content=ft.Text(""), expand=True), ft.FilledButton("Añadir a la factura", icon=ft.Icons.ADD_ROUNDED, height=44, on_click=add_to_invoice)],),
                        suggestions_box,
                    ], spacing=10), padding=20, bgcolor=ft.Colors.WHITE, border_radius=14),
                    ft.Container(content=ft.Column([
                        ft.Row([ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, color=ft.Colors.TEAL_700), ft.Text("Productos añadidos", size=17, weight=ft.FontWeight.BOLD)], spacing=8), lbl_badge_items], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                        ft.Container(content=ft.Column([table_invoice, empty_invoice_box], scroll=ft.ScrollMode.AUTO), height=270),
                    ], spacing=12), padding=20, bgcolor=ft.Colors.WHITE, border_radius=14, expand=True),
                ], spacing=16, expand=True),
                ft.Container(content=ft.Column([
                    ft.Text("Resumen", size=17, weight=ft.FontWeight.BOLD),
                    ft.Container(content=ft.Column([ft.Text("TOTAL A PAGAR", size=11, color=ft.Colors.BLUE_GREY_600, weight=ft.FontWeight.BOLD), lbl_total], spacing=3), padding=18, bgcolor=ft.Colors.TEAL_50, border_radius=12),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    ft.Text("Revisa los productos antes de generar el documento.", size=12, color=ft.Colors.BLUE_GREY_600),
                    ft.Container(content=ft.Text(""), expand=True),
                    ft.OutlinedButton("Vaciar factura", icon=ft.Icons.DELETE_SWEEP_OUTLINED, width=190, on_click=lambda e: (items_factura.clear(), render_invoice(), notify("Factura reiniciada."))),
                    ft.FilledButton("Generar factura PDF", icon=ft.Icons.PICTURE_AS_PDF_ROUNDED, width=190, height=48, style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_600, color=ft.Colors.WHITE), on_click=generate_pdf_action),
                ], spacing=14), padding=20, width=235, bgcolor=ft.Colors.WHITE, border_radius=14),
            ], spacing=16, expand=True),
        ], spacing=18, expand=True),
        padding=ft.Padding.only(left=28, right=28, top=24, bottom=20), expand=True,
    )

    catalog_create_button = ft.FilledButton("Crear producto", icon=ft.Icons.ADD_ROUNDED, height=44, style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_600, color=ft.Colors.WHITE), on_click=open_create_modal)

    catalog_view = ft.Container(content=ft.Column([
        ft.Row([
            ft.Column([ft.Text("Catálogo de productos", size=28, weight=ft.FontWeight.BOLD), ft.Text("Nombres y precios que aparecen al crear una factura", color=ft.Colors.BLUE_GREY_700)], spacing=3),
            catalog_create_button,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(content=ft.Column([
            ft.Row([ft.Row([ft.Icon(ft.Icons.SEARCH_ROUNDED, color=ft.Colors.BLUE_GREY_600), inp_search_cat], spacing=8, expand=True), ft.FilledTonalButton("Actualizar", icon=ft.Icons.REFRESH_ROUNDED, on_click=lambda e: reload_data(notify_ok=True))], spacing=12),
            lbl_cat_count,
            ft.Container(content=ft.Column([table_catalogo, empty_catalogo_box], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), expand=True),
        ], spacing=14), padding=20, bgcolor=ft.Colors.WHITE, border_radius=14, expand=True),
    ], spacing=18, expand=True), padding=ft.Padding.only(left=28, right=28, top=24, bottom=20), expand=True, visible=False)

    def change_database(e):
        nonlocal gestionar_productos
        perfil = "costa" if database_switch.value else "local"
        db.seleccionar_perfil(perfil)
        gestionar_productos = costa_manage_switch.value
        catalog_create_button.disabled = not gestionar_productos
        items_factura.clear()
        render_invoice()
        reload_data(notify_ok=True)
        notify(f"Ahora trabajas con {db.obtener_nombre_perfil()}.")

    def change_costa_permissions(e):
        nonlocal gestionar_productos
        gestionar_productos = costa_manage_switch.value
        catalog_create_button.disabled = not gestionar_productos
        render_catalogo(catalogo)
        page.update()

    database_switch = ft.Switch(label="Activar inventario de la costa", value=False, label_text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900, size=13), on_change=change_database)
    costa_manage_switch = ft.Switch(label="Permitir gestionar productos", value=True, label_text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900, size=13), on_change=change_costa_permissions)

    # -------------------------------------------------------------
    # 7. Pestaña 3: Utilidades Diarias
    # -------------------------------------------------------------
    fecha_utilidades = datetime.now().strftime("%Y-%m-%d")

    inp_fecha_utilidades = ft.TextField(
        label="Fecha (AAAA-MM-DD)",
        value=fecha_utilidades,
        width=150,
        border_radius=8,
        dense=True,
        text_align=ft.TextAlign.CENTER,
    )

    filtro_origen = "todos"  # "todos", "local", "costa"

    kpi_ventas_val = ft.Text("$0.00", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_900)
    kpi_ventas_sub = ft.Text("0 facturas", size=11, color=ft.Colors.TEAL_700)

    kpi_costo_val = ft.Text("$0.00", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900)
    kpi_costo_sub = ft.Text("Inversión en productos", size=11, color=ft.Colors.BLUE_GREY_600)

    kpi_utilidad_val = ft.Text("$0.00", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
    kpi_utilidad_sub = ft.Text("Ganancia real del día", size=11, color=ft.Colors.GREEN_800)

    kpi_margen_val = ft.Text("0.0%", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900)
    kpi_margen_sub = ft.Text("Margen / Rentabilidad", size=11, color=ft.Colors.AMBER_800)

    # Indicadores individuales para Productos Locales vs Productos Costa
    local_kpi_ventas = ft.Text("$0.00", size=17, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900)
    local_kpi_costo = ft.Text("$0.00", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700)
    local_kpi_utilidad = ft.Text("$0.00", size=17, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
    local_kpi_margen = ft.Text("0.0%", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900)
    local_kpi_cant = ft.Text("0 ventas", size=11, color=ft.Colors.BLUE_GREY_600)

    costa_kpi_ventas = ft.Text("$0.00", size=17, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_900)
    costa_kpi_costo = ft.Text("$0.00", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700)
    costa_kpi_utilidad = ft.Text("$0.00", size=17, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
    costa_kpi_margen = ft.Text("0.0%", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900)
    costa_kpi_cant = ft.Text("0 ventas", size=11, color=ft.Colors.BLUE_GREY_600)

    def crear_tarjeta_kpi(titulo: str, valor_ctrl: ft.Text, subtitulo_ctrl: ft.Text, icono: str, color_tema: str, bg_color: str):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icono, color=color_tema, size=28),
                    padding=12,
                    bgcolor=bg_color,
                    border_radius=12,
                ),
                ft.Column([
                    ft.Text(titulo, size=11, color=ft.Colors.BLUE_GREY_700, weight=ft.FontWeight.BOLD),
                    valor_ctrl,
                    subtitulo_ctrl,
                ], spacing=2, expand=True),
            ], spacing=14, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=14,
            padding=16,
            expand=True,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=6, color=ft.Colors.BLACK_12),
        )

    card_ventas = crear_tarjeta_kpi("VENTAS TOTALES", kpi_ventas_val, kpi_ventas_sub, ft.Icons.POINT_OF_SALE_ROUNDED, ft.Colors.TEAL_700, ft.Colors.TEAL_50)
    card_costo = crear_tarjeta_kpi("COSTO TOTAL", kpi_costo_val, kpi_costo_sub, ft.Icons.SHOPPING_BAG_OUTLINED, ft.Colors.BLUE_GREY_700, ft.Colors.BLUE_GREY_100)
    card_utilidad = crear_tarjeta_kpi("UTILIDAD NETA", kpi_utilidad_val, kpi_utilidad_sub, ft.Icons.ATTACH_MONEY_ROUNDED, ft.Colors.GREEN_700, ft.Colors.GREEN_50)
    card_margen = crear_tarjeta_kpi("MARGEN COMERCIAL", kpi_margen_val, kpi_margen_sub, ft.Icons.PERCENT_ROUNDED, ft.Colors.AMBER_800, ft.Colors.AMBER_50)

    # Tarjetas de desglose individual (Productos Locales vs Productos Costa)
    card_desglose_local = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.STOREFRONT_ROUNDED, color=ft.Colors.INDIGO_700, size=20),
                        bgcolor=ft.Colors.INDIGO_100,
                        padding=6,
                        border_radius=8,
                    ),
                    ft.Column([
                        ft.Text("Ventas Locales (productos)", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900),
                        ft.Text("Catálogo principal de productos", size=11, color=ft.Colors.BLUE_GREY_600),
                    ], spacing=1),
                ], spacing=8),
                ft.Container(content=local_kpi_cant, bgcolor=ft.Colors.INDIGO_100, border_radius=6, padding=ft.Padding.symmetric(horizontal=8, vertical=2)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=ft.Colors.INDIGO_100),
            ft.Row([
                ft.Column([
                    ft.Text("TOTAL VENTAS", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_600),
                    local_kpi_ventas,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("TOTAL COSTO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_600),
                    local_kpi_costo,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("UTILIDAD NETA", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                    local_kpi_utilidad,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("MARGEN %", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900),
                    local_kpi_margen,
                ], spacing=1, expand=True),
            ], spacing=8),
        ], spacing=8),
        bgcolor=ft.Colors.INDIGO_50,
        border=ft.Border.all(1, ft.Colors.INDIGO_200),
        border_radius=12,
        padding=14,
        expand=True,
    )

    card_desglose_costa = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.BEACH_ACCESS_ROUNDED, color=ft.Colors.ORANGE_800, size=20),
                        bgcolor=ft.Colors.ORANGE_100,
                        padding=6,
                        border_radius=8,
                    ),
                    ft.Column([
                        ft.Text("Ventas Costa (productos_costa)", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_900),
                        ft.Text("Catálogo especial de la costa", size=11, color=ft.Colors.BLUE_GREY_600),
                    ], spacing=1),
                ], spacing=8),
                ft.Container(content=costa_kpi_cant, bgcolor=ft.Colors.ORANGE_100, border_radius=6, padding=ft.Padding.symmetric(horizontal=8, vertical=2)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=ft.Colors.ORANGE_100),
            ft.Row([
                ft.Column([
                    ft.Text("TOTAL VENTAS", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_600),
                    costa_kpi_ventas,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("TOTAL COSTO", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_600),
                    costa_kpi_costo,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("UTILIDAD NETA", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                    costa_kpi_utilidad,
                ], spacing=1, expand=True),
                ft.Column([
                    ft.Text("MARGEN %", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900),
                    costa_kpi_margen,
                ], spacing=1, expand=True),
            ], spacing=8),
        ], spacing=8),
        bgcolor=ft.Colors.ORANGE_50,
        border=ft.Border.all(1, ft.Colors.ORANGE_200),
        border_radius=12,
        padding=14,
        expand=True,
    )

    table_ventas_dia = ft.DataTable(
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
        heading_row_height=44,
        data_row_min_height=44,
        column_spacing=22,
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Hora", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Cliente", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Perfil", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Total Venta", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Costo Total", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Utilidad", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Acciones", weight=ft.FontWeight.BOLD, size=12)),
        ],
        rows=[],
    )

    empty_ventas_box = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=40, color=ft.Colors.GREY_400),
            ft.Text("No se registran ventas para esta fecha con el filtro seleccionado.", color=ft.Colors.GREY_600, weight=ft.FontWeight.W_500, size=13),
            ft.Text("Cada factura generada se registrará automáticamente aquí con su utilidad.", color=ft.Colors.GREY_500, size=11),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
        padding=24,
        alignment=ft.Alignment.CENTER,
    )

    # Tabla: Últimos días con actividad (la opción solicitada por el usuario con espaciado limpio)
    table_resumen_dias = ft.DataTable(
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
        heading_row_height=42,
        data_row_min_height=42,
        column_spacing=36,
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("Fecha", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Ventas", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Total Venta", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Total Costo", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Utilidad Diaria", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Margen", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ft.DataColumn(ft.Text("Acción", weight=ft.FontWeight.BOLD, size=12)),
        ],
        rows=[],
    )

    def open_sale_detail_modal(v: Dict[str, Any]):
        detalles = db.obtener_detalle_venta(v["id"])
        filas = []
        for d in detalles:
            ut = d["utilidad_linea"]
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(d["concepto"], size=12, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(str(d["cantidad"]), size=12)),
                        ft.DataCell(ft.Text(f"${d['costo_unitario']:,.2f}", size=12, color=ft.Colors.BLUE_GREY_700)),
                        ft.DataCell(ft.Text(f"${d['precio_unitario']:,.2f}", size=12, color=ft.Colors.INDIGO_700)),
                        ft.DataCell(ft.Text(f"${d['subtotal']:,.2f}", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"${ut:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800 if ut >= 0 else ft.Colors.RED_800),
                                bgcolor=ft.Colors.GREEN_50 if ut >= 0 else ft.Colors.RED_50,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4,
                            )
                        ),
                    ]
                )
            )

        table_det = ft.DataTable(
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
            heading_row_height=38,
            data_row_min_height=38,
            column_spacing=18,
            columns=[
                ft.DataColumn(ft.Text("Producto", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Cant.", weight=ft.FontWeight.BOLD, size=12), numeric=True),
                ft.DataColumn(ft.Text("Costo Unit.", weight=ft.FontWeight.BOLD, size=12), numeric=True),
                ft.DataColumn(ft.Text("Precio Venta", weight=ft.FontWeight.BOLD, size=12), numeric=True),
                ft.DataColumn(ft.Text("Subtotal", weight=ft.FontWeight.BOLD, size=12), numeric=True),
                ft.DataColumn(ft.Text("Utilidad Línea", weight=ft.FontWeight.BOLD, size=12), numeric=True),
            ],
            rows=filas,
        )

        dlg_det = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color=ft.Colors.TEAL_700),
                ft.Text(f"Detalle de Venta #{v['id']} - {v['cliente']}", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Text(f"Hora: {v['hora']}", size=12, weight=ft.FontWeight.W_600), bgcolor=ft.Colors.BLUE_GREY_50, padding=6, border_radius=6),
                        ft.Container(content=ft.Text(f"Perfil: {v['perfil'].capitalize()}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900 if v['perfil'] == 'local' else ft.Colors.ORANGE_900), bgcolor=ft.Colors.INDIGO_50 if v['perfil'] == 'local' else ft.Colors.ORANGE_50, padding=6, border_radius=6),
                        ft.Container(content=ft.Text(f"Venta: ${v['total_venta']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_800), bgcolor=ft.Colors.INDIGO_50, padding=6, border_radius=6),
                        ft.Container(content=ft.Text(f"Costo: ${v['total_costo']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800), bgcolor=ft.Colors.BLUE_GREY_50, padding=6, border_radius=6),
                        ft.Container(content=ft.Text(f"Utilidad: ${v['utilidad']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800), bgcolor=ft.Colors.GREEN_50, padding=6, border_radius=6),
                    ], spacing=8, wrap=True),
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                    ft.Container(content=ft.Column([table_det], scroll=ft.ScrollMode.AUTO), height=240),
                ], spacing=12, tight=True),
                width=650,
            ),
            actions=[
                ft.FilledButton("Cerrar", on_click=lambda ev: close_dialog(dlg_det)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(dlg_det)

    def open_delete_sale_modal(v: Dict[str, Any]):
        def confirm_del_sale(ev, dlg):
            ok, msj = db.eliminar_venta(v["id"])
            close_dialog(dlg)
            if ok:
                reload_utilidades()
                notify(f"Venta #{v['id']} anulada correctamente.")
            else:
                notify(msj, es_error=True)

        dlg_del = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.RED_600), ft.Text("Anular / Eliminar Venta", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Text(f"¿Estás seguro de anular la venta #{v['id']} de '{v['cliente']}' por un total de ${v['total_venta']:,.2f}?", size=13),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: close_dialog(dlg_del)),
                ft.FilledButton("Anular Venta", icon=ft.Icons.DELETE_FOREVER_ROUNDED, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE), on_click=lambda ev: confirm_del_sale(ev, dlg_del)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(dlg_del)

    # Botones de filtro de origen (Todos, Locales, Costa)
    def set_filtro_origen(nuevo_filtro: str):
        nonlocal filtro_origen
        filtro_origen = nuevo_filtro
        actualizar_estilo_botones_filtro()
        reload_utilidades()

    btn_filtro_todos = ft.Button(
        "Todas las ventas",
        icon=ft.Icons.SELECT_ALL_ROUNDED,
        height=34,
        on_click=lambda e: set_filtro_origen("todos"),
    )
    btn_filtro_local = ft.Button(
        "Ventas locales (productos)",
        icon=ft.Icons.STOREFRONT_ROUNDED,
        height=34,
        on_click=lambda e: set_filtro_origen("local"),
    )
    btn_filtro_costa = ft.Button(
        "Ventas costa (productos_costa)",
        icon=ft.Icons.BEACH_ACCESS_ROUNDED,
        height=34,
        on_click=lambda e: set_filtro_origen("costa"),
    )

    def actualizar_estilo_botones_filtro():
        btn_filtro_todos.style = ft.ButtonStyle(
            bgcolor=ft.Colors.TEAL_700 if filtro_origen == "todos" else ft.Colors.WHITE,
            color=ft.Colors.WHITE if filtro_origen == "todos" else ft.Colors.BLUE_GREY_800,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=2 if filtro_origen == "todos" else 0,
        )
        btn_filtro_local.style = ft.ButtonStyle(
            bgcolor=ft.Colors.INDIGO_700 if filtro_origen == "local" else ft.Colors.WHITE,
            color=ft.Colors.WHITE if filtro_origen == "local" else ft.Colors.INDIGO_900,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=2 if filtro_origen == "local" else 0,
        )
        btn_filtro_costa.style = ft.ButtonStyle(
            bgcolor=ft.Colors.ORANGE_800 if filtro_origen == "costa" else ft.Colors.WHITE,
            color=ft.Colors.WHITE if filtro_origen == "costa" else ft.Colors.ORANGE_900,
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation=2 if filtro_origen == "costa" else 0,
        )

    actualizar_estilo_botones_filtro()

    def reload_utilidades():
        fecha_act = inp_fecha_utilidades.value.strip() or datetime.now().strftime("%Y-%m-%d")
        data_dia = db.obtener_utilidades_por_fecha(fecha_act)

        # 1. Actualizar desglose individual fijo (Locales vs Costa)
        dl = data_dia.get("local", {})
        dc = data_dia.get("costa", {})

        local_kpi_ventas.value = f"${dl.get('total_ventas', Decimal('0.00')):,.2f}"
        local_kpi_costo.value = f"${dl.get('total_costo', Decimal('0.00')):,.2f}"
        local_kpi_utilidad.value = f"${dl.get('total_utilidad', Decimal('0.00')):,.2f}"
        local_kpi_margen.value = f"{dl.get('margen_porcentaje', Decimal('0.00')):.1f}%"
        local_kpi_cant.value = f"{dl.get('cantidad_ventas', 0)} venta(s)"

        costa_kpi_ventas.value = f"${dc.get('total_ventas', Decimal('0.00')):,.2f}"
        costa_kpi_costo.value = f"${dc.get('total_costo', Decimal('0.00')):,.2f}"
        costa_kpi_utilidad.value = f"${dc.get('total_utilidad', Decimal('0.00')):,.2f}"
        costa_kpi_margen.value = f"{dc.get('margen_porcentaje', Decimal('0.00')):.1f}%"
        costa_kpi_cant.value = f"{dc.get('cantidad_ventas', 0)} venta(s)"

        # 2. Actualizar KPIs principales según el filtro activo (todos, local, costa)
        fuente = data_dia if filtro_origen == "todos" else data_dia.get(filtro_origen, {})
        tv = fuente.get("total_ventas", Decimal("0.00"))
        tc = fuente.get("total_costo", Decimal("0.00"))
        ut = fuente.get("total_utilidad", Decimal("0.00"))
        mg = fuente.get("margen_porcentaje", Decimal("0.00"))
        cant = fuente.get("cantidad_ventas", 0)

        etiqueta_filtro = "totales" if filtro_origen == "todos" else ("locales" if filtro_origen == "local" else "costa")
        kpi_ventas_val.value = f"${tv:,.2f}"
        kpi_ventas_sub.value = f"{cant} factura(s) {etiqueta_filtro}"

        kpi_costo_val.value = f"${tc:,.2f}"
        kpi_costo_sub.value = "Inversión en mercancía"

        kpi_utilidad_val.value = f"${ut:,.2f}"
        kpi_utilidad_val.color = ft.Colors.GREEN_700 if ut >= 0 else ft.Colors.RED_700
        kpi_utilidad_sub.value = f"Ganancia neta ({etiqueta_filtro})"

        kpi_margen_val.value = f"{mg:.1f}%"
        kpi_margen_sub.value = "Margen sobre ventas"

        # 3. Actualizar tabla de ventas del día
        ventas_a_mostrar = data_dia.get("ventas", []) if filtro_origen == "todos" else data_dia.get(filtro_origen, {}).get("ventas", [])
        table_ventas_dia.rows.clear()
        for v in ventas_a_mostrar:
            es_local = v.get("perfil") == "local"
            table_ventas_dia.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"#{v['id']}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                                bgcolor=ft.Colors.INDIGO_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(ft.Text(v["hora"], size=12, weight=ft.FontWeight.W_500)),
                        ft.DataCell(
                            ft.Row([
                                ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, size=15, color=ft.Colors.GREY_600),
                                ft.Text(v["cliente"], size=12, weight=ft.FontWeight.W_500),
                            ], spacing=4)
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(v["perfil"].capitalize(), size=11, color=ft.Colors.INDIGO_900 if es_local else ft.Colors.ORANGE_900, weight=ft.FontWeight.W_600),
                                bgcolor=ft.Colors.INDIGO_50 if es_local else ft.Colors.ORANGE_50,
                                border_radius=4,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(ft.Text(f"${v['total_venta']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900)),
                        ft.DataCell(ft.Text(f"${v['total_costo']:,.2f}", size=12, color=ft.Colors.BLUE_GREY_700)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"${v['utilidad']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800 if v['utilidad'] >= 0 else ft.Colors.RED_800),
                                bgcolor=ft.Colors.GREEN_50 if v['utilidad'] >= 0 else ft.Colors.RED_50,
                                border_radius=6,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            )
                        ),
                        ft.DataCell(
                            ft.Row([
                                ft.Button(
                                    "Detalle",
                                    icon=ft.Icons.VISIBILITY_OUTLINED,
                                    height=32,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_50, color=ft.Colors.TEAL_800, elevation=0, shape=ft.RoundedRectangleBorder(radius=6)),
                                    on_click=lambda ev, item=v: open_sale_detail_modal(item)
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                                    icon_color=ft.Colors.RED_600,
                                    icon_size=18,
                                    tooltip="Anular venta",
                                    on_click=lambda ev, item=v: open_delete_sale_modal(item)
                                ),
                            ], spacing=4)
                        ),
                    ]
                )
            )

        table_ventas_dia.visible = len(ventas_a_mostrar) > 0
        empty_ventas_box.visible = len(ventas_a_mostrar) == 0

        # 4. Actualizar tabla: Últimos días con actividad (la de la imagen)
        perfil_param = None if filtro_origen == "todos" else filtro_origen
        resumen_reciente = db.obtener_resumen_dias_recientes(10, perfil=perfil_param)
        table_resumen_dias.rows.clear()
        for r in resumen_reciente:
            def select_day_fn(ev, f=r["fecha"]):
                inp_fecha_utilidades.value = f
                reload_utilidades()

            es_dia_seleccionado = (r["fecha"] == fecha_act)
            table_resumen_dias.rows.append(
                ft.DataRow(
                    selected=es_dia_seleccionado,
                    cells=[
                        ft.DataCell(ft.Text(r["fecha"], weight=ft.FontWeight.BOLD if es_dia_seleccionado else ft.FontWeight.W_500, size=12)),
                        ft.DataCell(ft.Text(f"{r['cantidad_ventas']} venta(s)", size=12)),
                        ft.DataCell(ft.Text(f"${r['total_ventas']:,.2f}", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"${r['total_costo']:,.2f}", size=12, color=ft.Colors.BLUE_GREY_700)),
                        ft.DataCell(
                            ft.Text(f"${r['total_utilidad']:,.2f}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800 if r['total_utilidad'] >= 0 else ft.Colors.RED_800)
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(f"{r['margen_porcentaje']:.1f}%", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_900),
                                bgcolor=ft.Colors.AMBER_50,
                                border_radius=4,
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(
                            ft.Button(
                                "Ver día",
                                icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                                height=30,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_50, color=ft.Colors.BLUE_700, elevation=0, shape=ft.RoundedRectangleBorder(radius=6)),
                                on_click=select_day_fn,
                            )
                        ),
                    ]
                )
            )

        page.update()

    def cambiar_fecha(dias_offset: int):
        nonlocal fecha_utilidades
        try:
            dt = datetime.strptime(inp_fecha_utilidades.value.strip(), "%Y-%m-%d")
        except Exception:
            dt = datetime.now()
        dt = dt + timedelta(days=dias_offset)
        fecha_utilidades = dt.strftime("%Y-%m-%d")
        inp_fecha_utilidades.value = fecha_utilidades
        reload_utilidades()

    def ir_a_hoy(e):
        nonlocal fecha_utilidades
        fecha_utilidades = datetime.now().strftime("%Y-%m-%d")
        inp_fecha_utilidades.value = fecha_utilidades
        reload_utilidades()

    def ir_a_ayer(e):
        nonlocal fecha_utilidades
        fecha_utilidades = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        inp_fecha_utilidades.value = fecha_utilidades
        reload_utilidades()

    inp_fecha_utilidades.on_submit = lambda e: reload_utilidades()

    utilidades_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Utilidades Diarias", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Métricas de ventas, costos de inventario y ganancia neta por día", color=ft.Colors.BLUE_GREY_700),
                ], spacing=3),
                ft.Row([
                    ft.OutlinedButton("← Anterior", icon=ft.Icons.CHEVRON_LEFT_ROUNDED, on_click=lambda e: cambiar_fecha(-1)),
                    ft.FilledTonalButton("Hoy", icon=ft.Icons.TODAY_ROUNDED, on_click=ir_a_hoy),
                    ft.FilledTonalButton("Ayer", icon=ft.Icons.HISTORY_ROUNDED, on_click=ir_a_ayer),
                    inp_fecha_utilidades,
                    ft.OutlinedButton("Siguiente →", icon=ft.Icons.CHEVRON_RIGHT_ROUNDED, on_click=lambda e: cambiar_fecha(1)),
                    ft.FilledButton("Consultar", icon=ft.Icons.SEARCH_ROUNDED, on_click=lambda e: reload_utilidades()),
                ], spacing=8, alignment=ft.MainAxisAlignment.END),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            # Apartado: Filtro de Visualización de Origen
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.FILTER_LIST_ROUNDED, color=ft.Colors.TEAL_800, size=18),
                        ft.Text("Filtrar origen de ventas:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                    ], spacing=6),
                    ft.Row([
                        btn_filtro_todos,
                        btn_filtro_local,
                        btn_filtro_costa,
                    ], spacing=8),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ),

            # Tarjetas de Métricas Principales (KPIs)
            ft.Row([card_ventas, card_costo, card_utilidad, card_margen], spacing=14),

            # Apartado Individual: Resumen Comparativo de Productos Locales vs Productos Costa
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME_MOSAIC_ROUNDED, color=ft.Colors.TEAL_700, size=18),
                    ft.Text("Desglose Individual de Utilidades por Catálogo", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                ], spacing=6),
                ft.Row([
                    card_desglose_local,
                    card_desglose_costa,
                ], spacing=14),
            ], spacing=8),

            # Desglose de Ventas del Día y Resumen
            ft.Row([
                # Panel izquierdo: Ventas del día
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color=ft.Colors.TEAL_700),
                                ft.Text("Ventas de la fecha seleccionada", size=16, weight=ft.FontWeight.BOLD),
                            ], spacing=8),
                            ft.IconButton(ft.Icons.REFRESH_ROUNDED, icon_size=18, tooltip="Refrescar ventas", on_click=lambda e: reload_utilidades()),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                        ft.Container(
                            content=ft.Column([table_ventas_dia, empty_ventas_box], scroll=ft.ScrollMode.AUTO),
                            height=360,
                        ),
                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=14,
                    expand=3,
                ),

                # Panel derecho: Resumen días recientes (Tabla de la imagen del usuario)
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_MONTH_ROUNDED, color=ft.Colors.TEAL_700),
                            ft.Text("Últimos días con actividad", size=16, weight=ft.FontWeight.BOLD),
                        ], spacing=8),
                        ft.Divider(height=1, color=ft.Colors.BLUE_GREY_100),
                        ft.Container(
                            content=ft.Column([table_resumen_dias], scroll=ft.ScrollMode.AUTO),
                            height=360,
                        ),
                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=14,
                    expand=2,
                ),
            ], spacing=14, expand=True),
        ], spacing=16, expand=True),
        padding=ft.Padding.only(left=28, right=28, top=24, bottom=20),
        expand=True,
        visible=False,
    )

    # -------------------------------------------------------------
    # 8. Navegación y Ensamblado Principal
    # -------------------------------------------------------------
    def select_view(view: str):
        invoice_view.visible = view == "invoice"
        catalog_view.visible = view == "catalog"
        utilidades_view.visible = view == "utilidades"

        invoice_nav.bgcolor = ft.Colors.ORANGE_100 if invoice_view.visible else None
        catalog_nav.bgcolor = ft.Colors.ORANGE_100 if catalog_view.visible else None
        utilidades_nav.bgcolor = ft.Colors.ORANGE_100 if utilidades_view.visible else None

        if view == "utilidades":
            reload_utilidades()
        page.update()

    invoice_nav = ft.Container(content=ft.Row([ft.Icon(ft.Icons.POINT_OF_SALE_ROUNDED, color=ft.Colors.BLUE_GREY_900), ft.Column([ft.Text("Facturación", color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600), ft.Text("Nueva factura", color=ft.Colors.BLUE_GREY_800, size=11)], spacing=1)]), padding=12, border_radius=10, ink=True, on_click=lambda e: select_view("invoice"))
    catalog_nav = ft.Container(content=ft.Row([ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, color=ft.Colors.BLUE_GREY_900), ft.Column([ft.Text("Inventario", color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600), ft.Text("Productos y precios", color=ft.Colors.BLUE_GREY_800, size=11)], spacing=1)]), padding=12, border_radius=10, ink=True, on_click=lambda e: select_view("catalog"))
    utilidades_nav = ft.Container(content=ft.Row([ft.Icon(ft.Icons.ATTACH_MONEY_ROUNDED, color=ft.Colors.BLUE_GREY_900), ft.Column([ft.Text("Utilidades", color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600), ft.Text("Ganancias diarias", color=ft.Colors.BLUE_GREY_800, size=11)], spacing=1)]), padding=12, border_radius=10, ink=True, on_click=lambda e: select_view("utilidades"))

    sidebar = ft.Container(content=ft.Column([
        ft.Row([ft.Container(content=ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color=ft.Colors.WHITE, size=22), padding=8, bgcolor=ft.Colors.BLUE_700, border_radius=10), ft.Text("Dulcería Loaiza", color=ft.Colors.BLUE_GREY_900, size=16, weight=ft.FontWeight.BOLD)], spacing=10),
        ft.Divider(color=ft.Colors.BLUE_GREY_300, height=30),
        ft.Text("MENÚ PRINCIPAL", size=11, color=ft.Colors.BLUE_GREY_800, weight=ft.FontWeight.BOLD),
        invoice_nav, catalog_nav, utilidades_nav,
        ft.Container(content=ft.Column([
            ft.Text("ORIGEN DE PRECIOS", size=10, color=ft.Colors.BLUE_GREY_800, weight=ft.FontWeight.BOLD),
            database_switch,
            costa_manage_switch,
        ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), padding=ft.Padding.only(top=12, bottom=10), border=ft.Border.only(top=ft.BorderSide(1, ft.Colors.BLUE_GREY_300), bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_300))),
        ft.Container(content=ft.Text(""), expand=True),
        ft.Container(content=ft.Column([ft.Text("Conexión activa", size=10, color=ft.Colors.BLUE_GREY_800, weight=ft.FontWeight.BOLD), ft.Row([status_icon, status_text], spacing=8), database_mode_text], spacing=4), padding=10, bgcolor=ft.Colors.BLUE_50, border_radius=8),
        ft.Row([ft.Text("Sincronizar", size=11, color=ft.Colors.BLUE_GREY_800, weight=ft.FontWeight.W_600), ft.IconButton(ft.Icons.SYNC_ROUNDED, icon_color=ft.Colors.BLUE_GREY_900, icon_size=18, tooltip="Comprobar conexión", on_click=lambda e: reload_data(notify_ok=True))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    ], spacing=8), width=300, padding=20, bgcolor=ft.Colors.BLUE_100)

    content_area = ft.Column(
        [banner_xampp, invoice_view, catalog_view, utilidades_view],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    page.add(ft.Row([sidebar, content_area], expand=True, spacing=0))
    render_invoice()
    page.update()
    try:
        reload_data()
        reload_utilidades()
    except Exception as ex:
        update_connection_ui(False)
        notify(f"No se pudo conectar a la base de datos: {ex}", es_error=True)



if __name__ == "__main__":
    ft.run(main)