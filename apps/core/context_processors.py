from django.utils import timezone
from .models import Company
from .services import get_current_exchange_rate


def company_context(request):
    """
    Context processor para proveer la empresa activa, lista de empresas
    del usuario, tasa de cambio actual y alertas de cobro en todos los templates.
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    if user.is_superuser:
        user_companies = Company.objects.filter(is_active=True).order_by('name')
    else:
        user_companies = Company.objects.filter(
            memberships__user=user, 
            is_active=True
        ).distinct().order_by('name')

    active_company_id = request.session.get('active_company_id')
    active_company = None

    if active_company_id:
        active_company = user_companies.filter(id=active_company_id).first()

    if not active_company and user_companies.exists():
        default_membership = user.company_memberships.filter(is_default=True).first()
        if default_membership and default_membership.company in user_companies:
            active_company = default_membership.company
        else:
            active_company = user_companies.first()
        
        request.session['active_company_id'] = active_company.id

    current_rate = get_current_exchange_rate(active_company)

    # Conteo de recordatorios de cobro pendientes o vencidos del mes actual (1ra o 2da parte)
    pending_reminders_count = 0
    if active_company:
        today = timezone.localdate()
        active_clients = active_company.clients.filter(is_active=True)
        for client in active_clients:
            st = client.get_reminder_status(today)
            if st['status'] in ['overdue', 'due_today']:
                pending_reminders_count += 1

    return {
        'user_companies': user_companies,
        'active_company': active_company,
        'current_exchange_rate': current_rate,
        'pending_reminders_count': pending_reminders_count,
        'today': timezone.localdate(),
    }
