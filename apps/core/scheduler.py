import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    global _scheduler
    return _scheduler


def start_scheduler():
    """
    Inicializa el planificador en segundo plano (APScheduler) para ejecutar la actualización
    de la tasa de cambio del dólar una vez al día entre la 1:00 AM y 4:00 AM (02:30 AM).
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from .services import sync_all_active_companies_exchange_rates

    _scheduler = BackgroundScheduler(timezone="America/Tegucigalpa")

    # Ejecuta diariamente a las 2:30 AM (hora de Honduras / GMT-6)
    # Cubre el rango requerido por el usuario (entre 1:00 AM y 4:00 AM)
    trigger = CronTrigger(hour=2, minute=30)

    _scheduler.add_job(
        sync_all_active_companies_exchange_rates,
        trigger=trigger,
        id='daily_exchange_rate_sync',
        name='Actualización diaria de tasa de cambio USD a HNL (02:30 AM)',
        replace_existing=True,
        misfire_grace_time=3600 * 4,
        coalesce=True
    )

    try:
        _scheduler.start()
        logger.info("APScheduler iniciado: Tarea programada diaria de tasa de cambio activa para las 02:30 AM.")
    except Exception as e:
        logger.error(f"Error al iniciar APScheduler: {e}")

    return _scheduler
