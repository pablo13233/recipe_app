import io
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_financial_report_pdf(company, year, month_name, income_items, expense_company_items, expense_personal_items, totals, extra_income_items=None):
    """
    Genera un informe financiero en PDF comparando:
    Ingresos recibidos (Recibos + Ingresos Extra/Externos) vs Gastos de Empresa vs Gastos Personales.
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
    border_color = colors.HexColor("#cbd5e1")
    income_color = colors.HexColor("#16a34a")
    extra_color = colors.HexColor("#0f766e")
    expense_color = colors.HexColor("#dc2626")
    personal_color = colors.HexColor("#d97706")

    story = []

    # Título
    title_p = Paragraph(
        f"<b>{company.name}</b><br/><font size='12' color='#1e3a8a'>Estado de Ingresos vs Gastos ({month_name} {year})</font>",
        ParagraphStyle('FinTitle', fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=TA_CENTER)
    )
    story.append(title_p)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=8, spaceAfter=14))

    # Tarjetas de Resumen
    summary_data = [
        [
            Paragraph("TOTAL INGRESOS", ParagraphStyle('SH1', fontName='Helvetica-Bold', fontSize=9, textColor=income_color, alignment=TA_CENTER)),
            Paragraph("GASTOS EMPRESA", ParagraphStyle('SH2', fontName='Helvetica-Bold', fontSize=9, textColor=expense_color, alignment=TA_CENTER)),
            Paragraph("GASTOS PERSONALES", ParagraphStyle('SH3', fontName='Helvetica-Bold', fontSize=9, textColor=personal_color, alignment=TA_CENTER)),
            Paragraph("BALANCE OPERATIVO", ParagraphStyle('SH4', fontName='Helvetica-Bold', fontSize=9, textColor=primary_color, alignment=TA_CENTER)),
            Paragraph("BALANCE NETO FINAL", ParagraphStyle('SH5', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#111827"), alignment=TA_CENTER)),
        ],
        [
            Paragraph(f"<b>L {totals['income_hnl']:,.2f}</b><br/><font size='8'>(${totals['income_usd']:,.2f})</font>", ParagraphStyle('SV1', alignment=TA_CENTER)),
            Paragraph(f"<b>L {totals['exp_comp_hnl']:,.2f}</b><br/><font size='8'>(${totals['exp_comp_usd']:,.2f})</font>", ParagraphStyle('SV2', alignment=TA_CENTER)),
            Paragraph(f"<b>L {totals['exp_pers_hnl']:,.2f}</b><br/><font size='8'>(${totals['exp_pers_usd']:,.2f})</font>", ParagraphStyle('SV3', alignment=TA_CENTER)),
            Paragraph(f"<b>L {totals['op_balance_hnl']:,.2f}</b><br/><font size='8'>(${totals['op_balance_usd']:,.2f})</font>", ParagraphStyle('SV4', alignment=TA_CENTER)),
            Paragraph(f"<b>L {totals['net_balance_hnl']:,.2f}</b><br/><font size='8'>(${totals['net_balance_usd']:,.2f})</font>", ParagraphStyle('SV5', alignment=TA_CENTER)),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[108, 108, 108, 108, 108])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # 1. Ingresos por Recibos
    rec_hnl = totals.get('rec_hnl', totals['income_hnl'])
    story.append(Paragraph(f"<b>1. Ingresos por Recibos Emitidos (Total: L {rec_hnl:,.2f})</b>", ParagraphStyle('H_Inc', fontName='Helvetica-Bold', fontSize=11, textColor=income_color)))
    story.append(Spacer(1, 4))
    if income_items:
        inc_data = [
            [
                Paragraph("Fecha", ParagraphStyle('TH_I1', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Recibo", ParagraphStyle('TH_I2', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Cliente", ParagraphStyle('TH_I3', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Concepto", ParagraphStyle('TH_I4', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("USD", ParagraphStyle('TH_I5', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
                Paragraph("Total HNL", ParagraphStyle('TH_I6', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
            ]
        ]
        for inc in income_items:
            inc_data.append([
                Paragraph(inc.issue_date.strftime('%d/%m/%Y'), styles['Normal']),
                Paragraph(f"#{inc.receipt_number}", styles['Normal']),
                Paragraph(inc.client_display_name, styles['Normal']),
                Paragraph(inc.concept, styles['Normal']),
                Paragraph(f"${inc.amount_usd:,.2f}", ParagraphStyle('R1', alignment=TA_RIGHT)),
                Paragraph(f"L {inc.amount_hnl:,.2f}", ParagraphStyle('R2', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ])
        t_inc = Table(inc_data, colWidths=[65, 55, 140, 140, 65, 75])
        t_inc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), income_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_inc)
    else:
        story.append(Paragraph("<i>Sin recibos emitidos en este periodo.</i>", styles['Normal']))

    story.append(Spacer(1, 12))

    # 1.B Ingresos Extra y de Empresas Externas
    if extra_income_items is not None:
        ext_hnl = totals.get('ext_hnl', Decimal('0.00'))
        story.append(Paragraph(f"<b>2. Ingresos Extra y de Empresas Externas (Total: L {ext_hnl:,.2f})</b>", ParagraphStyle('H_Ext', fontName='Helvetica-Bold', fontSize=11, textColor=extra_color)))
        story.append(Spacer(1, 4))
        if extra_income_items:
            ext_data = [
                [
                    Paragraph("Fecha", ParagraphStyle('TH_E1', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                    Paragraph("Empresa / Cliente", ParagraphStyle('TH_E2', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                    Paragraph("Origen", ParagraphStyle('TH_E3', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                    Paragraph("Concepto", ParagraphStyle('TH_E4', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                    Paragraph("USD", ParagraphStyle('TH_E5', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
                    Paragraph("Total HNL", ParagraphStyle('TH_E6', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
                ]
            ]
            for ext in extra_income_items:
                origen_str = "Monto Extra" if ext.source_type == 'registered' else "Externa"
                ext_data.append([
                    Paragraph(ext.income_date.strftime('%d/%m/%Y'), styles['Normal']),
                    Paragraph(ext.source_display_name, styles['Normal']),
                    Paragraph(origen_str, styles['Normal']),
                    Paragraph(ext.concept, styles['Normal']),
                    Paragraph(f"${ext.amount_usd:,.2f}", ParagraphStyle('RE1', alignment=TA_RIGHT)),
                    Paragraph(f"L {ext.amount_hnl:,.2f}", ParagraphStyle('RE2', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
                ])
            t_ext = Table(ext_data, colWidths=[65, 130, 75, 130, 65, 75])
            t_ext.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), extra_color),
                ('GRID', (0, 0), (-1, -1), 0.5, border_color),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t_ext)
        else:
            story.append(Paragraph("<i>Sin ingresos extra ni de empresas externas en este periodo.</i>", styles['Normal']))
        story.append(Spacer(1, 12))

    # 3. Gastos de Empresa
    story.append(Paragraph(f"<b>3. Gastos Operativos de la Empresa (Total: L {totals['exp_comp_hnl']:,.2f})</b>", ParagraphStyle('H_Exp', fontName='Helvetica-Bold', fontSize=11, textColor=expense_color)))
    story.append(Spacer(1, 4))
    if expense_company_items:
        exp_c_data = [
            [
                Paragraph("Fecha", ParagraphStyle('TH_C1', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Categoría", ParagraphStyle('TH_C2', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Concepto", ParagraphStyle('TH_C3', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Beneficiario", ParagraphStyle('TH_C4', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("USD", ParagraphStyle('TH_C5', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
                Paragraph("Total HNL", ParagraphStyle('TH_C6', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
            ]
        ]
        for exp in expense_company_items:
            exp_c_data.append([
                Paragraph(exp.expense_date.strftime('%d/%m/%Y'), styles['Normal']),
                Paragraph(exp.get_category_display()[:22], styles['Normal']),
                Paragraph(exp.title, styles['Normal']),
                Paragraph(exp.beneficiary or "-", styles['Normal']),
                Paragraph(f"${exp.amount_usd:,.2f}", ParagraphStyle('R3', alignment=TA_RIGHT)),
                Paragraph(f"L {exp.amount_hnl:,.2f}", ParagraphStyle('R4', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ])
        t_exp_c = Table(exp_c_data, colWidths=[65, 110, 145, 80, 65, 75])
        t_exp_c.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), expense_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_exp_c)
    else:
        story.append(Paragraph("<i>Sin gastos de empresa registrados en este periodo.</i>", styles['Normal']))

    story.append(Spacer(1, 12))

    # 4. Gastos Personales
    story.append(Paragraph(f"<b>4. Bitácora de Gastos Personales / Retiros (Total: L {totals['exp_pers_hnl']:,.2f})</b>", ParagraphStyle('H_Pers', fontName='Helvetica-Bold', fontSize=11, textColor=personal_color)))
    story.append(Spacer(1, 4))
    if expense_personal_items:
        exp_p_data = [
            [
                Paragraph("Fecha", ParagraphStyle('TH_P1', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Concepto", ParagraphStyle('TH_P2', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("Beneficiario / Detalle", ParagraphStyle('TH_P3', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)),
                Paragraph("USD", ParagraphStyle('TH_P4', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
                Paragraph("Total HNL", ParagraphStyle('TH_P5', fontName='Helvetica-Bold', textColor=colors.white, fontSize=9, alignment=TA_RIGHT)),
            ]
        ]
        for exp in expense_personal_items:
            exp_p_data.append([
                Paragraph(exp.expense_date.strftime('%d/%m/%Y'), styles['Normal']),
                Paragraph(exp.title, styles['Normal']),
                Paragraph(exp.beneficiary or exp.description or "-", styles['Normal']),
                Paragraph(f"${exp.amount_usd:,.2f}", ParagraphStyle('R5', alignment=TA_RIGHT)),
                Paragraph(f"L {exp.amount_hnl:,.2f}", ParagraphStyle('R6', fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ])
        t_exp_p = Table(exp_p_data, colWidths=[70, 160, 170, 65, 75])
        t_exp_p.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), personal_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_exp_p)
    else:
        story.append(Paragraph("<i>Sin gastos personales registrados en este periodo.</i>", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
