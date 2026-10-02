from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from apps.core.models import Company
from apps.employees.models import CompanyMembership
from apps.clients.models import Client
from apps.receipts.models import Receipt, ExtraIncome
from apps.expenses.models import Expense


class RecipeAppIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.company = Company.objects.create(
            name='Empresa Test',
            tax_id='08019999888877',
            receipt_start_number=1,
            receipt_padding=4,
            default_exchange_rate=Decimal('24.8000')
        )
        CompanyMembership.objects.create(
            user=self.user,
            company=self.company,
            role='admin',
            is_default=True
        )
        self.client_model = Client.objects.create(
            company=self.company,
            name='Cliente Ejemplo',
            monthly_fee_usd=Decimal('100.00'),
            billing_day=5,
            default_concept='Servicio Mensual'
        )
        self.http_client = TestClient()

    def test_public_landing_and_login_pages(self):
        resp_landing = self.http_client.get(reverse('landing'))
        self.assertEqual(resp_landing.status_code, 200)
        self.assertContains(resp_landing, 'RecipeApp')

        resp_login = self.http_client.get(reverse('login'))
        self.assertEqual(resp_login.status_code, 200)

    def test_automatic_receipt_numbering_and_currency_conversion(self):
        today = timezone.localdate()
        r1 = Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Pago Mes 1',
            amount_usd=Decimal('100.00'),
            exchange_rate=Decimal('24.8000'),
            created_by=self.user
        )
        self.assertEqual(r1.receipt_number, '0001')
        self.assertEqual(r1.amount_hnl, Decimal('2480.00'))

        r2 = Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Pago Mes 2',
            amount_usd=Decimal('50.00'),
            exchange_rate=Decimal('25.0000'),
            created_by=self.user
        )
        self.assertEqual(r2.receipt_number, '0002')
        self.assertEqual(r2.amount_hnl, Decimal('1250.00'))

    def test_receipt_displays_only_hnl_without_signatures_and_supports_payment_proof(self):
        today = timezone.localdate()
        r1 = Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Cuota Mensual',
            amount_usd=Decimal('100.00'),
            exchange_rate=Decimal('24.8000'),
            created_by=self.user
        )
        self.http_client.login(username='testuser', password='password123')
        self.http_client.get(reverse('dashboard'))

        resp_detail = self.http_client.get(reverse('receipt_detail', args=[r1.id]))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, '2480.00')
        self.assertNotContains(resp_detail, 'MÉTODO DE PAGO:')
        self.assertNotContains(resp_detail, 'Firma y Sello Autorizado')
        self.assertContains(resp_detail, 'Agregar Comprobante')

        # Subir comprobante de pago
        fake_proof = SimpleUploadedFile("comprobante.png", b"fake-image-content", content_type="image/png")
        resp_upload = self.http_client.post(
            reverse('receipt_upload_proof', args=[r1.id]),
            {'payment_proof': fake_proof, 'payment_reference': 'TRF-998877'}
        )
        self.assertEqual(resp_upload.status_code, 302)
        r1.refresh_from_db()
        self.assertTrue(bool(r1.payment_proof))
        self.assertTrue(r1.is_proof_image)
        self.assertEqual(r1.payment_reference, 'TRF-998877')

        resp_detail_after = self.http_client.get(reverse('receipt_detail', args=[r1.id]))
        self.assertContains(resp_detail_after, 'Ver Comprobante')

    def test_extra_incomes_for_unregistered_companies_and_registered_clients(self):
        today = timezone.localdate()
        self.http_client.login(username='testuser', password='password123')
        self.http_client.get(reverse('dashboard'))

        # 1. Ingreso de empresa NO registrada (solo como registro de ingreso)
        resp_ext = self.http_client.post(reverse('extra_income_create'), {
            'source_type': 'external',
            'external_company_name': 'Inversiones del Norte S.A.',
            'income_date': today.strftime('%Y-%m-%d'),
            'concept': 'Consultoría externa puntual',
            'currency': 'USD',
            'amount': '150.00',
            'exchange_rate': '25.0000',
            'payment_reference': 'DEP-111',
            'notes': 'Empresa no registrada en cobro mensual',
        })
        self.assertEqual(resp_ext.status_code, 302)

        # 2. Monto extra fuera del cobro mensual para un cliente registrado
        resp_reg = self.http_client.post(reverse('extra_income_create'), {
            'source_type': 'registered',
            'client': self.client_model.id,
            'income_date': today.strftime('%Y-%m-%d'),
            'concept': 'Módulo adicional fuera de iguala',
            'currency': 'HNL',
            'amount': '2500.00',
            'exchange_rate': '25.0000',
            'payment_reference': 'TRF-222',
            'notes': 'No debe afectar su cobro mensual fijo',
        })
        self.assertEqual(resp_reg.status_code, 302)

        self.assertEqual(ExtraIncome.objects.count(), 2)

        # Verificar que el cliente registrado sigue teniendo $0.00 abonado a su cuota mensual fija
        self.assertFalse(self.client_model.has_paid_for_period(today.year, today.month))
        self.assertEqual(self.client_model.get_paid_amount_for_period(today.year, today.month), Decimal('0.00'))

        # También si se emite un recibo marcado como is_extra_charge=True no afecta la cuota mensual
        Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            is_extra_charge=True,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Soporte Extra',
            amount_usd=Decimal('100.00'),
            exchange_rate=Decimal('25.0000'),
            created_by=self.user
        )
        self.assertFalse(self.client_model.has_paid_for_period(today.year, today.month))

        # Verificar que la vista de listado de ingresos extra muestra ambos registros
        resp_list = self.http_client.get(reverse('extra_income_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Inversiones del Norte S.A.')
        self.assertContains(resp_list, 'Módulo adicional fuera de iguala')

    def test_two_part_client_payment_flow_and_no_rtn_in_receipt(self):
        today = timezone.localdate()
        split_client = Client.objects.create(
            company=self.company,
            name='Cliente Dos Partes',
            tax_id='08011990112233',
            monthly_fee_usd=Decimal('600.00'),
            payment_parts=2,
            billing_day=15,
            first_payment_usd=Decimal('300.00'),
            second_billing_day=30,
            second_payment_usd=Decimal('300.00'),
        )
        self.assertEqual(split_client.first_payment_usd, Decimal('300.00'))
        self.assertEqual(split_client.second_payment_usd, Decimal('300.00'))
        self.assertFalse(split_client.has_paid_for_period(today.year, today.month))

        sug1 = split_client.get_next_payment_suggestion(today.year, today.month)
        self.assertEqual(sug1['suggested_usd'], Decimal('300.00'))
        self.assertEqual(sug1['part_label'], '1er Pago')

        r_part1 = Receipt.objects.create(
            company=self.company,
            client=split_client,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Cuota (1er Pago)',
            amount_usd=Decimal('300.00'),
            exchange_rate=Decimal('24.8000'),
            created_by=self.user
        )
        self.assertFalse(split_client.has_paid_for_period(today.year, today.month))
        self.assertEqual(split_client.get_paid_amount_for_period(today.year, today.month), Decimal('300.00'))
        self.assertEqual(split_client.get_remaining_balance_for_period(today.year, today.month), Decimal('300.00'))

        sug2 = split_client.get_next_payment_suggestion(today.year, today.month)
        self.assertEqual(sug2['suggested_usd'], Decimal('300.00'))
        self.assertEqual(sug2['part_label'], '2do Pago')
        self.assertEqual(sug2['target_day'], 30)

        self.http_client.login(username='testuser', password='password123')
        self.http_client.get(reverse('dashboard'))
        resp_detail = self.http_client.get(reverse('receipt_detail', args=[r_part1.id]))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertNotContains(resp_detail, '08011990112233')
        self.assertNotContains(resp_detail, '08019999888877')

        Receipt.objects.create(
            company=self.company,
            client=split_client,
            issue_date=today,
            billing_month=today.month,
            billing_year=today.year,
            concept='Cuota (2do Pago)',
            amount_usd=Decimal('300.00'),
            exchange_rate=Decimal('24.8000'),
            created_by=self.user
        )
        self.assertTrue(split_client.has_paid_for_period(today.year, today.month))
        self.assertEqual(split_client.get_remaining_balance_for_period(today.year, today.month), Decimal('0.00'))

    def test_custom_start_receipt_number(self):
        comp2 = Company.objects.create(
            name='Empresa 50',
            receipt_start_number=50,
            receipt_padding=4,
            default_exchange_rate=Decimal('24.7500')
        )
        self.assertEqual(comp2.get_next_receipt_number_formatted(), '0050')

    def test_authenticated_views_and_pdf_generation(self):
        self.http_client.login(username='testuser', password='password123')
        resp_dash = self.http_client.get(reverse('dashboard'))
        self.assertEqual(resp_dash.status_code, 200)

        today = timezone.localdate()
        resp_create = self.http_client.post(reverse('receipt_create'), {
            'client': self.client_model.id,
            'issue_date': today.strftime('%Y-%m-%d'),
            'billing_month': today.month,
            'billing_year': today.year,
            'concept': 'Cuota de Prueba',
            'amount_usd': '100.00',
            'exchange_rate': '24.8000',
            'amount_hnl': '2480.00',
            'notes': ''
        })
        self.assertEqual(resp_create.status_code, 302)
        receipt = Receipt.objects.first()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.receipt_number, '0001')

        resp_pdf = self.http_client.get(reverse('receipt_pdf', args=[receipt.id]))
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf['Content-Type'], 'application/pdf')

        resp_m_pdf = self.http_client.get(reverse('receipt_monthly_pdf'))
        self.assertEqual(resp_m_pdf.status_code, 200)
        self.assertEqual(resp_m_pdf['Content-Type'], 'application/pdf')

        Expense.objects.create(
            company=self.company,
            expense_type='company',
            category='services',
            title='Internet',
            expense_date=today,
            currency='HNL',
            amount=Decimal('1000.00'),
            exchange_rate=Decimal('24.8000')
        )
        resp_fin_pdf = self.http_client.get(reverse('expense_financial_pdf'))
        self.assertEqual(resp_fin_pdf.status_code, 200)
        self.assertEqual(resp_fin_pdf['Content-Type'], 'application/pdf')

    def test_rollover_balance_from_previous_months(self):
        """Verifica que el sobrante positivo de meses anteriores entra al balance del mes siguiente."""
        import datetime
        from apps.core.services import get_month_financial_summary

        # Configurar saldo inicial opcional en la empresa
        self.company.initial_balance_hnl = Decimal('1000.00')
        self.company.initial_balance_usd = Decimal('40.00')
        self.company.save()

        # En enero (mes 1): Cobro de recibo L 5000 y Gasto L 2000 -> Sobrante neto del mes = +L 3000
        Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            issue_date=datetime.date(2026, 1, 10),
            billing_month=1,
            billing_year=2026,
            concept='Servicio Enero',
            amount_usd=Decimal('200.00'),
            exchange_rate=Decimal('25.0000'), # L 5000
            created_by=self.user
        )
        Expense.objects.create(
            company=self.company,
            expense_type='company',
            category='services',
            title='Gasto Enero',
            expense_date=datetime.date(2026, 1, 15),
            currency='HNL',
            amount=Decimal('2000.00'),
            exchange_rate=Decimal('25.0000')
        )

        # En febrero (mes 2):
        # El saldo inicial arrastrado debe ser: 1000 (saldo base) + 5000 (ingresos enero) - 2000 (gastos enero) = L 4000.00
        summary_feb = get_month_financial_summary(self.company, 2026, 2)
        self.assertEqual(summary_feb['rollover_balance_hnl'], Decimal('4000.00'))

        # En febrero se reciben L 3000 y se gastan L 1000
        Receipt.objects.create(
            company=self.company,
            client=self.client_model,
            issue_date=datetime.date(2026, 2, 5),
            billing_month=2,
            billing_year=2026,
            concept='Servicio Febrero',
            amount_usd=Decimal('120.00'),
            exchange_rate=Decimal('25.0000'), # L 3000
            created_by=self.user
        )
        Expense.objects.create(
            company=self.company,
            expense_type='company',
            category='services',
            title='Gasto Febrero',
            expense_date=datetime.date(2026, 2, 10),
            currency='HNL',
            amount=Decimal('1000.00'),
            exchange_rate=Decimal('25.0000')
        )

        # Recalcular febrero
        summary_feb = get_month_financial_summary(self.company, 2026, 2)
        self.assertEqual(summary_feb['rollover_balance_hnl'], Decimal('4000.00'))
        self.assertEqual(summary_feb['month_income_hnl'], Decimal('3000.00'))
        self.assertEqual(summary_feb['total_available_hnl'], Decimal('7000.00')) # 4000 + 3000
        self.assertEqual(summary_feb['total_expenses_hnl'], Decimal('1000.00'))
        self.assertEqual(summary_feb['ending_balance_hnl'], Decimal('6000.00')) # 7000 - 1000

        # En marzo (mes 3), el sobrante arrastrado debe ser exactamente L 6000.00
        summary_mar = get_month_financial_summary(self.company, 2026, 3)
        self.assertEqual(summary_mar['rollover_balance_hnl'], Decimal('6000.00'))

    def test_recurring_payments_lifecycle_and_budgeting(self):
        """Verifica la configuración, monitoreo y pago de servicios recurrentes (luz, internet, etc.)."""
        import datetime
        from apps.expenses.models import RecurringPayment

        rec_payment = RecurringPayment.objects.create(
            company=self.company,
            title='Energía Eléctrica ENEE',
            category='services',
            expense_type='company',
            due_day=15,
            currency='HNL',
            estimated_amount=Decimal('1500.00'),
            beneficiary='ENEE',
            service_code='CLAVE-123456'
        )

        # Status antes de pagar
        status_before = rec_payment.get_status_for_month(2026, 3, today=datetime.date(2026, 3, 10))
        self.assertFalse(status_before['is_paid'])
        self.assertEqual(status_before['status'], 'upcoming') # Faltan 5 días para el día 15

        # Registrar el pago como gasto enlazado
        Expense.objects.create(
            company=self.company,
            recurring_payment=rec_payment,
            title='Pago Energía Eléctrica ENEE (Marzo 2026)',
            category='services',
            expense_type='company',
            expense_date=datetime.date(2026, 3, 12),
            currency='HNL',
            amount=Decimal('1480.00'),
            exchange_rate=Decimal('24.8000')
        )

        # Status después de pagar
        status_after = rec_payment.get_status_for_month(2026, 3, today=datetime.date(2026, 3, 12))
        self.assertTrue(status_after['is_paid'])
        self.assertEqual(status_after['status'], 'paid')
        self.assertEqual(status_after['paid_amount_hnl'], Decimal('1480.00'))

        # Probar vistas de pagos recurrentes
        self.http_client.login(username='testuser', password='password123')
        self.http_client.get(reverse('dashboard'))

        resp_list = self.http_client.get(reverse('recurring_payment_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Energía Eléctrica ENEE')

        resp_reminders = self.http_client.get(reverse('reminders'))
        self.assertEqual(resp_reminders.status_code, 200)
        self.assertContains(resp_reminders, 'Energía Eléctrica ENEE')

    def test_exchange_rate_configuration_and_live_test_endpoint(self):
        """Verifica la configuración de API de divisas y el endpoint de prueba."""
        self.http_client.login(username='testuser', password='password123')
        session = self.http_client.session
        session['active_company_id'] = self.company.id
        session.save()

        # 1. Verificar guardado de configuración de API en Company
        edit_url = reverse('company_edit', kwargs={'pk': self.company.pk})
        post_data = {
            'name': 'Empresa Test con API',
            'legal_name': self.company.legal_name,
            'tax_id': '08019999888877',
            'address': self.company.address,
            'phone': self.company.phone,
            'email': self.company.email,
            'receipt_start_number': 1,
            'receipt_padding': 4,
            'receipt_footer_note': 'Nota de prueba',
            'default_exchange_rate': '24.9500',
            'exchange_rate_api_url': 'https://v6.exchangerate-api.com/v6/{api_key}/latest/USD',
            'exchange_rate_api_key': 'test-fake-key-123',
            'exchange_rate_auto_update': True,
            'initial_balance_hnl': '500.00',
            'initial_balance_usd': '50.00',
            'is_active': True,
        }
        resp = self.http_client.post(edit_url, post_data)
        self.assertEqual(resp.status_code, 302)

        self.company.refresh_from_db()
        self.assertEqual(self.company.exchange_rate_api_url, 'https://v6.exchangerate-api.com/v6/{api_key}/latest/USD')
        self.assertEqual(self.company.exchange_rate_api_key, 'test-fake-key-123')
        self.assertTrue(self.company.exchange_rate_auto_update)
        self.assertEqual(self.company.default_exchange_rate, Decimal('24.9500'))

        # 2. Verificar llamada al endpoint AJAX de prueba (test_exchange_rate_api)
        test_url = reverse('test_exchange_rate_api')
        # Probar con endpoint simulado o URL
        resp_test = self.http_client.post(test_url, {
            'api_url': 'https://open.er-api.com/v6/latest/USD',
            'api_key': ''
        })
        self.assertEqual(resp_test.status_code, 200)
        json_data = resp_test.json()
        self.assertIn('success', json_data)

        # 3. Probar que al emitir recibo con tasa manual específica, se guarda exactamente esa tasa
        receipt_post = {
            'client': self.client_model.id,
            'issue_date': timezone.localdate(),
            'billing_month': 5,
            'billing_year': 2026,
            'concept': 'Cobro con tasa manual personalizada',
            'amount_usd': '100.00',
            'exchange_rate': '25.1234',  # Tasa manual diferente
            'amount_hnl': '2512.34',
        }
        resp_receipt = self.http_client.post(reverse('receipt_create'), receipt_post)
        self.assertEqual(resp_receipt.status_code, 302)

        created_receipt = Receipt.objects.get(concept='Cobro con tasa manual personalizada')
        self.assertEqual(created_receipt.exchange_rate, Decimal('25.1234'))
        self.assertEqual(created_receipt.amount_hnl, Decimal('2512.34'))



