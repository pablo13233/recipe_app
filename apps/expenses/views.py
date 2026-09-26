from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum, Q

from .models import Expense
from .forms import ExpenseForm
from .pdf import generate_financial_report_pdf
from apps.core.models import Company
from apps.core.services import get_current_exchange_rate
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

    expenses_qs = Expense.objects.filter(company=company).select_related('created_by')

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
    """Registrar un gasto en la bitácora."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.company = company
            expense.created_by = request.user
            expense.save()
            messages.success(request, f"Gasto '{expense.title}' registrado exitosamente.")
            return redirect('expense_list')
    else:
        form = ExpenseForm(initial={
            'exchange_rate': current_rate,
            'expense_date': today,
            'currency': 'HNL'
        })

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'company': company,
        'current_rate': current_rate,
        'title': 'Registrar Nuevo Gasto'
    })


@login_required
def expense_edit_view(request, pk):
    """Editar un gasto registrado."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    expense = get_object_or_404(Expense, pk=pk, company=company)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f"Gasto '{expense.title}' actualizado.")
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)

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


@login_required
def expense_financial_pdf_view(request):
    """Genera y descarga el estado financiero de ingresos vs gastos en PDF."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Ingresos (Recibos cobrados + Ingresos Extra/Externos)
    paid_receipts = Receipt.objects.filter(
        company=company,
        billing_year=year,
        billing_month=month,
        status='paid'
    ).select_related('client').order_by('issue_date')

    extra_incomes = ExtraIncome.objects.filter(
        company=company,
        income_date__year=year,
        income_date__month=month
    ).select_related('client').order_by('income_date')

    rec_usd = paid_receipts.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    rec_hnl = paid_receipts.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    ext_usd = extra_incomes.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    ext_hnl = extra_incomes.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    income_usd = rec_usd + ext_usd
    income_hnl = rec_hnl + ext_hnl

    # Gastos
    month_expenses = Expense.objects.filter(
        company=company,
        expense_date__year=year,
        expense_date__month=month
    ).order_by('expense_date')

    exp_comp = month_expenses.filter(expense_type='company')
    exp_pers = month_expenses.filter(expense_type='personal')

    exp_comp_usd = exp_comp.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_comp_hnl = exp_comp.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    exp_pers_usd = exp_pers.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_pers_hnl = exp_pers.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    op_bal_usd = income_usd - exp_comp_usd
    op_bal_hnl = income_hnl - exp_comp_hnl

    net_bal_usd = income_usd - (exp_comp_usd + exp_pers_usd)
    net_bal_hnl = income_hnl - (exp_comp_hnl + exp_pers_hnl)

    totals = {
        'income_usd': income_usd,
        'income_hnl': income_hnl,
        'rec_usd': rec_usd,
        'rec_hnl': rec_hnl,
        'ext_usd': ext_usd,
        'ext_hnl': ext_hnl,
        'exp_comp_usd': exp_comp_usd,
        'exp_comp_hnl': exp_comp_hnl,
        'exp_pers_usd': exp_pers_usd,
        'exp_pers_hnl': exp_pers_hnl,
        'op_balance_usd': op_bal_usd,
        'op_balance_hnl': op_bal_hnl,
        'net_balance_usd': net_bal_usd,
        'net_balance_hnl': net_bal_hnl,
    }

    month_name = Receipt.MONTH_NAMES.get(month, str(month))
    pdf_bytes = generate_financial_report_pdf(
        company=company,
        year=year,
        month_name=month_name,
        income_items=paid_receipts,
        expense_company_items=exp_comp,
        expense_personal_items=exp_pers,
        totals=totals,
        extra_income_items=extra_incomes
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Estado-Financiero-{month_name}-{year}-{company.name[:15].replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
