from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.core.models import Company


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
        # Auto-conversión a ambas monedas
        rate = Decimal(str(self.exchange_rate))
        raw_amt = Decimal(str(self.amount))

        if self.currency == 'USD':
            self.amount_usd = raw_amt.quantize(Decimal('0.01'))
            self.amount_hnl = (raw_amt * rate).quantize(Decimal('0.01'))
        else: # HNL
            self.amount_hnl = raw_amt.quantize(Decimal('0.01'))
            if rate > 0:
                self.amount_usd = (raw_amt / rate).quantize(Decimal('0.01'))
            else:
                self.amount_usd = Decimal('0.00')

        super().save(*args, **kwargs)
