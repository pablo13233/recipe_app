from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q

from .models import Client
from .forms import ClientForm
from apps.core.models import Company
from apps.core.services import get_current_exchange_rate


@login_required
def client_list_view(request):
    """Lista y búsqueda de clientes de la empresa activa."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    today = timezone.localdate()
    current_rate = get_current_exchange_rate(company)

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    clients_qs = Client.objects.filter(company=company)

    if query:
        clients_qs = clients_qs.filter(
            Q(name__icontains=query) |
            Q(tax_id__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    clients_data = []
    for client in clients_qs.order_by('name'):
        st = client.get_reminder_status(today)
        if status_filter == 'paid' and st['status'] != 'paid':
            continue
        elif status_filter == 'unpaid' and st['status'] == 'paid':
            continue
        elif status_filter == 'overdue' and st['status'] != 'overdue':
            continue

        clients_data.append({
            'client': client,
            'status_info': st,
            'approx_hnl': (client.monthly_fee_usd * current_rate).quantize(Decimal('0.01')),
            'whatsapp_url': client.get_whatsapp_reminder_url(current_rate),
        })

    return render(request, 'clients/client_list.html', {
        'company': company,
        'clients_data': clients_data,
        'query': query,
        'status_filter': status_filter,
        'current_rate': current_rate,
        'total_clients': clients_qs.count(),
    })


@login_required
def client_create_view(request):
    """Registrar un nuevo cliente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)

    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.company = company
            client.save()
            messages.success(request, f"Cliente '{client.name}' registrado exitosamente.")
            return redirect('client_list')
    else:
        form = ClientForm()

    return render(request, 'clients/client_form.html', {
        'form': form,
        'company': company,
        'title': 'Registrar Nuevo Cliente'
    })


@login_required
def client_edit_view(request, pk):
    """Editar información de un cliente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    client = get_object_or_404(Client, pk=pk, company=company)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de '{client.name}' actualizados con éxito.")
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/client_form.html', {
        'form': form,
        'company': company,
        'client': client,
        'title': f'Editar Cliente: {client.name}'
    })


@login_required
def client_toggle_status_view(request, pk):
    """Activa o desactiva un cliente."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    client = get_object_or_404(Client, pk=pk, company=company)

    client.is_active = not client.is_active
    client.save()
    status_str = "activado" if client.is_active else "desactivado"
    messages.info(request, f"Cliente '{client.name}' ha sido {status_str}.")
    return redirect('client_list')


@login_required
def client_api_detail_view(request, pk):
    """Endpoint JSON para obtener datos del cliente y cuota sugerida al crear recibos."""
    active_company_id = request.session.get('active_company_id')
    company = get_object_or_404(Company, id=active_company_id)
    client = get_object_or_404(Client, pk=pk, company=company)

    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    suggestion = client.get_next_payment_suggestion(year, month)

    return JsonResponse({
        'id': client.id,
        'name': client.name,
        'monthly_fee_usd': float(client.monthly_fee_usd),
        'payment_parts': client.payment_parts,
        'billing_day': client.billing_day,
        'first_payment_usd': float(client.first_payment_usd),
        'second_billing_day': client.second_billing_day,
        'second_payment_usd': float(client.second_payment_usd),
        'paid_usd': float(suggestion['paid_usd']),
        'remaining_usd': float(suggestion['remaining_usd']),
        'suggested_usd': float(suggestion['suggested_usd']),
        'part_label': suggestion['part_label'],
        'default_concept': client.default_concept,
        'phone': client.phone,
        'address': client.address,
    })
