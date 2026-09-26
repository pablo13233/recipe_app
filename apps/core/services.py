import logging
from decimal import Decimal
import requests
from django.utils import timezone
from .models import Company, ExchangeRateLog

logger = logging.getLogger(__name__)

DEFAULT_RATE = Decimal('24.7500')


def get_current_exchange_rate(company=None):
    """
    Obtiene la tasa de cambio USD a HNL para el día actual.
    1. Revisa si ya hay un registro de hoy en ExchangeRateLog.
    2. Si no, intenta consultar la API pública en tiempo real y guardarla.
    3. Si la API falla o está offline, usa la tasa predeterminada de la empresa o el último registro.
    """
    today = timezone.localdate()
    
    # 1. Buscar si ya existe para hoy
    today_log = ExchangeRateLog.objects.filter(date=today).first()
    if today_log:
        return today_log.rate_usd_to_hnl

    # 2. Consultar API pública en tiempo real
    try:
        response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=3.5)
        if response.status_code == 200:
            data = response.json()
            hnl_rate = data.get('rates', {}).get('HNL')
            if hnl_rate:
                rate_decimal = Decimal(str(hnl_rate)).quantize(Decimal('0.0001'))
                ExchangeRateLog.objects.create(
                    date=today,
                    rate_usd_to_hnl=rate_decimal,
                    source='API'
                )
                return rate_decimal
    except Exception as e:
        logger.warning(f"No se pudo consultar API de tipo de cambio: {e}")

    # 3. Fallback al último registro histórico
    last_log = ExchangeRateLog.objects.order_by('-date', '-created_at').first()
    if last_log:
        return last_log.rate_usd_to_hnl

    # 4. Fallback a la empresa o default
    if company and company.default_exchange_rate:
        return company.default_exchange_rate

    return DEFAULT_RATE


def set_manual_exchange_rate(rate_value):
    """Guarda o actualiza manualmente la tasa de cambio para el día de hoy."""
    today = timezone.localdate()
    rate_decimal = Decimal(str(rate_value)).quantize(Decimal('0.0001'))
    
    log, created = ExchangeRateLog.objects.update_or_create(
        date=today,
        defaults={
            'rate_usd_to_hnl': rate_decimal,
            'source': 'Manual'
        }
    )
    return log.rate_usd_to_hnl
