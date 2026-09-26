from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.core.models import Company, ExchangeRateLog
from apps.employees.models import CompanyMembership, EmployeeProfile
from apps.clients.models import Client
from apps.receipts.models import Receipt
from apps.expenses.models import Expense


class Command(BaseCommand):
    help = "Inicializa usuario administrador, empresa de ejemplo, clientes, recibos y gastos."

    def handle(self, *args, **options):
        today = timezone.localdate()

        # 1. Crear o recuperar superusuario admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Administrador',
                'last_name': 'General',
                'email': 'admin@recipeapp.hn',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin1234')
            admin_user.save()
            EmployeeProfile.objects.get_or_create(
                user=admin_user,
                defaults={'job_title': 'Director General', 'phone': '+504 9999-0000'}
            )
            self.stdout.write(self.style.SUCCESS("Superusuario 'admin' (contraseña: admin1234) creado."))
        else:
            self.stdout.write("Usuario 'admin' ya existe.")

        # 2. Tasa de cambio inicial
        rate = Decimal('24.7850')
        ExchangeRateLog.objects.get_or_create(
            date=today,
            defaults={'rate_usd_to_hnl': rate, 'source': 'Inicial'}
        )

        # 3. Crear empresa principal si no existe
        company, comp_created = Company.objects.get_or_create(
            name='Soluciones Digitales HN',
            defaults={
                'legal_name': 'Inversiones y Servicios Digitales S. de R.L.',
                'tax_id': '08011995123456',
                'address': 'Col. Palmira, Blvd. Morazán, Tegucigalpa, Honduras',
                'phone': '+504 2233-4455',
                'email': 'facturacion@solucioneshn.com',
                'receipt_prefix': '',
                'receipt_start_number': 1,
                'receipt_padding': 4,
                'default_exchange_rate': rate,
            }
        )
        CompanyMembership.objects.get_or_create(
            user=admin_user,
            company=company,
            defaults={'role': 'admin', 'is_default': True}
        )

        # 4. Crear segunda empresa de ejemplo para probar multi-empresa
        company2, _ = Company.objects.get_or_create(
            name='Inmobiliaria & Alquileres del Valle',
            defaults={
                'legal_name': 'Bienes Raíces del Valle S.A.',
                'tax_id': '05011998654321',
                'address': 'Barrio Río de Piedras, San Pedro Sula, Cortés',
                'phone': '+504 9876-5432',
                'email': 'cobros@inmobiliariavalle.hn',
                'receipt_prefix': 'REC-',
                'receipt_start_number': 101,
                'receipt_padding': 4,
                'default_exchange_rate': rate,
            }
        )
        CompanyMembership.objects.get_or_create(
            user=admin_user,
            company=company2,
            defaults={'role': 'admin', 'is_default': False}
        )

        # 5. Clientes de ejemplo en la empresa principal
        clients_seed = [
            {
                'name': 'Comercial La Económica S.A.',
                'tax_id': '08019001122334',
                'address': 'Comayagüela, 4ta Avenida',
                'phone': '+504 9988-7766',
                'email': 'pagos@laeconomica.hn',
                'monthly_fee_usd': Decimal('150.00'),
                'billing_day': 5,
                'default_concept': 'Servicio de Soporte y Mantenimiento Mensual',
                'paid_this_month': True,
            },
            {
                'name': 'Farmacia San Rafael',
                'tax_id': '08019005544332',
                'address': 'Blvd. Suyapa, frente a UNAH',
                'phone': '+504 9911-2233',
                'email': 'admin@farmaciasanrafael.hn',
                'monthly_fee_usd': Decimal('85.00'),
                'billing_day': 10,
                'default_concept': 'Suscripción Mensual Sistema de Inventario',
                'paid_this_month': True,
            },
            {
                'name': 'Restaurante El Patio Catracho',
                'tax_id': '08019009988776',
                'address': 'Col. Lomas del Guijarro',
                'phone': '+504 9765-4321',
                'email': 'contabilidad@elpatiuhn.com',
                'monthly_fee_usd': Decimal('120.00'),
                'billing_day': max(1, today.day - 3),  # Vencido para mostrar alerta
                'default_concept': 'Mensualidad de Hosting y Facturación',
                'paid_this_month': False,
            },
            {
                'name': 'Clínica Dental Sonrisa Feliz',
                'tax_id': '08011988001122',
                'address': 'Edificio Metrópolis, Torre 1, Piso 4',
                'phone': '+504 9555-8899',
                'email': 'info@sonrisafeliz.hn',
                'monthly_fee_usd': Decimal('60.00'),
                'billing_day': today.day,  # Vence hoy
                'default_concept': 'Mantenimiento Mensual de Agenda Médica',
                'paid_this_month': False,
            },
        ]

        month_name = Receipt.MONTH_NAMES.get(today.month, '')

        for c_data in clients_seed:
            paid_flag = c_data.pop('paid_this_month')
            client, _ = Client.objects.get_or_create(
                company=company,
                name=c_data['name'],
                defaults=c_data
            )
            if paid_flag and not Receipt.objects.filter(company=company, client=client, billing_year=today.year, billing_month=today.month).exists():
                Receipt.objects.create(
                    company=company,
                    client=client,
                    issue_date=today,
                    billing_month=today.month,
                    billing_year=today.year,
                    concept=f"{client.default_concept} - {month_name} {today.year}",
                    amount_usd=client.monthly_fee_usd,
                    exchange_rate=rate,
                    payment_method='transfer',
                    payment_reference=f"TRF-{client.id}0982",
                    created_by=admin_user,
                    status='paid'
                )

        # 6. Gastos de ejemplo (Empresa vs Personales)
        if not Expense.objects.filter(company=company).exists():
            Expense.objects.create(
                company=company,
                expense_type='company',
                category='services',
                title='Pago de Internet Fibra Óptica y Servidores',
                description='Factura mensual de conectividad de la oficina',
                expense_date=today,
                currency='HNL',
                amount=Decimal('1650.00'),
                exchange_rate=rate,
                beneficiary='Cable Color / Hondutel',
                payment_method='transfer',
                created_by=admin_user,
            )
            Expense.objects.create(
                company=company,
                expense_type='company',
                category='supplies',
                title='Licencias Cloud y Dominios',
                description='Renovación mensual de servidores cloud',
                expense_date=today,
                currency='USD',
                amount=Decimal('35.00'),
                exchange_rate=rate,
                beneficiary='DigitalOcean / AWS',
                payment_method='card',
                created_by=admin_user,
            )
            Expense.objects.create(
                company=company,
                expense_type='personal',
                category='personal_draw',
                title='Compra de Supermercado Familiar',
                description='Gasto personal registrado en bitácora',
                expense_date=today,
                currency='HNL',
                amount=Decimal('1200.00'),
                exchange_rate=rate,
                beneficiary='Supermercados La Colonia',
                payment_method='card',
                created_by=admin_user,
            )

        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados exitosamente."))
