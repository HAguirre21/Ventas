"""
Sistema de Facturación Electrónica - Dulcería R & V
Interfaz gráfica desarrollada con Flet (Material Design 3).
- Persistencia y operaciones CRUD: db.py
- Generación de reportes PDF: pdf_generator.py
"""

import flet as ft
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
    page.window.width = 1100
    page.window.height = 800
    page.window.min_width = 850
    page.window.min_height = 650
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
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK12),
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
            matches = [p["concepto"] for p in catalogo if q in p["concepto"].lower()][:6]
            for m in matches:
                suggestions_col.controls.append(
                    ft.Container(
                        content=ft.Row([ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT_ROUNDED, size=16, color=ft.Colors.PRIMARY), ft.Text(m, size=13, weight=ft.FontWeight.W_500)], spacing=8),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border_radius=6,
                        ink=True,
                        on_click=lambda ev, name=m: select_suggestion(name),
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
                notify(f"Factura generada exitosamente: {res}")
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
        column_spacing=80,
        expand=True,
        columns=[
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Nombre del Producto", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Precio Unitario", weight=ft.FontWeight.BOLD, size=13), numeric=True),
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
        price_field = ft.TextField(label="Precio Unitario ($)", border_radius=8, prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)

        def save_new(ev, dlg):
            nom, pr_str = name_field.value.strip(), price_field.value.strip()
            if not nom or not pr_str:
                notify("Completa todos los campos.", es_advertencia=True)
                return
            try:
                pr = Decimal(pr_str)
                if pr <= 0:
                    notify("El precio debe ser positivo.", es_error=True)
                    return
            except Exception:
                notify("Precio inválido.", es_error=True)
                return
            ok, msj, new_id = db.agregar_producto(nom, pr)
            if ok:
                close_dialog(dlg)
                reload_data()
                notify(f"Producto '{nom}' creado en la Base de Datos (ID #{new_id}).")
            else:
                notify(msj, es_error=True)

        dlg_create = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.ADD_BOX_ROUNDED, color=ft.Colors.PRIMARY), ft.Text("Nuevo Producto", weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Container(content=ft.Column([name_field, price_field], spacing=10, tight=True), width=400),
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
        price_field = ft.TextField(label="Precio Unitario ($)", value=f"{prod['precio']:.2f}", border_radius=8, prefix_icon=ft.Icons.ATTACH_MONEY_ROUNDED, keyboard_type=ft.KeyboardType.NUMBER)

        def save_edit(ev, dlg):
            nom, pr_str = name_field.value.strip(), price_field.value.strip()
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
            ok, msj = db.actualizar_producto(prod["id"], nom, pr)
            if ok:
                close_dialog(dlg)
                reload_data()
                notify(f"Producto #{prod['id']} actualizado en la Base de Datos.")
            else:
                notify(msj, es_error=True)

        dlg_edit = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.EDIT_ROUNDED, color=ft.Colors.PRIMARY), ft.Text(f"Editar Producto #{prod['id']}", weight=ft.FontWeight.BOLD)], spacing=8),
            content=ft.Container(content=ft.Column([name_field, price_field], spacing=10, tight=True), width=400),
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
                                content=ft.Text(f"${p['precio']:,.2f}", weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.GREEN_800),
                                bgcolor=ft.Colors.GREEN_50,
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
                ft.Column([ft.Text("Nueva factura", size=28, weight=ft.FontWeight.BOLD), ft.Text("Crea el comprobante de venta en pocos pasos", color=ft.Colors.BLUE_GREY_700)], spacing=3),
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

    database_switch = ft.Switch(label="Ventas de la costa", value=False, label_text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900, size=13), on_change=change_database)
    costa_manage_switch = ft.Switch(label="Permitir gestionar productos", value=True, label_text_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_900, size=13), on_change=change_costa_permissions)

    def select_view(view: str):
        invoice_view.visible = view == "invoice"
        catalog_view.visible = view == "catalog"
        invoice_nav.bgcolor = ft.Colors.ORANGE_100 if invoice_view.visible else None
        catalog_nav.bgcolor = ft.Colors.ORANGE_100 if catalog_view.visible else None
        page.update()

    invoice_nav = ft.Container(content=ft.Row([ft.Icon(ft.Icons.POINT_OF_SALE_ROUNDED, color=ft.Colors.BLUE_GREY_900), ft.Column([ft.Text("Facturación", color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600), ft.Text("Nueva factura", color=ft.Colors.BLUE_GREY_800, size=11)], spacing=1)]), padding=12, border_radius=10, ink=True, on_click=lambda e: select_view("invoice"))
    catalog_nav = ft.Container(content=ft.Row([ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, color=ft.Colors.BLUE_GREY_900), ft.Column([ft.Text("Inventario", color=ft.Colors.BLUE_GREY_900, weight=ft.FontWeight.W_600), ft.Text("Productos y precios", color=ft.Colors.BLUE_GREY_800, size=11)], spacing=1)]), padding=12, border_radius=10, ink=True, on_click=lambda e: select_view("catalog"))
    sidebar = ft.Container(content=ft.Column([
        ft.Row([ft.Container(content=ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color=ft.Colors.WHITE, size=22), padding=8, bgcolor=ft.Colors.BLUE_700, border_radius=10), ft.Text("Dulcería Loaiza", color=ft.Colors.BLUE_GREY_900, size=16, weight=ft.FontWeight.BOLD)], spacing=10),
        ft.Divider(color=ft.Colors.BLUE_GREY_300, height=30),
        ft.Text("MENÚ PRINCIPAL", size=11, color=ft.Colors.BLUE_GREY_800, weight=ft.FontWeight.BOLD),
        invoice_nav, catalog_nav,
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
        [banner_xampp, invoice_view, catalog_view],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    page.add(ft.Row([sidebar, content_area], expand=True, spacing=0))
    reload_data()
    render_invoice()


if __name__ == "__main__":
    ft.run(main)