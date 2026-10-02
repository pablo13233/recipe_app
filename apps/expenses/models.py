from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.core.models import Company


class RecurringPayment(models.Model):
    """
    Pagos y servicios recurrentes mensuales (luz, internet, alquiler, suscripciones, etc.)
    para presupuestar el mes y emitir recordatorios de pago.
    """
    CATEGORY_CHOICES = [
        ('services', 'Servicios Públicos (Luz, Agua, Internet, Celular)'),
        ('rent', 'Alquiler y Oficina'),
        ('payroll', 'Sueldos / Salarios / Honorarios'),
        ('supplies', 'Materiales, Insumos y Equipos'),
        ('transport', 'Transporte / Combustible / Mantenimiento Vehicular'),
        ('food', 'Alimentación y Viáticos'),
        ('taxes', 'Impuestos, Tasas y Permisos'),
        ('personal_draw', 'Retiro / Gastos del Propietario'),
        ('marketing', 'Publicidad y Marketing'),
        ('maintenance', 'Mantenimiento y Reparaciones'),
        ('other', 'Otros Gastos Varios'),
    ]

    EXPENSE_TYPE_CHOICES = [
        ('company', 'Gasto de Empresa'),
        ('personal', 'Gasto Personal'),
    ]

    CURRENCY_CHOICES = [
        ('HNL', 'Lempiras (L HNL)'),
        ('USD', 'Dólares ($ USD)'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='recurring_payments',
        verbose_name="Empresa"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Concepto / Servicio",
        help_text="Ej: Energía Eléctrica (Luz), Internet de Oficina, Renta de Local"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='services',
        verbose_name="Categoría"
    )
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        default='company',
        verbose_name="Tipo de Gasto"
    )
    due_day = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Día de Pago en el Mes (1 - 31)"
    )
    currency = models.CharField(
        max_length=5,
        choices=CURRENCY_CHOICES,
        default='HNL',
        verbose_name="Moneda"
    )
    estimated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto Presupuestado / Estimado"
    )
    beneficiary = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Beneficiario / Proveedor",
        help_text="Ej: ENEE, Claro, Arrendador"
    )
    service_code = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="N° de Cuenta / Clave / Contador (Opcional)",
        help_text="Ej: Clave de cliente, N° de contador o contrato"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notas u Observaciones"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago Recurrente / Presupuesto"
        verbose_name_plural = "Pagos Recurrentes & Servicios"
        ordering = ['due_day', 'title']

    def __str__(self):
        return f"{self.title} (Día {self.due_day} - {self.currency} {self.estimated_amount})"

    def get_status_for_month(self, year, month, today=None, current_rate=None):
        """
        Retorna el estado de pago para el mes y año consultados:
        - 'paid': Ya se registró el gasto pagado para este mes
        - 'overdue': Fecha límite superada y sin pagar
        - 'due_today': Vence el día de hoy
        - 'upcoming': Vence dentro de los próximos 5 días
        - 'pending': Pago programado más adelante en el mes
        """
        if today is None:
            today = timezone.localdate()

        rate = current_rate or self.company.default_exchange_rate
        if rate <= Decimal('0.00'):
            rate = Decimal('24.7500')

        # Convertir monto estimado para visualización
        raw_amt = Decimal(str(self.estimated_amount or '0.00'))
        if self.currency == 'USD':
            estimated_usd = raw_amt.quantize(Decimal('0.01'))
            estimated_hnl = (raw_amt * rate).quantize(Decimal('0.01'))
        else:
            estimated_hnl = raw_amt.quantize(Decimal('0.01'))
            estimated_usd = (raw_amt / rate).quantize(Decimal('0.01'))

        # Buscar si existe un gasto registrado para este pago recurrente en este mes
        expense = self.recorded_expenses.filter(
            expense_date__year=year,
            expense_date__month=month
        ).first()

        # Si no está enlazado directamente, buscar por título idéntico en este mes
        if not expense:
            expense = Expense.objects.filter(
                company=self.company,
                expense_date__year=year,
                expense_date__month=month,
                title__iexact=self.title
            ).first()

        if expense:
            return {
                'is_paid': True,
                'status': 'paid',
                'label': 'Pagado',
                'badge_class': 'badge-paid',
                'expense': expense,
                'paid_amount_hnl': expense.amount_hnl,
                'paid_amount_usd': expense.amount_usd,
                'paid_date': expense.expense_date,
                'estimated_hnl': estimated_hnl,
                'estimated_usd': estimated_usd,
                'due_day': self.due_day,
            }

        # No está pagado: evaluar fecha límite
        diff = self.due_day - today.day
        if diff < 0:
            status = 'overdue'
            label = f'Vencido hace {abs(diff)} d'
            badge_class = 'badge-overdue'
        elif diff == 0:
            status = 'due_today'
            label = 'Vence Hoy'
            badge_class = 'badge-due-today'
        elif diff <= 5:
            status = 'upcoming'
            label = f'Vence en {diff} d'
            badge_class = 'badge-info'
        else:
            status = 'pending'
            label = f'Día {self.due_day}'
            badge_class = 'badge-secondary'

        return {
            'is_paid': False,
            'status': status,
            'label': label,
            'badge_class': badge_class,
            'expense': None,
            'paid_amount_hnl': Decimal('0.00'),
            'paid_amount_usd': Decimal('0.00'),
            'paid_date': None,
            'estimated_hnl': estimated_hnl,
            'estimated_usd': estimated_usd,
            'due_day': self.due_day,
        }


