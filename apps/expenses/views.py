from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum, Q

from .models import Expense, RecurringPayment
from .forms import ExpenseForm, RecurringPaymentForm
from .pdf import generate_financial_report_pdf
from apps.core.models import Company
from apps.core.services import get_current_exchange_rate, get_month_financial_summary
from apps.receipts.models import Receipt, ExtraIncome


@login_required
def expense_list_view(request):
    """Bitácora de gastos personales y de empresa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    type_filter = request.GET.get('type', 'all')
    category_filter = request.GET.get('category', '')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    search_q = request.GET.get('q', '').strip()

    expenses_qs = Expense.objects.filter(company=company).select_related('created_by', 'recurring_payment')

    if search_q:
        expenses_qs = expenses_qs.filter(
            Q(title__icontains=search_q) |
            Q(beneficiary__icontains=search_q) |
            Q(description__icontains=search_q)
        )

    if type_filter in ['company', 'personal']:
        expenses_qs = expenses_qs.filter(expense_type=type_filter)
    if category_filter:
        expenses_qs = expenses_qs.filter(category=category_filter)
    if month_filter:
        expenses_qs = expenses_qs.filter(expense_date__month=int(month_filter))
    if year_filter:
        expenses_qs = expenses_qs.filter(expense_date__year=int(year_filter))

    # Totales
    comp_totals = expenses_qs.filter(expense_type='company').aggregate(
        usd=Sum('amount_usd'),
        hnl=Sum('amount_hnl')
    )
    pers_totals = expenses_qs.filter(expense_type='personal').aggregate(
        usd=Sum('amount_usd'),
        hnl=Sum('amount_hnl')
    )

    exp_comp_usd = comp_totals['usd'] or Decimal('0.00')
    exp_comp_hnl = comp_totals['hnl'] or Decimal('0.00')
    exp_pers_usd = pers_totals['usd'] or Decimal('0.00')
    exp_pers_hnl = pers_totals['hnl'] or Decimal('0.00')

    total_usd = exp_comp_usd + exp_pers_usd
    total_hnl = exp_comp_hnl + exp_pers_hnl

    years = list(range(today.year - 4, today.year + 2))

    return render(request, 'expenses/expense_list.html', {
        'company': company,
        'expenses': expenses_qs,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'selected_month': int(month_filter) if month_filter else '',
        'selected_year': int(year_filter) if year_filter else '',
        'search_q': search_q,
        'categories': Expense.CATEGORY_CHOICES,
        'months': Receipt.MONTH_NAMES.items(),
        'years': years,
        'exp_comp_usd': exp_comp_usd,
        'exp_comp_hnl': exp_comp_hnl,
        'exp_pers_usd': exp_pers_usd,
        'exp_pers_hnl': exp_pers_hnl,
        'total_usd': total_usd,
        'total_hnl': total_hnl,
    })


@login_required
def expense_create_view(request):
    """Registrar un gasto en la bitácora (opcionalmente derivado de un pago recurrente)."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)
    recurring_id = request.GET.get('recurring_id')
    recurring_obj = None
    if recurring_id:
        recurring_obj = RecurringPayment.objects.filter(id=recurring_id, company=company).first()

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.company = company
            expense.created_by = request.user
            expense.save()
            messages.success(request, f"Gasto '{expense.title}' registrado exitosamente.")
            if recurring_id:
                return redirect('recurring_payment_list')
            return redirect('expense_list')
    else:
        initial_data = {
            'exchange_rate': current_rate,
            'expense_date': today,
            'currency': 'HNL'
        }
        if recurring_obj:
            month_name = Receipt.MONTH_NAMES.get(today.month, str(today.month))
            initial_data.update({
                'recurring_payment': recurring_obj,
                'title': f"{recurring_obj.title} ({month_name} {today.year})",
                'category': recurring_obj.category,
                'expense_type': recurring_obj.expense_type,
                'currency': recurring_obj.currency,
                'amount': recurring_obj.estimated_amount,
                'beneficiary': recurring_obj.beneficiary,
                'description': f"Pago de servicio correspondiente a {month_name}. Cuenta/Clave: {recurring_obj.service_code}" if recurring_obj.service_code else f"Pago de servicio recurrente ({month_name})",
            })
        form = ExpenseForm(initial=initial_data, company=company)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'company': company,
        'current_rate': current_rate,
        'recurring_obj': recurring_obj,
        'title': f'Pagar Servicio: {recurring_obj.title}' if recurring_obj else 'Registrar Nuevo Gasto'
    })


@login_required
def expense_edit_view(request, pk):
    """Editar un gasto registrado."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    expense = get_object_or_404(Expense, pk=pk, company=company)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Gasto '{expense.title}' actualizado.")
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, company=company)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'company': company,
        'expense': expense,
        'current_rate': expense.exchange_rate,
        'title': f'Editar Gasto: {expense.title}'
    })


@login_required
def expense_delete_view(request, pk):
    """Eliminar un gasto de la bitácora."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    expense = get_object_or_404(Expense, pk=pk, company=company)

    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f"Gasto '{title}' eliminado de la bitácora.")
        return redirect('expense_list')

    return render(request, 'expenses/expense_confirm_delete.html', {
        'expense': expense,
        'company': company,
    })


# ==============================================================================
# PAGOS Y SERVICIOS RECURRENTES (PRESUPUESTO Y RECORDATORIOS)
# ==============================================================================

