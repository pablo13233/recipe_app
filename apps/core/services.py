import logging
from decimal import Decimal
import requests
from django.utils import timezone
from .models import Company, ExchangeRateLog

logger = logging.getLogger(__name__)

DEFAULT_RATE = Decimal('24.7500')


def fetch_live_exchange_rate(company=None, custom_url=None, custom_api_key=None, return_detail=False):
    """
    Realiza la consulta en vivo al endpoint configurado (con su respectiva API key si aplica)
    y retorna la tasa de cambio USD a HNL obtenida, o None / (rate, error, raw) si falló.
    """
    url = custom_url
    api_key = custom_api_key
    if not url and company:
        url = company.exchange_rate_api_url
        api_key = company.exchange_rate_api_key

    if not url:
        url = "https://open.er-api.com/v6/latest/USD"

    # Si hay API Key configurada y la URL tiene el placeholder {api_key}, reemplazarla
    clean_url = url.strip()
    if api_key:
        clean_key = api_key.strip()
        if "{api_key}" in clean_url:
            clean_url = clean_url.replace("{api_key}", clean_key)
        elif "{API_KEY}" in clean_url:
            clean_url = clean_url.replace("{API_KEY}", clean_key)

    headers = {'User-Agent': 'RecipeApp/1.0'}
    if api_key and "open.er-api.com" not in clean_url and "{api_key}" not in url and "{API_KEY}" not in url:
        headers['apikey'] = api_key.strip()
        headers['Authorization'] = f"Bearer {api_key.strip()}"

    error_msg = None
    try:
        response = requests.get(clean_url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            hnl_val = None

            # Formato estándar 1: data['rates']['HNL'] (open.er-api, openexchangerates)
            if isinstance(data.get('rates'), dict) and 'HNL' in data['rates']:
                hnl_val = data['rates']['HNL']
            # Formato estándar 2: data['conversion_rates']['HNL'] (exchangerate-api v6)
            elif isinstance(data.get('conversion_rates'), dict) and 'HNL' in data['conversion_rates']:
                hnl_val = data['conversion_rates']['HNL']
            # Formato estándar 3: data['quotes']['USDHNL'] (currencylayer)
            elif isinstance(data.get('quotes'), dict) and 'USDHNL' in data['quotes']:
                hnl_val = data['quotes']['USDHNL']
            # Formato estándar 4: búsqueda recursiva de la clave 'HNL' en cualquier JSON
            else:
                def find_key(obj, key):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if str(k).upper() == key:
                                return v
                            if isinstance(v, (dict, list)):
                                item = find_key(v, key)
                                if item is not None:
                                    return item
                    elif isinstance(obj, list):
                        for el in obj:
                            item = find_key(el, key)
                            if item is not None:
                                return item
                    return None
                hnl_val = find_key(data, 'HNL')

            if hnl_val is not None:
                rate_decimal = Decimal(str(hnl_val)).quantize(Decimal('0.0001'))
                if rate_decimal > Decimal('0.0000'):
                    if return_detail:
                        return rate_decimal, None, data
                    return rate_decimal
            error_msg = "No se encontró el valor de la moneda 'HNL' en la respuesta del endpoint."
        else:
            error_msg = f"El servidor respondió con código HTTP {response.status_code}: {response.text[:200]}"
    except requests.exceptions.Timeout:
        error_msg = "Tiempo de espera agotado (timeout al conectar con la URL)."
    except requests.exceptions.RequestException as e:
        error_msg = f"Error de conexión: {str(e)}"
    except Exception as e:
        error_msg = f"Error procesando respuesta: {str(e)}"

    logger.warning(f"Error consultando endpoint de tipo de cambio ({clean_url}): {error_msg}")
    if return_detail:
        return None, error_msg, None
    return None


def get_current_exchange_rate(company=None):
    """
    Obtiene la tasa de cambio USD a HNL guardada en la base de datos para la empresa.
    NO realiza llamadas HTTP a la API durante la carga de páginas web.
    La tasa se actualiza 1 vez al día entre 1:00 AM y 4:00 AM mediante la tarea programada.
    """
    if company:
        if company.current_exchange_rate and company.current_exchange_rate > Decimal('0.0000'):
            return company.current_exchange_rate
        if company.default_exchange_rate and company.default_exchange_rate > Decimal('0.0000'):
            return company.default_exchange_rate

    # Si no se pasó empresa o no tiene tasa guardada, buscar primera empresa activa
    first_comp = Company.objects.filter(is_active=True).first()
    if first_comp and first_comp.current_exchange_rate and first_comp.current_exchange_rate > Decimal('0.0000'):
        return first_comp.current_exchange_rate

    # Fallback al último registro en log
    last_log = ExchangeRateLog.objects.order_by('-date', '-created_at').first()
    if last_log and last_log.rate_usd_to_hnl > Decimal('0.0000'):
        return last_log.rate_usd_to_hnl

    return DEFAULT_RATE


def sync_company_exchange_rate(company, force=False):
    """
    Función ejecutada por la tarea programada (1:00 AM - 4:00 AM) para actualizar
    la tasa de cambio del día de una empresa consultando su endpoint configurado.
    Actualiza company.current_exchange_rate, company.exchange_rate_updated_at
    y registra un ExchangeRateLog.
    """
    today = timezone.localdate()
    now = timezone.now()

    # Si no es forzado y ya se actualizó hoy, omitir
    if not force and company.exchange_rate_updated_at:
        local_updated_date = timezone.localtime(company.exchange_rate_updated_at).date()
        if local_updated_date == today:
            logger.info(f"Tasa para {company.name} ya fue actualizada hoy ({company.current_exchange_rate}).")
            return company.current_exchange_rate, False, "Tasa ya actualizada el día de hoy"

    if not company.exchange_rate_auto_update:
        # Usa la tasa fija predeterminada configurada
        company.current_exchange_rate = company.default_exchange_rate
        company.exchange_rate_updated_at = now
        company.save(update_fields=['current_exchange_rate', 'exchange_rate_updated_at'])
        ExchangeRateLog.objects.update_or_create(
            company=company,
            date=today,
            defaults={
                'rate_usd_to_hnl': company.default_exchange_rate,
                'source': 'Predeterminada (Fija)'
            }
        )
        return company.default_exchange_rate, True, "Actualizada con tasa fija predeterminada"

    # Consultar API configurada
    rate, error, raw = fetch_live_exchange_rate(company=company, return_detail=True)
    if rate is not None:
        company.current_exchange_rate = rate
        company.exchange_rate_updated_at = now
        company.save(update_fields=['current_exchange_rate', 'exchange_rate_updated_at'])
        ExchangeRateLog.objects.update_or_create(
            company=company,
            date=today,
            defaults={
                'rate_usd_to_hnl': rate,
                'source': 'API (Tarea Programada)'
            }
        )
        logger.info(f"Tarea programada actualizó tasa para {company.name}: $1 USD = L {rate} HNL")
        return rate, True, f"Tasa actualizada con éxito: $1 USD = L {rate} HNL"
    else:
        # Si falló la API por timeout o error de red, mantener tasa previa o predeterminada
        fallback_rate = company.current_exchange_rate or company.default_exchange_rate or DEFAULT_RATE
        logger.warning(f"Fallo al consultar API para {company.name}: {error}. Manteniendo tasa previa: {fallback_rate}")
        return fallback_rate, False, f"Error en API ({error}). Se conservó tasa previa: L {fallback_rate}"


def sync_all_active_companies_exchange_rates(force=False):
    """
    Recorre todas las empresas activas y actualiza sus tasas de cambio.
    Retorna resumen de ejecuciones.
    """
    companies = Company.objects.filter(is_active=True)
    results = []
    for comp in companies:
        rate, updated, msg = sync_company_exchange_rate(comp, force=force)
        results.append({'company': comp, 'rate': rate, 'updated': updated, 'message': msg})
    return results


def set_manual_exchange_rate(rate_value, company=None):
    """Guarda o actualiza manualmente la tasa de cambio para el día de hoy."""
    today = timezone.localdate()
    now = timezone.now()
    rate_decimal = Decimal(str(rate_value)).quantize(Decimal('0.0001'))

    if company:
        company.current_exchange_rate = rate_decimal
        company.exchange_rate_updated_at = now
        company.save(update_fields=['current_exchange_rate', 'exchange_rate_updated_at'])

    filter_kwargs = {'date': today}
    if company:
        filter_kwargs['company'] = company

    log, created = ExchangeRateLog.objects.update_or_create(
        **filter_kwargs,
        defaults={
            'rate_usd_to_hnl': rate_decimal,
            'source': 'Manual'
        }
    )
    return log.rate_usd_to_hnl


def get_month_financial_summary(company, year, month):
    """
    Calcula el balance financiero integral de un mes para una empresa,
    arrastrando el sobrante / balance acumulado de meses anteriores (rollover).
    """
    import datetime
    from django.db.models import Sum, Q
    from apps.receipts.models import Receipt, ExtraIncome
    from apps.expenses.models import Expense

    cutoff_date = datetime.date(year, month, 1)

    # 1. Ingresos y Gastos de meses anteriores
    prior_receipts = Receipt.objects.filter(
        company=company,
        status='paid'
    ).filter(
        Q(billing_year__lt=year) |
        Q(billing_year=year, billing_month__lt=month)
    ).aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))

    prior_extra = ExtraIncome.objects.filter(
        company=company,
        income_date__lt=cutoff_date
    ).aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))

    prior_expenses = Expense.objects.filter(
        company=company,
        expense_date__lt=cutoff_date
    ).aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))

    prior_income_usd = (prior_receipts['usd'] or Decimal('0.00')) + (prior_extra['usd'] or Decimal('0.00'))
    prior_income_hnl = (prior_receipts['hnl'] or Decimal('0.00')) + (prior_extra['hnl'] or Decimal('0.00'))

    prior_exp_usd = prior_expenses['usd'] or Decimal('0.00')
    prior_exp_hnl = prior_expenses['hnl'] or Decimal('0.00')

    init_bal_usd = getattr(company, 'initial_balance_usd', Decimal('0.00')) or Decimal('0.00')
    init_bal_hnl = getattr(company, 'initial_balance_hnl', Decimal('0.00')) or Decimal('0.00')

    rollover_balance_usd = (init_bal_usd + prior_income_usd - prior_exp_usd).quantize(Decimal('0.01'))
    rollover_balance_hnl = (init_bal_hnl + prior_income_hnl - prior_exp_hnl).quantize(Decimal('0.01'))

    # 2. Movimientos del mes consultado
    current_receipts_qs = Receipt.objects.filter(
        company=company,
        billing_year=year,
        billing_month=month,
        status='paid'
    ).select_related('client', 'created_by')

    current_extra_qs = ExtraIncome.objects.filter(
        company=company,
        income_date__year=year,
        income_date__month=month
    ).select_related('client', 'created_by')

    rec_totals = current_receipts_qs.aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))
    ext_totals = current_extra_qs.aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))

    receipt_income_usd = rec_totals['usd'] or Decimal('0.00')
    receipt_income_hnl = rec_totals['hnl'] or Decimal('0.00')

    extra_income_usd = ext_totals['usd'] or Decimal('0.00')
    extra_income_hnl = ext_totals['hnl'] or Decimal('0.00')

    month_income_usd = receipt_income_usd + extra_income_usd
    month_income_hnl = receipt_income_hnl + extra_income_hnl

    # Fondos totales disponibles (Sobrante anterior + Ingresos de este mes)
    total_available_usd = rollover_balance_usd + month_income_usd
    total_available_hnl = rollover_balance_hnl + month_income_hnl

    # Gastos de este mes
    current_expenses_qs = Expense.objects.filter(
        company=company,
        expense_date__year=year,
        expense_date__month=month
    ).select_related('created_by')

    comp_exp_totals = current_expenses_qs.filter(expense_type='company').aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))
    pers_exp_totals = current_expenses_qs.filter(expense_type='personal').aggregate(usd=Sum('amount_usd'), hnl=Sum('amount_hnl'))

    exp_company_usd = comp_exp_totals['usd'] or Decimal('0.00')
    exp_company_hnl = comp_exp_totals['hnl'] or Decimal('0.00')

    exp_personal_usd = pers_exp_totals['usd'] or Decimal('0.00')
    exp_personal_hnl = pers_exp_totals['hnl'] or Decimal('0.00')

    total_expenses_usd = exp_company_usd + exp_personal_usd
    total_expenses_hnl = exp_company_hnl + exp_personal_hnl

    # Balances
    operational_balance_usd = month_income_usd - exp_company_usd
    operational_balance_hnl = month_income_hnl - exp_company_hnl

    # Balance neto exclusivo de este mes
    month_net_balance_usd = month_income_usd - total_expenses_usd
    month_net_balance_hnl = month_income_hnl - total_expenses_hnl

    # Saldo final acumulado al cierre del mes (Sobrante final que pasa al siguiente mes)
    ending_balance_usd = rollover_balance_usd + month_net_balance_usd
    ending_balance_hnl = rollover_balance_hnl + month_net_balance_hnl

    return {
        'rollover_balance_usd': rollover_balance_usd,
        'rollover_balance_hnl': rollover_balance_hnl,
        'has_positive_rollover': rollover_balance_hnl > Decimal('0.00'),
        'receipt_income_usd': receipt_income_usd,
        'receipt_income_hnl': receipt_income_hnl,
        'extra_income_usd': extra_income_usd,
        'extra_income_hnl': extra_income_hnl,
        'month_income_usd': month_income_usd,
        'month_income_hnl': month_income_hnl,
        'total_available_usd': total_available_usd,
        'total_available_hnl': total_available_hnl,
        'exp_company_usd': exp_company_usd,
        'exp_company_hnl': exp_company_hnl,
        'exp_personal_usd': exp_personal_usd,
        'exp_personal_hnl': exp_personal_hnl,
        'total_expenses_usd': total_expenses_usd,
        'total_expenses_hnl': total_expenses_hnl,
        'operational_balance_usd': operational_balance_usd,
        'operational_balance_hnl': operational_balance_hnl,
        'month_net_balance_usd': month_net_balance_usd,
        'month_net_balance_hnl': month_net_balance_hnl,
        'ending_balance_usd': ending_balance_usd,
        'ending_balance_hnl': ending_balance_hnl,
        'current_receipts': current_receipts_qs,
        'current_extra_incomes': current_extra_qs,
        'current_expenses': current_expenses_qs,
        'expense_company_items': current_expenses_qs.filter(expense_type='company'),
        'expense_personal_items': current_expenses_qs.filter(expense_type='personal'),
    }
