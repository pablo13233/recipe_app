import os
import sys
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Iniciar el scheduler únicamente cuando el servidor web esté en ejecución
        # y evitando duplicación en el autoreloader de runserver
        is_web_server = any(arg in sys.argv for arg in ['runserver', 'gunicorn', 'uvicorn', 'daphne'])
        is_main_process = os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv

        if is_web_server and is_main_process:
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"No se pudo iniciar el scheduler de tareas: {e}")
