from django.core.management.base import BaseCommand
from apps.core.models import Company
from apps.core.services import sync_company_exchange_rate, sync_all_active_companies_exchange_rates


class Command(BaseCommand):
    help = "Actualiza la tasa de cambio USD a HNL del día para las empresas activas mediante la API configurada."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la actualización aunque la tasa ya se haya actualizado el día de hoy.'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            default=None,
            help='ID específico de la empresa a actualizar (opcional).'
        )

    def handle(self, *args, **options):
        force = options['force']
        company_id = options['company_id']

        self.stdout.write(self.style.NOTICE("=== Inicio de Tarea Programada: Actualización de Tasa de Cambio ==="))

        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                rate, updated, msg = sync_company_exchange_rate(company, force=force)
                style = self.style.SUCCESS if updated else self.style.WARNING
                self.stdout.write(style(f"[{company.name}] Resultado: {msg} (Tasa: {rate})"))
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"No se encontró la empresa con ID {company_id}."))
        else:
            results = sync_all_active_companies_exchange_rates(force=force)
            if not results:
                self.stdout.write(self.style.WARNING("No hay empresas activas registradas en el sistema."))
            for res in results:
                comp = res['company']
                style = self.style.SUCCESS if res['updated'] else self.style.WARNING
                self.stdout.write(style(f"- [{comp.name}] {res['message']} (Tasa actual: $1 USD = L {res['rate']} HNL)"))

        self.stdout.write(self.style.NOTICE("=== Tarea Finalizada con Éxito ==="))
