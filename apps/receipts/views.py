from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum, Q

from .models import Receipt, ExtraIncome
from .forms import ReceiptForm, ReceiptProofForm, ExtraIncomeForm
from .pdf import generate_receipt_pdf, generate_monthly_report_pdf
from apps.core.models import Company
from apps.core.services import get_current_exchange_rate
from apps.clients.models import Client


@login_required
def receipt_list_view(request):
    """Lista de recibos emitidos con filtros por mes, año y cliente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    client_filter = request.GET.get('client', '')
    status_filter = request.GET.get('status', 'all')
    search_q = request.GET.get('q', '').strip()

    receipts_qs = Receipt.objects.filter(company=company).select_related('client', 'created_by')

    if search_q:
        receipts_qs = receipts_qs.filter(
            Q(receipt_number__icontains=search_q) |
            Q(client__name__icontains=search_q) |
            Q(external_client_name__icontains=search_q) |
            Q(concept__icontains=search_q) |
            Q(payment_reference__icontains=search_q)
        )

    if month_filter:
        receipts_qs = receipts_qs.filter(billing_month=int(month_filter))
    if year_filter:
        receipts_qs = receipts_qs.filter(billing_year=int(year_filter))
    if client_filter:
        receipts_qs = receipts_qs.filter(client_id=int(client_filter))
    if status_filter in ['paid', 'cancelled']:
        receipts_qs = receipts_qs.filter(status=status_filter)

    totals = receipts_qs.filter(status='paid').aggregate(
        total_usd=Sum('amount_usd'),
        total_hnl=Sum('amount_hnl')
    )

    clients = company.clients.filter(is_active=True).order_by('name')
    years = list(range(today.year - 4, today.year + 2))

    return render(request, 'receipts/receipt_list.html', {
        'company': company,
        'receipts': receipts_qs,
        'clients': clients,
        'years': years,
        'months': Receipt.MONTH_NAMES.items(),
        'selected_month': int(month_filter) if month_filter else '',
        'selected_year': int(year_filter) if year_filter else '',
        'selected_client': int(client_filter) if client_filter else '',
        'selected_status': status_filter,
        'search_q': search_q,
        'total_usd': totals['total_usd'] or Decimal('0.00'),
        'total_hnl': totals['total_hnl'] or Decimal('0.00'),
    })


@login_required
def receipt_create_view(request):
    """Crea un nuevo recibo con numeración correlativa automática y soporte para pagos en 1 o 2 partes o montos extra."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)
    next_number = company.get_next_receipt_number_formatted()

    client_id_param = request.GET.get('client_id')
    is_extra_param = request.GET.get('extra') == '1'
    preselected_client = None
    client_suggestion = None
    if client_id_param:
        preselected_client = company.clients.filter(id=client_id_param, is_active=True).first()
        if preselected_client:
            client_suggestion = preselected_client.get_next_payment_suggestion(today.year, today.month)

    if request.method == 'POST':
        form = ReceiptForm(request.POST, company=company)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.company = company
            receipt.created_by = request.user
            receipt.save()
            messages.success(request, f"Recibo #{receipt.receipt_number} emitido exitosamente para {receipt.client_display_name}.")
            return redirect('receipt_detail', pk=receipt.pk)
    else:
        initial_data = {
            'exchange_rate': current_rate,
            'issue_date': today,
            'billing_month': today.month,
            'billing_year': today.year,
            'is_extra_charge': is_extra_param,
        }
        if preselected_client and client_suggestion:
            initial_data['client'] = preselected_client
            if not is_extra_param:
                suggested_usd = client_suggestion['suggested_usd']
                part_label = client_suggestion['part_label']
                month_str = f"{Receipt.MONTH_NAMES.get(today.month, '')} {today.year}"
                if preselected_client.payment_parts == 2 or client_suggestion['paid_usd'] > Decimal('0.00'):
                    concept_str = f"{preselected_client.default_concept} ({part_label}) - {month_str}"
                else:
                    concept_str = f"{preselected_client.default_concept} - {month_str}"

                initial_data['amount_usd'] = suggested_usd
                initial_data['concept'] = concept_str
                initial_data['amount_hnl'] = (suggested_usd * current_rate).quantize(Decimal('0.01'))

        form = ReceiptForm(initial=initial_data, company=company)

    return render(request, 'receipts/receipt_form.html', {
        'form': form,
        'company': company,
        'next_number': next_number,
        'current_rate': current_rate,
        'preselected_client': preselected_client,
        'client_suggestion': client_suggestion,
    })


