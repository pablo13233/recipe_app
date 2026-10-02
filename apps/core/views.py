from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse

from .models import Company, ExchangeRateLog
from .forms import CompanyForm, ExchangeRateForm
from .services import (
    get_current_exchange_rate, set_manual_exchange_rate, 
    get_month_financial_summary, fetch_live_exchange_rate,
    sync_company_exchange_rate
)
from apps.employees.models import CompanyMembership
from apps.clients.models import Client
from apps.receipts.models import Receipt, ExtraIncome
from apps.expenses.models import Expense, RecurringPayment


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
    """Panel principal del sistema con balance acumulado y recordatorios."""
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

    # Resumen financiero con arrastre de saldo / sobrante del mes anterior (Rollover)
    fin_summary = get_month_financial_summary(active_company, current_year, current_month)

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

    # Recordatorios de Pagos Recurrentes (Luz, Internet, etc.) del mes
    recurring_items = RecurringPayment.objects.filter(company=active_company, is_active=True)
    urgent_recurring_payments = []
    recurring_budget_hnl = Decimal('0.00')
    recurring_paid_hnl = Decimal('0.00')

    for r_item in recurring_items:
        r_status = r_item.get_status_for_month(current_year, current_month, today=today, current_rate=current_rate)
        recurring_budget_hnl += r_status['estimated_hnl']
        if r_status['is_paid']:
            recurring_paid_hnl += r_status['paid_amount_hnl']
        else:
            if r_status['status'] in ['overdue', 'due_today', 'upcoming']:
                urgent_recurring_payments.append({
                    'item': r_item,
                    'status': r_status
                })

    # Últimos recibos emitidos
    latest_receipts = Receipt.objects.filter(company=active_company).order_by('-issue_date', '-sequence_number')[:6]
    
    # Últimos gastos registrados
    latest_expenses = Expense.objects.filter(company=active_company).order_by('-expense_date', '-created_at')[:6]

    context = {
        'company': active_company,
        'current_rate': current_rate,
        'next_receipt_number': next_receipt_number,
        # Finanzas integradas con arrastre de saldo (rollover)
        'rollover_balance_usd': fin_summary['rollover_balance_usd'],
        'rollover_balance_hnl': fin_summary['rollover_balance_hnl'],
        'total_available_usd': fin_summary['total_available_usd'],
        'total_available_hnl': fin_summary['total_available_hnl'],
        'income_usd': fin_summary['month_income_usd'],
        'income_hnl': fin_summary['month_income_hnl'],
        'receipt_income_usd': fin_summary['receipt_income_usd'],
        'receipt_income_hnl': fin_summary['receipt_income_hnl'],
        'extra_income_usd': fin_summary['extra_income_usd'],
        'extra_income_hnl': fin_summary['extra_income_hnl'],
        'exp_company_usd': fin_summary['exp_company_usd'],
        'exp_company_hnl': fin_summary['exp_company_hnl'],
        'exp_personal_usd': fin_summary['exp_personal_usd'],
        'exp_personal_hnl': fin_summary['exp_personal_hnl'],
        'total_exp_usd': fin_summary['total_expenses_usd'],
        'total_exp_hnl': fin_summary['total_expenses_hnl'],
        'operational_balance_usd': fin_summary['operational_balance_usd'],
        'operational_balance_hnl': fin_summary['operational_balance_hnl'],
        'net_balance_usd': fin_summary['month_net_balance_usd'],
        'net_balance_hnl': fin_summary['month_net_balance_hnl'],
        'ending_balance_usd': fin_summary['ending_balance_usd'],
        'ending_balance_hnl': fin_summary['ending_balance_hnl'],
        # Clientes
        'paid_count': paid_count,
        'pending_count': pending_count,
        'total_clients': all_clients.count(),
        'urgent_reminders': urgent_reminders[:8],
        # Pagos recurrentes
        'urgent_recurring_payments': urgent_recurring_payments[:6],
        'recurring_budget_hnl': recurring_budget_hnl,
        'recurring_paid_hnl': recurring_paid_hnl,
        'recurring_pending_hnl': recurring_budget_hnl - recurring_paid_hnl,
        # Movimientos recientes
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
        active_company_id = request.session.get('active_company_id')
        company = Company.objects.filter(id=active_company_id).first()
        if rate_val:
            try:
                new_rate = set_manual_exchange_rate(rate_val, company=company)
                messages.success(request, f"Tasa de cambio actualizada para hoy: $1 USD = L {new_rate:,.4f} HNL")
            except Exception as e:
                messages.error(request, f"Error al actualizar tasa: {e}")
        else:
            messages.error(request, "Monto de tasa no proporcionado.")
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required
def sync_exchange_rate_now_view(request):
    """
    Sincroniza en el momento la tasa de cambio con la API para la empresa activa bajo demanda manual.
    """
    active_company_id = request.session.get('active_company_id')
    company = Company.objects.filter(id=active_company_id).first()
    if not company:
        messages.error(request, "No hay una empresa activa seleccionada.")
        return redirect('dashboard')

    rate, updated, msg = sync_company_exchange_rate(company, force=True)
    if updated:
        messages.success(request, f"Tasa de cambio sincronizada exitosamente desde la API: $1 USD = L {rate:,.4f} HNL")
    else:
        messages.warning(request, f"Aviso de sincronización: {msg}")

    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required
def test_exchange_rate_api_view(request):
    """
    Endpoint AJAX para probar la conectividad y respuesta de un endpoint o API Key de tipo de cambio.
    Recibe por POST o GET 'api_url' y 'api_key'.
    """
    if request.method not in ['POST', 'GET']:
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    api_url = request.POST.get('api_url') or request.GET.get('api_url') or ''
    api_key = request.POST.get('api_key') or request.GET.get('api_key') or ''

    rate, error, raw = fetch_live_exchange_rate(
        custom_url=api_url if api_url.strip() else None,
        custom_api_key=api_key if api_key.strip() else None,
        return_detail=True
    )

    if rate is not None:
        return JsonResponse({
            'success': True,
            'rate': str(rate),
            'formatted_rate': f"$1 USD = L {rate:,.4f} HNL",
            'message': f"¡Conexión exitosa! Tasa obtenida en tiempo real: $1 USD = L {rate:,.4f} HNL"
        })
    else:
        return JsonResponse({
            'success': False,
            'error': error or "No se pudo obtener la tasa desde el endpoint proporcionado."
        })


@login_required
def reports_view(request):
    """Centro de reportes interactivos mensuales y estados financieros con arrastre de saldo."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)
    selected_year = int(request.GET.get('year', today.year))
    selected_month = int(request.GET.get('month', today.month))

    fin_summary = get_month_financial_summary(company, selected_year, selected_month)

    all_active_clients = company.clients.filter(is_active=True).order_by('billing_day', 'name')
    pending_clients = []
    for c in all_active_clients:
        if not c.has_paid_for_period(selected_year, selected_month):
            c.paid_period_usd = c.get_paid_amount_for_period(selected_year, selected_month)
            c.remaining_period_usd = c.get_remaining_balance_for_period(selected_year, selected_month)
            pending_clients.append(c)

    # Pagos recurrentes en este mes
    recurring_items = RecurringPayment.objects.filter(company=company)
    recurring_data = []
    budget_tot_hnl = Decimal('0.00')
    budget_paid_hnl = Decimal('0.00')
    for r in recurring_items:
        r_stat = r.get_status_for_month(selected_year, selected_month, today=today, current_rate=current_rate)
        recurring_data.append({'item': r, 'status': r_stat})
        if r.is_active:
            budget_tot_hnl += r_stat['estimated_hnl']
            if r_stat['is_paid']:
                budget_paid_hnl += r_stat['paid_amount_hnl']

    years_range = list(range(today.year - 4, today.year + 2))
    month_name = Receipt.MONTH_NAMES.get(selected_month, str(selected_month))

    context = {
        'company': company,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_name': month_name,
        'months': Receipt.MONTH_NAMES.items(),
        'years_range': years_range,
        'paid_receipts': fin_summary['current_receipts'],
        'extra_incomes': fin_summary['current_extra_incomes'],
        'pending_clients': pending_clients,
        'recurring_data': recurring_data,
        'budget_tot_hnl': budget_tot_hnl,
        'budget_paid_hnl': budget_paid_hnl,
        # Balances y arrastre
        'rollover_balance_usd': fin_summary['rollover_balance_usd'],
        'rollover_balance_hnl': fin_summary['rollover_balance_hnl'],
        'total_available_usd': fin_summary['total_available_usd'],
        'total_available_hnl': fin_summary['total_available_hnl'],
        'receipt_income_usd': fin_summary['receipt_income_usd'],
        'receipt_income_hnl': fin_summary['receipt_income_hnl'],
        'extra_income_usd': fin_summary['extra_income_usd'],
        'extra_income_hnl': fin_summary['extra_income_hnl'],
        'total_income_usd': fin_summary['month_income_usd'],
        'total_income_hnl': fin_summary['month_income_hnl'],
        'expense_company': fin_summary['expense_company_items'],
        'expense_personal': fin_summary['expense_personal_items'],
        'exp_comp_usd': fin_summary['exp_company_usd'],
        'exp_comp_hnl': fin_summary['exp_company_hnl'],
        'exp_pers_usd': fin_summary['exp_personal_usd'],
        'exp_pers_hnl': fin_summary['exp_personal_hnl'],
        'total_exp_usd': fin_summary['total_expenses_usd'],
        'total_exp_hnl': fin_summary['total_expenses_hnl'],
        'operational_balance_usd': fin_summary['operational_balance_usd'],
        'operational_balance_hnl': fin_summary['operational_balance_hnl'],
        'net_balance_usd': fin_summary['month_net_balance_usd'],
        'net_balance_hnl': fin_summary['month_net_balance_hnl'],
        'ending_balance_usd': fin_summary['ending_balance_usd'],
        'ending_balance_hnl': fin_summary['ending_balance_hnl'],
    }
    return render(request, 'core/reports.html', context)


@login_required
def reminders_view(request):
    """Centro de recordatorios: cobros a clientes y pagos recurrentes de la empresa (luz, internet, etc.)."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)

    # 1. Cobros a Clientes
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

    # 2. Pagos Recurrentes / Cuentas por Pagar (Luz, Internet, Alquiler, etc.)
    recurring_items = RecurringPayment.objects.filter(company=company, is_active=True).order_by('due_day', 'title')
    rec_overdue_list = []
    rec_due_today_list = []
    rec_upcoming_list = []
    rec_pending_list = []
    rec_paid_list = []

    rec_budget_hnl = Decimal('0.00')
    rec_paid_hnl = Decimal('0.00')
    rec_pending_hnl = Decimal('0.00')

    for r in recurring_items:
        r_info = r.get_status_for_month(today.year, today.month, today=today, current_rate=current_rate)
        r_data = {
            'item': r,
            'info': r_info,
        }
        rec_budget_hnl += r_info['estimated_hnl']
        if r_info['is_paid']:
            rec_paid_hnl += r_info['paid_amount_hnl']
            rec_paid_list.append(r_data)
        else:
            rec_pending_hnl += r_info['estimated_hnl']
            if r_info['status'] == 'overdue':
                rec_overdue_list.append(r_data)
            elif r_info['status'] == 'due_today':
                rec_due_today_list.append(r_data)
            elif r_info['status'] == 'upcoming':
                rec_upcoming_list.append(r_data)
            else:
                rec_pending_list.append(r_data)

    context = {
        'company': company,
        'today': today,
        'current_rate': current_rate,
        # Clientes
        'overdue_list': overdue_list,
        'due_today_list': due_today_list,
        'upcoming_list': upcoming_list,
        'pending_list': pending_list,
        'paid_list': paid_list,
        # Pagos recurrentes
        'rec_overdue_list': rec_overdue_list,
        'rec_due_today_list': rec_due_today_list,
        'rec_upcoming_list': rec_upcoming_list,
        'rec_pending_list': rec_pending_list,
        'rec_paid_list': rec_paid_list,
        'rec_budget_hnl': rec_budget_hnl,
        'rec_paid_hnl': rec_paid_hnl,
        'rec_pending_hnl': rec_pending_hnl,
        'month_name': Receipt.MONTH_NAMES.get(today.month, ''),
    }
    return render(request, 'core/reminders.html', context)
