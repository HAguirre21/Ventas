"""
Módulo de generación de facturas en formato PDF utilizando ReportLab.
"""

import os
import webbrowser
from datetime import datetime
from decimal import Decimal
from typing import List, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet


def generar_factura_pdf(productos: List[Any], info_cliente: dict = None) -> tuple[bool, str]:
    """
    Genera un archivo PDF con la factura comercial a partir de la lista de productos.
    Abre automáticamente el archivo generado y retorna (éxito, ruta_o_mensaje).
    """
    if not productos:
        return False, "No hay productos en la factura para generar el PDF."

    try:
        # Definir la ruta base del proyecto y carpeta facturas
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_guardado = os.path.join(ruta_base, "facturas")

        if not os.path.exists(ruta_guardado):
            os.makedirs(ruta_guardado, exist_ok=True)

        fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archivo = os.path.join(ruta_guardado, f"factura_{fecha_hora}.pdf")

        estilos = getSampleStyleSheet()
        doc = BaseDocTemplate(archivo, pagesize=letter)

        margen_superior = 25
        margen_inferior = 80
        ancho, alto = letter

        frame_contenido = Frame(
            x1=50,
            y1=margen_inferior + 20,
            width=ancho - 100,
            height=alto - margen_superior - margen_inferior,
            id="contenido",
        )

        def template(canvas, doc_obj):
            canvas.saveState()
            y_centro = (alto + margen_inferior + margen_superior) / 2
            total = sum(p.monto for p in productos)
            firma_y_total = [
                [
                    Paragraph("Firma: ___________________________", estilos["Normal"]),
                    Paragraph(f"Total a Pagar: ${total:,.2f}", estilos["Heading4"]),
                ]
            ]
            tabla_firma_total = Table(firma_y_total, colWidths=[400, 150])
            tabla_firma_total.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ]
                )
            )
            tabla_firma_total.wrapOn(canvas, 400, 50)
            tabla_firma_total.drawOn(canvas, 50, y_centro - 30)
            canvas.restoreState()

        doc.addPageTemplates([PageTemplate(id="principal", frames=frame_contenido, onPage=template)])

        elementos = []

        # Logos
        logo_izquierdo = os.path.join(ruta_base, "imagenes", "logo.png")
        logos_derecha = [
            os.path.join(ruta_base, "imagenes", "colombina.png"),
            os.path.join(ruta_base, "imagenes", "amer.png"),
            os.path.join(ruta_base, "imagenes", "mas.png"),
            os.path.join(ruta_base, "imagenes", "postobon.png"),
        ]

        if os.path.exists(logo_izquierdo):
            logo_left = Image(logo_izquierdo)
            logo_left.drawHeight = 100
            logo_left.drawWidth = 130
        else:
            logo_left = ""

        logo_data_derecha = []
        for logo_path in logos_derecha:
            if os.path.exists(logo_path):
                logo = Image(logo_path)
                logo.drawHeight = 40
                logo.drawWidth = 70
                logo_data_derecha.append(logo)

        if not logo_data_derecha:
            tabla_derecha = ""
        else:
            tabla_derecha = Table([logo_data_derecha])
            tabla_derecha.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )

        encabezado = Table(
            [[logo_left, "", tabla_derecha]],
            colWidths=[70, 150, 300],
        )
        encabezado.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ]
            )
        )
        elementos.append(encabezado)
        elementos.append(Spacer(1, 7))

        # Título
        titulo = Paragraph("DULCERIA <b>LOAIZA</b>", estilos["Title"])
        elementos.append(titulo)
        elementos.append(Spacer(1, 2))

        fecha_actual = datetime.now().strftime("%Y-%m-%d")

        # Recuadro de información
        data_recuadro = [
            [
                Paragraph(
                    "Empresa: Dulceria Loaiza<br/>Dirección: Carrera 66 1b<br/>Numero de la Empresa: 3014653717",
                    estilos["Normal"],
                ),
                Paragraph(
                    f"Cliente: {info_cliente.get('nombre', 'Cliente') if info_cliente else 'Cliente'}",
                    estilos["Normal"],
                ),
                Paragraph(
                    f"Fecha: {fecha_actual}<br/>Vendedor: Jhoan Hernandes<br/>Numero: 3014653717 ",
                    estilos["Normal"],
                ),
            ]
        ]
        tabla_recuadro = Table(data_recuadro, colWidths=[210, 200, 170])
        tabla_recuadro.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elementos.append(tabla_recuadro)
        elementos.append(Spacer(1, 7))

        # Tabla con los productos
        data = [["No.", "Producto", "Precio Unitario", "Cantidad", "Total"]] + [
            [index + 1, p.concepto, f"${p.precio_unitario:,.2f}", p.cantidad, f"${p.monto:,.2f}"]
            for index, p in enumerate(productos)
        ]

        col_widths = [50, 230, 100, 100, 100]

        tabla_productos = Table(data, colWidths=col_widths)
        tabla_productos.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elementos.append(tabla_productos)
        elementos.append(Spacer(1, 7))

        # Construir PDF
        doc.build(elementos)

        try:
            webbrowser.open(f"file://{archivo}")
        except Exception:
            pass

        return True, archivo

    except Exception as e:
        print(f"[PDF Error] Error al generar PDF: {e}")
        return False, str(e)
