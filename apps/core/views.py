from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.http import HttpResponse

from .models import Company, ExchangeRateLog
from .forms import CompanyForm, ExchangeRateForm
from .services import get_current_exchange_rate, set_manual_exchange_rate
from apps.employees.models import CompanyMembership
from apps.clients.models import Client
from apps.receipts.models import Receipt, ExtraIncome
from apps.expenses.models import Expense


def landing_view(request):
    """Página de información pública inicial."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    today_rate = get_current_exchange_rate()
    return render(request, 'core/landing.html', {
        'today_rate': today_rate
    })


def login_view(request):
    """Inicio de sesión responsive."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"¡Bienvenido(a), {user.first_name or user.username}!")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña incorrectos. Por favor intenta de nuevo.")
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Cierre de sesión seguro."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('landing')


@login_required
def dashboard_view(request):
    """Panel principal del sistema."""
    user = request.user
    
    # Obtener empresas del usuario
    if user.is_superuser:
        companies = Company.objects.filter(is_active=True).order_by('name')
    else:
        companies = Company.objects.filter(memberships__user=user, is_active=True).distinct().order_by('name')

    # Si no tiene empresas creadas, guiar a crear la primera
    if not companies.exists():
        if user.is_superuser or user.is_staff:
            return redirect('company_create')
        return render(request, 'core/no_company.html')

    # Empresa activa
    active_company_id = request.session.get('active_company_id')
    active_company = None
    if active_company_id:
        active_company = companies.filter(id=active_company_id).first()
    
    if not active_company:
        active_company = companies.first()
        request.session['active_company_id'] = active_company.id

    today = timezone.localdate()
    current_year = today.year
    current_month = today.month

    # Tasa del día
    current_rate = get_current_exchange_rate(active_company)

    # Correlativo próximo formateado
    next_receipt_number = active_company.get_next_receipt_number_formatted()

    # Recibos del mes actual
    month_receipts = Receipt.objects.filter(
        company=active_company,
        billing_year=current_year,
        billing_month=current_month,
        status='paid'
    )
    receipt_income_usd = month_receipts.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    receipt_income_hnl = month_receipts.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    # Ingresos Extra / Externos del mes actual (Fuera de cobros mensuales)
    month_extra_incomes = ExtraIncome.objects.filter(
        company=active_company,
        income_date__year=current_year,
        income_date__month=current_month
    )
    extra_income_usd = month_extra_incomes.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    extra_income_hnl = month_extra_incomes.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    income_usd = receipt_income_usd + extra_income_usd
    income_hnl = receipt_income_hnl + extra_income_hnl

    # Gastos del mes actual (Empresa vs Personal)
    month_expenses = Expense.objects.filter(
        company=active_company,
        expense_date__year=current_year,
        expense_date__month=current_month
    )
    company_expenses = month_expenses.filter(expense_type='company')
    personal_expenses = month_expenses.filter(expense_type='personal')

    exp_company_usd = company_expenses.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_company_hnl = company_expenses.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    exp_personal_usd = personal_expenses.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_personal_hnl = personal_expenses.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    total_exp_usd = exp_company_usd + exp_personal_usd
    total_exp_hnl = exp_company_hnl + exp_personal_hnl

    # Balances
    operational_balance_usd = income_usd - exp_company_usd
    operational_balance_hnl = income_hnl - exp_company_hnl
    net_balance_usd = income_usd - total_exp_usd
    net_balance_hnl = income_hnl - total_exp_hnl

    # Estado de cobro de clientes para el mes actual
    all_clients = active_company.clients.filter(is_active=True).order_by('billing_day', 'name')
    paid_count = 0
    pending_count = 0
    urgent_reminders = []

    for client in all_clients:
        status_info = client.get_reminder_status(today)
        if status_info['status'] == 'paid':
            paid_count += 1
        else:
            pending_count += 1
            if status_info['status'] in ['overdue', 'due_today', 'upcoming']:
                urgent_reminders.append({
                    'client': client,
                    'status': status_info,
                    'whatsapp_url': client.get_whatsapp_reminder_url(current_rate)
                })

    # Últimos recibos emitidos
    latest_receipts = Receipt.objects.filter(company=active_company).order_by('-issue_date', '-sequence_number')[:6]
    
    # Últimos gastos registrados
    latest_expenses = Expense.objects.filter(company=active_company).order_by('-expense_date', '-created_at')[:6]

    context = {
        'company': active_company,
        'current_rate': current_rate,
        'next_receipt_number': next_receipt_number,
        'income_usd': income_usd,
        'income_hnl': income_hnl,
        'receipt_income_usd': receipt_income_usd,
        'receipt_income_hnl': receipt_income_hnl,
        'extra_income_usd': extra_income_usd,
        'extra_income_hnl': extra_income_hnl,
        'exp_company_usd': exp_company_usd,
        'exp_company_hnl': exp_company_hnl,
        'exp_personal_usd': exp_personal_usd,
        'exp_personal_hnl': exp_personal_hnl,
        'total_exp_usd': total_exp_usd,
        'total_exp_hnl': total_exp_hnl,
        'operational_balance_usd': operational_balance_usd,
        'operational_balance_hnl': operational_balance_hnl,
        'net_balance_usd': net_balance_usd,
        'net_balance_hnl': net_balance_hnl,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'total_clients': all_clients.count(),
        'urgent_reminders': urgent_reminders[:8],
        'latest_receipts': latest_receipts,
        'latest_expenses': latest_expenses,
        'current_month_name': Receipt.MONTH_NAMES.get(current_month, ''),
        'current_year': current_year,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def switch_company_view(request, company_id):
    """Cambia la empresa activa en la sesión del usuario."""
    if request.user.is_superuser:
        company = get_object_or_404(Company, id=company_id, is_active=True)
    else:
        company = get_object_or_404(Company, id=company_id, memberships__user=request.user, is_active=True)

    request.session['active_company_id'] = company.id
    messages.success(request, f"Cambiado a empresa: {company.name}")
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required
def company_list_view(request):
    """Lista de empresas."""
    if request.user.is_superuser:
        companies = Company.objects.all().order_by('name')
    else:
        companies = Company.objects.filter(memberships__user=request.user).order_by('name')
    return render(request, 'core/company_list.html', {'companies': companies})


@login_required
def company_create_view(request):
    """Crear una nueva empresa."""
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            # Asociar al usuario actual como admin de esta empresa
            CompanyMembership.objects.get_or_create(
                user=request.user,
                company=company,
                defaults={'role': 'admin', 'is_default': True}
            )
            request.session['active_company_id'] = company.id
            messages.success(request, f"Empresa '{company.name}' creada exitosamente.")
            return redirect('dashboard')
    else:
        form = CompanyForm()
    return render(request, 'core/company_form.html', {'form': form, 'title': 'Registrar Nueva Empresa'})


@login_required
def company_edit_view(request, pk):
    """Modificar configuración de una empresa."""
    if request.user.is_superuser:
        company = get_object_or_404(Company, pk=pk)
    else:
        membership = get_object_or_404(CompanyMembership, user=request.user, company_id=pk, role='admin')
        company = membership.company

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de '{company.name}' actualizados correctamente.")
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'core/company_form.html', {'form': form, 'company': company, 'title': f'Configurar {company.name}'})