class Expense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ('company', 'Gasto de Empresa'),
        ('personal', 'Gasto Personal'),
    ]

    CATEGORY_CHOICES = [
        ('services', 'Servicios Públicos (Luz, Agua, Internet, Celular)'),
        ('rent', 'Alquiler y Oficina'),
        ('payroll', 'Sueldos / Salarios / Honorarios'),
        ('supplies', 'Materiales, Insumos y Equipos'),
        ('transport', 'Transporte / Combustible / Mantenimiento Vehicular'),
        ('food', 'Alimentación y Viáticos'),
        ('taxes', 'Impuestos, Tasas y Permisos'),
        ('personal_draw', 'Retiro / Gastos del Propietario'),
        ('marketing', 'Publicidad y Marketing'),
        ('maintenance', 'Mantenimiento y Reparaciones'),
        ('other', 'Otros Gastos Varios'),
    ]

    CURRENCY_CHOICES = [
        ('HNL', 'Lempiras (L HNL)'),
        ('USD', 'Dólares ($ USD)'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia Bancaria'),
        ('card', 'Tarjeta de Débito / Crédito'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ]

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='expenses',
        verbose_name="Empresa"
    )
    recurring_payment = models.ForeignKey(
        RecurringPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_expenses',
        verbose_name="Pago Recurrente Asociado"
    )
    expense_type = models.CharField(
        max_length=20, 
        choices=EXPENSE_TYPE_CHOICES, 
        default='company',
        verbose_name="Tipo de Gasto"
    )
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='other',
        verbose_name="Categoría"
    )
    title = models.CharField(
        max_length=200, 
        verbose_name="Concepto / Título del Gasto"
    )
    description = models.TextField(
        blank=True, 
        verbose_name="Descripción / Detalle"
    )
    expense_date = models.DateField(
        default=timezone.now, 
        verbose_name="Fecha del Gasto"
    )
    currency = models.CharField(
        max_length=5, 
        choices=CURRENCY_CHOICES, 
        default='HNL',
        verbose_name="Moneda de Origen"
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Monto Registrado"
    )
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Tasa de Cambio (USD -> HNL)"
    )
    amount_hnl = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Equivalente en Lempiras (L)"
    )
    amount_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Equivalente en Dólares ($)"
    )
    beneficiary = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Beneficiario / Proveedor / Comercio"
    )
    payment_method = models.CharField(
        max_length=30, 
        choices=PAYMENT_METHODS, 
        default='cash',
        verbose_name="Método de Pago"
    )
    receipt_voucher = models.FileField(
        upload_to="expense_vouchers/", 
        blank=True, 
        null=True, 
        verbose_name="Comprobante / Foto / Factura"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_expenses',
        verbose_name="Registrado por"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Bitácora de Gastos"
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"[{self.get_expense_type_display()}] {self.title} - {self.currency} {self.amount}"

    def save(self, *args, **kwargs):
        rate = Decimal(str(self.exchange_rate or '24.7500'))
        if rate <= Decimal('0.00'):
            rate = Decimal('24.7500')
        raw_amt = Decimal(str(self.amount or '0.00'))

        if self.currency == 'USD':
            self.amount_usd = raw_amt.quantize(Decimal('0.01'))
            self.amount_hnl = (raw_amt * rate).quantize(Decimal('0.01'))
        else: # HNL
            self.amount_hnl = raw_amt.quantize(Decimal('0.01'))
            self.amount_usd = (raw_amt / rate).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)
