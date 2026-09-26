import io
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_receipt_pdf(receipt):
    """
    Genera un PDF profesional para el recibo especificado:
    - Solo muestra el Total en Lempiras (L HNL).
    - No muestra DNI/RTN comercial.
    - No muestra Método de Pago ni Firmas (ya que se emite antes del pago).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#1e3a8a")
    neutral_dark = colors.HexColor("#1f2937")
    neutral_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")

    company_sub = ParagraphStyle(
        'CompSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#4b5563")
    )

    receipt_tag_style = ParagraphStyle(
        'ReceiptTag',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#b91c1c"),
        alignment=TA_RIGHT
    )

    date_style = ParagraphStyle(
        'ReceiptDate',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=neutral_dark,
        alignment=TA_RIGHT
    )

    label_style = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b")
    )

    val_style = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=neutral_dark
    )

    th_left = ParagraphStyle(
        'THLeft',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=TA_LEFT
    )

    th_right = ParagraphStyle(
        'THRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=TA_RIGHT
    )

    story = []

    # 1. ENCABEZADO: Empresa vs Número de Recibo (Sin RTN)
    comp = receipt.company
    comp_info = [
        f"<b><font size='13' color='#1e3a8a'>{comp.name}</font></b>",
        f"{comp.legal_name}" if comp.legal_name else "",
        f"Dirección: {comp.address}" if comp.address else "",
        f"Tel: {comp.phone}" + (f" | Correo: {comp.email}" if comp.email else "") if (comp.phone or comp.email) else "",
    ]
    comp_html = "<br/>".join([line for line in comp_info if line])

    header_left = Paragraph(comp_html, company_sub)
    
    receipt_header_right = [
        Paragraph("RECIBO DE PAGO", ParagraphStyle('RHead', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=primary_color, alignment=TA_RIGHT)),
        Paragraph(f"N° {receipt.receipt_number}", receipt_tag_style),
        Spacer(1, 4),
        Paragraph(f"<b>Fecha de Emisión:</b> {receipt.issue_date.strftime('%d/%m/%Y')}", date_style),
        Paragraph(f"<b>Periodo:</b> {receipt.period_display}", date_style),
    ]

    header_table = Table(
        [[header_left, receipt_header_right]],
        colWidths=[330, 210]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=4, spaceAfter=14))

    # 2. DATOS DEL CLIENTE (Sin DNI ni RTN)
    client = receipt.client
    client_name = receipt.client_display_name
    client_phone = (client.phone if client and client.phone else "-")
    client_address = (client.address if client and client.address else "No especificada")

    client_box_data = [
        [
            Paragraph("CLIENTE:", label_style),
            Paragraph("TELÉFONO / CONTACTO:", label_style),
        ],
        [
            Paragraph(f"<b>{client_name}</b>", val_style),
            Paragraph(client_phone, val_style),
        ],
        [
            Paragraph("DIRECCIÓN:", label_style),
            Paragraph("", label_style),
        ],
        [
            Paragraph(client_address, val_style),
            Paragraph("", val_style),
        ]
    ]
    client_table = Table(client_box_data, colWidths=[360, 180])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), neutral_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('SPAN', (0, 2), (1, 2)),
        ('SPAN', (0, 3), (1, 3)),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 14))

    # 3. TABLA DE DETALLE / CONCEPTO Y TOTAL EN HNL (Solo HNL)
    table_data = [
        [
            Paragraph("CONCEPTO / DESCRIPCIÓN", th_left),
            Paragraph("TOTAL (L HNL)", th_right),
        ],
        [
            Paragraph(f"<b>{receipt.concept}</b><br/><font color='#64748b' size='8'>Periodo correspondiente: {receipt.period_display}</font>", val_style),
            Paragraph(f"<b>L {receipt.amount_hnl:,.2f} HNL</b>", ParagraphStyle('P_HNL', fontName='Helvetica-Bold', fontSize=12, textColor=primary_color, alignment=TA_RIGHT)),
        ]
    ]

    detail_table = Table(table_data, colWidths=[390, 150])
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 10))

    # 4. TOTAL EN LEMPIRAS Y OBSERVACIONES (Sin método de pago ni firmas)
    notes_text = f"<b>OBSERVACIONES:</b><br/>{receipt.notes}" if receipt.notes else ""
    totales_data = [
        [
            Paragraph(notes_text, val_style),
            Paragraph("TOTAL EN LEMPIRAS:", ParagraphStyle('TL', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT)),
            Paragraph(f"<b>L {receipt.amount_hnl:,.2f} HNL</b>", ParagraphStyle('TR', fontName='Helvetica-Bold', fontSize=13, textColor=primary_color, alignment=TA_RIGHT))
        ]
    ]
    totales_table = Table(totales_data, colWidths=[290, 120, 130])
    totales_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (2, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (1, 0), (2, 0), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(totales_table)
    story.append(Spacer(1, 16))

    # 5. NOTA AL PIE (Opcional)
    if comp.receipt_footer_note:
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER
        )
        story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=4, spaceAfter=6))
        story.append(Paragraph(comp.receipt_footer_note, footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_monthly_report_pdf(company, year, month, paid_receipts, pending_clients, total_usd, total_hnl, extra_incomes=None):
    """Genera un PDF con el reporte mensual de recibos pagados, clientes pendientes e ingresos extra/externos."""
    from apps.receipts.models import Receipt
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1e3a8a")
    border_color = colors.HexColor("#cbd5e1")
    month_name = Receipt.MONTH_NAMES.get(int(month), str(month))

    story = []

    title_p = Paragraph(
        f"<b>{company.name}</b><br/><font size='12' color='#1e3a8a'>Reporte de Cobros e Ingresos Mensuales: {month_name} {year}</font>",
        ParagraphStyle('RTitle', fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=TA_CENTER)
    )
    story.append(title_p)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=8, spaceAfter=14))

    # Resumen
    summary_data = [
        [
            Paragraph(f"<b>Recibos Emitidos:</b> {len(paid_receipts)}", styles['Normal']),
            Paragraph(f"<b>Con Saldo Pendiente:</b> {len(pending_clients)}", styles['Normal']),
            Paragraph(f"<b>Total Recaudado ($):</b> ${total_usd:,.2f} USD", ParagraphStyle('USD_T', fontName='Helvetica-Bold', textColor=primary_color)),
            Paragraph(f"<b>Total Recaudado (L):</b> L {total_hnl:,.2f} HNL", ParagraphStyle('HNL_T', fontName='Helvetica-Bold', textColor=primary_color)),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 140, 140])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Sección 1: Pagos recibidos por recibo
    story.append(Paragraph(f"<b>1. Recibos Emitidos en {month_name} {year} ({len(paid_receipts)})</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=11, textColor=primary_color)))
    story.append(Spacer(1, 6))

    if paid_receipts:
        paid_table_data = [
            [
                Paragraph("N° Recibo", ParagraphStyle('TH1', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                Paragraph("Cliente / Concepto", ParagraphStyle('TH2', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                Paragraph("Fecha", ParagraphStyle('TH3', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                Paragraph("Monto USD", ParagraphStyle('TH4', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
                Paragraph("Monto HNL", ParagraphStyle('TH6', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
            ]
        ]
        for r in paid_receipts:
            extra_tag = " <i>(Monto Extra)</i>" if r.is_extra_charge else ""
            paid_table_data.append([
                Paragraph(f"#{r.receipt_number}", styles['Normal']),
                Paragraph(f"<b>{r.client_display_name}</b>{extra_tag}<br/><font size='8' color='#64748b'>{r.concept}</font>", styles['Normal']),
                Paragraph(r.issue_date.strftime('%d/%m/%Y'), styles['Normal']),
                Paragraph(f"${r.amount_usd:,.2f}", ParagraphStyle('R_USD', alignment=TA_RIGHT)),
                Paragraph(f"L {r.amount_hnl:,.2f}", ParagraphStyle('R_HNL', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ])
        p_table = Table(paid_table_data, colWidths=[65, 235, 70, 80, 90])
        p_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(p_table)
    else:
        story.append(Paragraph("<i>No se han emitido recibos para este mes todavía.</i>", styles['Normal']))

    story.append(Spacer(1, 14))

    # Sección 2: Ingresos Extra y de Empresas Externas
    if extra_incomes is not None:
        story.append(Paragraph(f"<b>2. Ingresos Extra y de Empresas Externas ({len(extra_incomes)})</b>", ParagraphStyle('H2_Ext', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f766e"))))
        story.append(Spacer(1, 6))
        if extra_incomes:
            ext_table_data = [
                [
                    Paragraph("Fecha", ParagraphStyle('ETH1', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                    Paragraph("Empresa / Cliente", ParagraphStyle('ETH2', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                    Paragraph("Tipo", ParagraphStyle('ETH3', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                    Paragraph("Concepto", ParagraphStyle('ETH4', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                    Paragraph("Monto HNL", ParagraphStyle('ETH5', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
                ]
            ]
            for ext in extra_incomes:
                tipo_lbl = "Monto Extra" if ext.source_type == 'registered' else "Externa"
                ext_table_data.append([
                    Paragraph(ext.income_date.strftime('%d/%m/%Y'), styles['Normal']),
                    Paragraph(f"<b>{ext.source_display_name}</b>", styles['Normal']),
                    Paragraph(tipo_lbl, styles['Normal']),
                    Paragraph(ext.concept, styles['Normal']),
                    Paragraph(f"L {ext.amount_hnl:,.2f}", ParagraphStyle('E_HNL', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
                ])
            e_table = Table(ext_table_data, colWidths=[65, 145, 80, 160, 90])
            e_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(e_table)
        else:
            story.append(Paragraph("<i>Sin ingresos extra ni externos registrados en este mes.</i>", styles['Normal']))
        story.append(Spacer(1, 14))

    # Sección 3: Clientes pendientes o con saldo parcial
    story.append(Paragraph(f"<b>3. Clientes con Pago o Saldo Mensual Pendiente en {month_name} {year} ({len(pending_clients)})</b>", ParagraphStyle('H2_2', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#dc2626"))))
    story.append(Spacer(1, 6))

    if pending_clients:
        pending_table_data = [
            [
                Paragraph("Cliente", ParagraphStyle('PTH1', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)),
                Paragraph("Fechas Cobro", ParagraphStyle('PTH2', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_CENTER)),
                Paragraph("Cuota Mes", ParagraphStyle('PTH3', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
                Paragraph("Abonado", ParagraphStyle('PTH4', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
                Paragraph("Saldo Pendiente", ParagraphStyle('PTH5', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
            ]
        ]
        for c in pending_clients:
            paid_u = getattr(c, 'paid_period_usd', c.get_paid_amount_for_period(year, month))
            rem_u = getattr(c, 'remaining_period_usd', c.get_remaining_balance_for_period(year, month))
            days_str = f"Día {c.billing_day} y {c.second_billing_day}" if c.payment_parts == 2 else f"Día {c.billing_day}"
            pending_table_data.append([
                Paragraph(c.name, styles['Normal']),
                Paragraph(days_str, ParagraphStyle('P_DAY', alignment=TA_CENTER)),
                Paragraph(f"${c.monthly_fee_usd:,.2f}", ParagraphStyle('P_U', alignment=TA_RIGHT)),
                Paragraph(f"${paid_u:,.2f}", ParagraphStyle('P_PD', alignment=TA_RIGHT)),
                Paragraph(f"<b>${rem_u:,.2f} USD</b>", ParagraphStyle('P_H', alignment=TA_RIGHT, textColor=colors.HexColor("#dc2626"))),
            ])
        pen_table = Table(pending_table_data, colWidths=[190, 95, 85, 80, 90])
        pen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dc2626")),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(pen_table)
    else:
        story.append(Paragraph("<i>¡Excelente! Todos los clientes han cancelado el 100% de su cuota para este periodo.</i>", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