@login_required
def recurring_payment_list_view(request):
    """Gestión y control de pagos y servicios recurrentes mensuales (luz, internet, renta, etc.)."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    items = RecurringPayment.objects.filter(company=company)

    detailed_items = []
    budget_total_hnl = Decimal('0.00')
    budget_total_usd = Decimal('0.00')
    paid_total_hnl = Decimal('0.00')
    paid_total_usd = Decimal('0.00')
    pending_total_hnl = Decimal('0.00')
    pending_total_usd = Decimal('0.00')

    for item in items:
        status_info = item.get_status_for_month(year, month, today=today, current_rate=current_rate)
        detailed_items.append({
            'item': item,
            'status': status_info,
        })
        if item.is_active:
            budget_total_hnl += status_info['estimated_hnl']
            budget_total_usd += status_info['estimated_usd']
            if status_info['is_paid']:
                paid_total_hnl += status_info['paid_amount_hnl']
                paid_total_usd += status_info['paid_amount_usd']
            else:
                pending_total_hnl += status_info['estimated_hnl']
                pending_total_usd += status_info['estimated_usd']

    years = list(range(today.year - 3, today.year + 2))
    month_name = Receipt.MONTH_NAMES.get(month, str(month))

    return render(request, 'expenses/recurring_payment_list.html', {
        'company': company,
        'detailed_items': detailed_items,
        'selected_year': year,
        'selected_month': month,
        'month_name': month_name,
        'months': Receipt.MONTH_NAMES.items(),
        'years': years,
        'budget_total_hnl': budget_total_hnl,
        'budget_total_usd': budget_total_usd,
        'paid_total_hnl': paid_total_hnl,
        'paid_total_usd': paid_total_usd,
        'pending_total_hnl': pending_total_hnl,
        'pending_total_usd': pending_total_usd,
        'current_rate': current_rate,
    })


@login_required
def recurring_payment_create_view(request):
    """Crear un nuevo servicio o pago recurrente mensual."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    if request.method == 'POST':
        form = RecurringPaymentForm(request.POST)
        if form.is_valid():
            rec_pay = form.save(commit=False)
            rec_pay.company = company
            rec_pay.save()
            messages.success(request, f"Servicio recurrente '{rec_pay.title}' registrado en el presupuesto.")
            return redirect('recurring_payment_list')
    else:
        form = RecurringPaymentForm(initial={'currency': 'HNL', 'due_day': 1, 'is_active': True})

    return render(request, 'expenses/recurring_payment_form.html', {
        'form': form,
        'company': company,
        'title': 'Configurar Pago Recurrente (Presupuesto)',
    })


@login_required
def recurring_payment_edit_view(request, pk):
    """Editar un servicio o pago recurrente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    rec_pay = get_object_or_404(RecurringPayment, pk=pk, company=company)

    if request.method == 'POST':
        form = RecurringPaymentForm(request.POST, instance=rec_pay)
        if form.is_valid():
            form.save()
            messages.success(request, f"Servicio recurrente '{rec_pay.title}' actualizado.")
            return redirect('recurring_payment_list')
    else:
        form = RecurringPaymentForm(instance=rec_pay)

    return render(request, 'expenses/recurring_payment_form.html', {
        'form': form,
        'company': company,
        'rec_pay': rec_pay,
        'title': f'Editar Servicio Recurrente: {rec_pay.title}',
    })


@login_required
def recurring_payment_delete_view(request, pk):
    """Eliminar un servicio o pago recurrente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    rec_pay = get_object_or_404(RecurringPayment, pk=pk, company=company)

    if request.method == 'POST':
        title = rec_pay.title
        rec_pay.delete()
        messages.success(request, f"Servicio recurrente '{title}' eliminado.")
        return redirect('recurring_payment_list')

    return render(request, 'expenses/recurring_payment_confirm_delete.html', {
        'rec_pay': rec_pay,
        'company': company,
    })


# ==============================================================================
# ESTADO FINANCIERO PDF (CON BALANCE ACUMULADO / ROLLOVER)
# ==============================================================================

@login_required
def expense_financial_pdf_view(request):
    """Genera y descarga el estado financiero de ingresos vs gastos en PDF con arrastre de saldo."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    summary = get_month_financial_summary(company, year, month)
    month_name = Receipt.MONTH_NAMES.get(month, str(month))

    totals = {
        'rollover_balance_usd': summary['rollover_balance_usd'],
        'rollover_balance_hnl': summary['rollover_balance_hnl'],
        'total_available_usd': summary['total_available_usd'],
        'total_available_hnl': summary['total_available_hnl'],
        'income_usd': summary['month_income_usd'],
        'income_hnl': summary['month_income_hnl'],
        'rec_usd': summary['receipt_income_usd'],
        'rec_hnl': summary['receipt_income_hnl'],
        'ext_usd': summary['extra_income_usd'],
        'ext_hnl': summary['extra_income_hnl'],
        'exp_comp_usd': summary['exp_company_usd'],
        'exp_comp_hnl': summary['exp_company_hnl'],
        'exp_pers_usd': summary['exp_personal_usd'],
        'exp_pers_hnl': summary['exp_personal_hnl'],
        'total_expenses_usd': summary['total_expenses_usd'],
        'total_expenses_hnl': summary['total_expenses_hnl'],
        'op_balance_usd': summary['operational_balance_usd'],
        'op_balance_hnl': summary['operational_balance_hnl'],
        'net_balance_usd': summary['month_net_balance_usd'],
        'net_balance_hnl': summary['month_net_balance_hnl'],
        'ending_balance_usd': summary['ending_balance_usd'],
        'ending_balance_hnl': summary['ending_balance_hnl'],
    }

    pdf_bytes = generate_financial_report_pdf(
        company=company,
        year=year,
        month_name=month_name,
        income_items=summary['current_receipts'],
        expense_company_items=summary['expense_company_items'],
        expense_personal_items=summary['expense_personal_items'],
        totals=totals,
        extra_income_items=summary['current_extra_incomes']
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Estado-Financiero-{month_name}-{year}-{company.name[:15].replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