@login_required
def update_exchange_rate_view(request):
    """Actualiza manualmente la tasa de cambio para hoy."""
    if request.method == 'POST':
        rate_val = request.POST.get('rate')
        if rate_val:
            try:
                new_rate = set_manual_exchange_rate(rate_val)
                messages.success(request, f"Tasa de cambio actualizada para hoy: $1 USD = L {new_rate:,.4f} HNL")
            except Exception as e:
                messages.error(request, f"Error al actualizar tasa: {e}")
        else:
            messages.error(request, "Monto de tasa no proporcionado.")
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required
def reports_view(request):
    """Centro de reportes interactivos mensuales y estados financieros."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    selected_year = int(request.GET.get('year', today.year))
    selected_month = int(request.GET.get('month', today.month))

    # Recibos pagados en el periodo
    paid_receipts = Receipt.objects.filter(
        company=company,
        billing_year=selected_year,
        billing_month=selected_month,
        status='paid'
    ).select_related('client').order_by('sequence_number')

    # Ingresos Extra y Externos del periodo
    extra_incomes = ExtraIncome.objects.filter(
        company=company,
        income_date__year=selected_year,
        income_date__month=selected_month
    ).select_related('client').order_by('-income_date')

    all_active_clients = company.clients.filter(is_active=True).order_by('billing_day', 'name')
    pending_clients = []
    for c in all_active_clients:
        if not c.has_paid_for_period(selected_year, selected_month):
            c.paid_period_usd = c.get_paid_amount_for_period(selected_year, selected_month)
            c.remaining_period_usd = c.get_remaining_balance_for_period(selected_year, selected_month)
            pending_clients.append(c)

    # Totales de ingresos (Recibos + Ingresos Extra/Externos)
    receipt_income_usd = paid_receipts.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    receipt_income_hnl = paid_receipts.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    extra_income_usd = extra_incomes.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    extra_income_hnl = extra_incomes.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    total_income_usd = receipt_income_usd + extra_income_usd
    total_income_hnl = receipt_income_hnl + extra_income_hnl

    # Gastos en ese mes
    month_expenses = Expense.objects.filter(
        company=company,
        expense_date__year=selected_year,
        expense_date__month=selected_month
    ).order_by('-expense_date')

    expense_company = month_expenses.filter(expense_type='company')
    expense_personal = month_expenses.filter(expense_type='personal')

    exp_comp_usd = expense_company.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_comp_hnl = expense_company.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    exp_pers_usd = expense_personal.aggregate(total=Sum('amount_usd'))['total'] or Decimal('0.00')
    exp_pers_hnl = expense_personal.aggregate(total=Sum('amount_hnl'))['total'] or Decimal('0.00')

    total_exp_usd = exp_comp_usd + exp_pers_usd
    total_exp_hnl = exp_comp_hnl + exp_pers_hnl

    net_balance_usd = total_income_usd - total_exp_usd
    net_balance_hnl = total_income_hnl - total_exp_hnl

    years_range = list(range(today.year - 4, today.year + 2))
    month_name = Receipt.MONTH_NAMES.get(selected_month, str(selected_month))

    context = {
        'company': company,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_name': month_name,
        'months': Receipt.MONTH_NAMES.items(),
        'years_range': years_range,
        'paid_receipts': paid_receipts,
        'extra_incomes': extra_incomes,
        'pending_clients': pending_clients,
        'receipt_income_usd': receipt_income_usd,
        'receipt_income_hnl': receipt_income_hnl,
        'extra_income_usd': extra_income_usd,
        'extra_income_hnl': extra_income_hnl,
        'total_income_usd': total_income_usd,
        'total_income_hnl': total_income_hnl,
        'expense_company': expense_company,
        'expense_personal': expense_personal,
        'exp_comp_usd': exp_comp_usd,
        'exp_comp_hnl': exp_comp_hnl,
        'exp_pers_usd': exp_pers_usd,
        'exp_pers_hnl': exp_pers_hnl,
        'total_exp_usd': total_exp_usd,
        'total_exp_hnl': total_exp_hnl,
        'net_balance_usd': net_balance_usd,
        'net_balance_hnl': net_balance_hnl,
    }
    return render(request, 'core/reports.html', context)


@login_required
def reminders_view(request):
    """Centro de recordatorios de cobro a clientes."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)

    clients = company.clients.filter(is_active=True).order_by('billing_day', 'name')
    
    overdue_list = []
    due_today_list = []
    upcoming_list = []
    pending_list = []
    paid_list = []

    for client in clients:
        info = client.get_reminder_status(today)
        due_usd = info.get('next_amount_usd') or client.monthly_fee_usd
        data = {
            'client': client,
            'info': info,
            'due_usd': due_usd,
            'whatsapp_url': client.get_whatsapp_reminder_url(current_rate),
            'approx_hnl': (due_usd * current_rate).quantize(Decimal('0.01'))
        }
        if info['status'] == 'paid':
            paid_list.append(data)
        elif info['status'] == 'overdue':
            overdue_list.append(data)
        elif info['status'] == 'due_today':
            due_today_list.append(data)
        elif info['status'] == 'upcoming':
            upcoming_list.append(data)
        else:
            pending_list.append(data)

    context = {
        'company': company,
        'today': today,
        'current_rate': current_rate,
        'overdue_list': overdue_list,
        'due_today_list': due_today_list,
        'upcoming_list': upcoming_list,
        'pending_list': pending_list,
        'paid_list': paid_list,
        'month_name': Receipt.MONTH_NAMES.get(today.month, ''),
    }
    return render(request, 'core/reminders.html', context)