@login_required
def receipt_detail_view(request, pk):
    """Vista detallada de impresión del recibo y control de comprobante."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    receipt = get_object_or_404(Receipt, pk=pk, company=company)

    proof_form = ReceiptProofForm(instance=receipt)

    return render(request, 'receipts/receipt_detail.html', {
        'receipt': receipt,
        'company': company,
        'proof_form': proof_form,
    })


@login_required
def receipt_upload_proof_view(request, pk):
    """Adjunta o actualiza el comprobante de pago de un recibo."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    receipt = get_object_or_404(Receipt, pk=pk, company=company)

    if request.method == 'POST':
        form = ReceiptProofForm(request.POST, request.FILES, instance=receipt)
        if form.is_valid():
            if 'payment_proof' in request.FILES:
                receipt.payment_proof_uploaded_at = timezone.now()
            form.save()
            messages.success(request, f"Comprobante de pago guardado correctamente en el Recibo #{receipt.receipt_number}.")
        else:
            messages.error(request, "No se pudo guardar el comprobante. Verifica el archivo seleccionado.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('receipt_detail', pk=receipt.pk)


@login_required
def receipt_pdf_view(request, pk):
    """Descarga directa del recibo en formato PDF profesional (solo HNL, sin firmas ni método de pago)."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    receipt = get_object_or_404(Receipt, pk=pk, company=company)

    pdf_bytes = generate_receipt_pdf(receipt)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    client_slug = receipt.client_display_name[:20].replace(' ', '_')
    filename = f"Recibo-{receipt.receipt_number}-{client_slug}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def receipt_cancel_view(request, pk):
    """Anula un recibo emitido."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    receipt = get_object_or_404(Receipt, pk=pk, company=company)

    if request.method == 'POST':
        receipt.status = 'cancelled'
        receipt.save()
        messages.warning(request, f"El recibo #{receipt.receipt_number} ha sido ANULADO.")
        return redirect('receipt_list')

    return render(request, 'receipts/receipt_confirm_cancel.html', {
        'receipt': receipt,
        'company': company,
    })


@login_required
def receipt_monthly_pdf_report_view(request):
    """Genera y descarga el reporte mensual de cobros e ingresos extra en PDF."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    paid_receipts = Receipt.objects.filter(
        company=company,
        billing_year=year,
        billing_month=month,
        status='paid'
    ).select_related('client').order_by('sequence_number')

    extra_incomes = ExtraIncome.objects.filter(
        company=company,
        income_date__year=year,
        income_date__month=month
    ).select_related('client').order_by('income_date')

    all_clients = company.clients.filter(is_active=True).order_by('billing_day', 'name')
    pending_clients = []
    for c in all_clients:
        if not c.has_paid_for_period(year, month):
            c.paid_period_usd = c.get_paid_amount_for_period(year, month)
            c.remaining_period_usd = c.get_remaining_balance_for_period(year, month)
            pending_clients.append(c)

    rec_totals = paid_receipts.aggregate(
        total_usd=Sum('amount_usd'),
        total_hnl=Sum('amount_hnl')
    )
    ext_totals = extra_incomes.aggregate(
        total_usd=Sum('amount_usd'),
        total_hnl=Sum('amount_hnl')
    )
    total_usd = (rec_totals['total_usd'] or Decimal('0.00')) + (ext_totals['total_usd'] or Decimal('0.00'))
    total_hnl = (rec_totals['total_hnl'] or Decimal('0.00')) + (ext_totals['total_hnl'] or Decimal('0.00'))

    pdf_bytes = generate_monthly_report_pdf(
        company=company,
        year=year,
        month=month,
        paid_receipts=paid_receipts,
        pending_clients=pending_clients,
        total_usd=total_usd,
        total_hnl=total_hnl,
        extra_incomes=extra_incomes
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    month_name = Receipt.MONTH_NAMES.get(month, str(month))
    filename = f"Reporte-Cobros-{month_name}-{year}-{company.name[:15].replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==============================================================================
# VISTAS DE INGRESOS EXTRA Y DE EMPRESAS EXTERNAS (NO REGISTRADAS)
# ==============================================================================

@login_required
def extra_income_list_view(request):
    """
    Bitácora de ingresos que no van en el cobro mensual:
    - Valores de empresas o clientes externos no registrados (solo como registro de ingreso).
    - Montos extra fuera de la cuota mensual fija para empresas/clientes registrados.
    """
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    source_filter = request.GET.get('source', 'all')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    client_filter = request.GET.get('client', '')
    search_q = request.GET.get('q', '').strip()

    incomes_qs = ExtraIncome.objects.filter(company=company).select_related('client', 'created_by')

    if search_q:
        incomes_qs = incomes_qs.filter(
            Q(external_company_name__icontains=search_q) |
            Q(client__name__icontains=search_q) |
            Q(concept__icontains=search_q) |
            Q(payment_reference__icontains=search_q)
        )

    if source_filter in ['external', 'registered']:
        incomes_qs = incomes_qs.filter(source_type=source_filter)
    if month_filter:
        incomes_qs = incomes_qs.filter(income_date__month=int(month_filter))
    if year_filter:
        incomes_qs = incomes_qs.filter(income_date__year=int(year_filter))
    if client_filter:
        incomes_qs = incomes_qs.filter(client_id=int(client_filter))

    ext_totals = incomes_qs.filter(source_type='external').aggregate(
        usd=Sum('amount_usd'),
        hnl=Sum('amount_hnl')
    )
    reg_totals = incomes_qs.filter(source_type='registered').aggregate(
        usd=Sum('amount_usd'),
        hnl=Sum('amount_hnl')
    )

    ext_usd = ext_totals['usd'] or Decimal('0.00')
    ext_hnl = ext_totals['hnl'] or Decimal('0.00')
    reg_usd = reg_totals['usd'] or Decimal('0.00')
    reg_hnl = reg_totals['hnl'] or Decimal('0.00')

    total_usd = ext_usd + reg_usd
    total_hnl = ext_hnl + reg_hnl

    clients = company.clients.filter(is_active=True).order_by('name')
    years = list(range(today.year - 4, today.year + 2))

    return render(request, 'receipts/extra_income_list.html', {
        'company': company,
        'extra_incomes': incomes_qs,
        'clients': clients,
        'years': years,
        'months': Receipt.MONTH_NAMES.items(),
        'source_filter': source_filter,
        'selected_month': int(month_filter) if month_filter else '',
        'selected_year': int(year_filter) if year_filter else '',
        'selected_client': int(client_filter) if client_filter else '',
        'search_q': search_q,
        'ext_usd': ext_usd,
        'ext_hnl': ext_hnl,
        'reg_usd': reg_usd,
        'reg_hnl': reg_hnl,
        'total_usd': total_usd,
        'total_hnl': total_hnl,
    })


@login_required
def extra_income_create_view(request):
    """Registrar un nuevo ingreso de empresa externa (no registrada) o monto extra de empresa registrada."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)

    client_id_param = request.GET.get('client_id')
    source_param = request.GET.get('source', '')
    preselected_client = None
    if client_id_param:
        preselected_client = company.clients.filter(id=client_id_param, is_active=True).first()

    if request.method == 'POST':
        form = ExtraIncomeForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            extra_inc = form.save(commit=False)
            extra_inc.company = company
            extra_inc.created_by = request.user
            extra_inc.save()
            messages.success(
                request,
                f"Ingreso registrado exitosamente para '{extra_inc.source_display_name}' por L {extra_inc.amount_hnl:,.2f} HNL."
            )
            return redirect('extra_income_list')
    else:
        initial = {
            'income_date': today,
            'exchange_rate': current_rate,
            'currency': 'USD',
            'source_type': 'registered' if (preselected_client or source_param == 'registered') else 'external',
        }
        if preselected_client:
            initial['client'] = preselected_client
        form = ExtraIncomeForm(initial=initial, company=company)

    return render(request, 'receipts/extra_income_form.html', {
        'form': form,
        'company': company,
        'current_rate': current_rate,
        'title': 'Registrar Ingreso Extra o de Empresa Externa',
    })


@login_required
def extra_income_edit_view(request, pk):
    """Editar un registro de ingreso extra o externo."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    extra_inc = get_object_or_404(ExtraIncome, pk=pk, company=company)

    if request.method == 'POST':
        form = ExtraIncomeForm(request.POST, request.FILES, instance=extra_inc, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ingreso de '{extra_inc.source_display_name}' actualizado correctamente.")
            return redirect('extra_income_list')
    else:
        form = ExtraIncomeForm(instance=extra_inc, company=company)

    return render(request, 'receipts/extra_income_form.html', {
        'form': form,
        'company': company,
        'extra_inc': extra_inc,
        'current_rate': extra_inc.exchange_rate,
        'title': f'Editar Ingreso: {extra_inc.source_display_name}',
    })


@login_required
def extra_income_delete_view(request, pk):
    """Eliminar un registro de ingreso extra o externo."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    extra_inc = get_object_or_404(ExtraIncome, pk=pk, company=company)

    if request.method == 'POST':
        name = extra_inc.source_display_name
        extra_inc.delete()
        messages.success(request, f"Registro de ingreso de '{name}' eliminado.")
        return redirect('extra_income_list')

    return render(request, 'receipts/extra_income_confirm_delete.html', {
        'extra_inc': extra_inc,
        'company': company,
    })

