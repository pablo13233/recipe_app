from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.core.models import Company
from apps.clients.models import Client


class Receipt(models.Model):
    PAYMENT_METHODS = [
        ('transfer', 'Transferencia Bancaria'),
        ('cash', 'Efectivo'),
        ('deposit', 'Depósito Bancario'),
        ('card', 'Tarjeta de Crédito / Débito'),
        ('other', 'Otro Medio'),
    ]

    STATUS_CHOICES = [
        ('paid', 'Emitido / Pagado'),
        ('cancelled', 'Anulado'),
    ]

    MONTH_NAMES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='receipts',
        verbose_name="Empresa"
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT, 
        related_name='receipts',
        null=True,
        blank=True,
        verbose_name="Cliente Registrado"
    )
    external_client_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Empresa / Cliente Externo (No registrado)"
    )
    is_extra_charge = models.BooleanField(
        default=False,
        verbose_name="Es Monto Extra (Fuera del cobro mensual)"
    )
    sequence_number = models.PositiveIntegerField(
        verbose_name="Secuencia Numérica"
    )
    receipt_number = models.CharField(
        max_length=50, 
        verbose_name="Número de Recibo (ej: 0001)"
    )
    issue_date = models.DateField(
        default=timezone.now, 
        verbose_name="Fecha de Emisión"
    )
    billing_month = models.PositiveSmallIntegerField(
        verbose_name="Mes de Cobro (1-12)"
    )
    billing_year = models.PositiveSmallIntegerField(
        verbose_name="Año de Cobro"
    )
    concept = models.CharField(
        max_length=300, 
        verbose_name="Concepto / Detalle del Pago"
    )
    amount_usd = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Monto en Dólares ($ USD)"
    )
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Tasa de Cambio (USD a HNL)"
    )
    amount_hnl = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Monto en Lempiras (L HNL)"
    )
    payment_method = models.CharField(
        max_length=30, 
        choices=PAYMENT_METHODS, 
        default='transfer',
        blank=True,
        verbose_name="Forma de Pago"
    )
    payment_reference = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Referencia / N° de Transacción"
    )
    payment_proof = models.FileField(
        upload_to='receipt_proofs/',
        blank=True,
        null=True,
        verbose_name="Comprobante de Pago (Imagen o PDF)"
    )
    payment_proof_uploaded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Subida del Comprobante"
    )
    notes = models.TextField(
        blank=True, 
        verbose_name="Observaciones"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='paid',
        verbose_name="Estado"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_receipts',
        verbose_name="Emitido por"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"
        ordering = ['-issue_date', '-sequence_number']
        unique_together = ('company', 'sequence_number')

    def __str__(self):
        return f"Recibo #{self.receipt_number} - {self.client_display_name} (L {self.amount_hnl} HNL)"

    @property
    def client_display_name(self):
        if self.client:
            return self.client.name
        return self.external_client_name or "Empresa Externa"

    @property
    def month_display(self):
        return self.MONTH_NAMES.get(self.billing_month, str(self.billing_month))

    @property
    def period_display(self):
        return f"{self.month_display} {self.billing_year}"

    @property
    def is_proof_image(self):
        if not self.payment_proof:
            return False
        name_lower = self.payment_proof.name.lower()
        return name_lower.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))

    def save(self, *args, **kwargs):
        if self.amount_usd and self.exchange_rate:
            self.amount_hnl = (Decimal(str(self.amount_usd)) * Decimal(str(self.exchange_rate))).quantize(Decimal('0.01'))

        if not self.sequence_number:
            self.sequence_number = self.company.get_next_sequence_number()
        
        if not self.receipt_number:
            self.receipt_number = self.company.format_receipt_number(self.sequence_number)

        super().save(*args, **kwargs)


class ExtraIncome(models.Model):
    """
    Registro de ingresos que NO pertenecen al cobro mensual regular:
    1. Ingresos de empresas o clientes externos (no registrados en el directorio, solo como registro de ingreso).
    2. Montos extra fuera de la cuota mensual fija para clientes/empresas registradas.
    """
    SOURCE_TYPES = [
        ('external', 'Empresa / Cliente Externo (No registrado - Solo registro de ingreso)'),
        ('registered', 'Empresa / Cliente Registrado (Monto extra fuera del cobro mensual)'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'Dólares ($ USD)'),
        ('HNL', 'Lempiras (L HNL)'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='extra_incomes',
        verbose_name="Empresa"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default='external',
        verbose_name="Tipo de Origen del Ingreso"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extra_incomes',
        verbose_name="Empresa / Cliente Registrado"
    )
    external_company_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre de Empresa o Cliente Externo (No registrado)"
    )
    income_date = models.DateField(
        default=timezone.now,
        verbose_name="Fecha del Ingreso"
    )
    concept = models.CharField(
        max_length=300,
        verbose_name="Concepto / Descripción del Ingreso"
    )
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='USD',
        verbose_name="Moneda del Monto"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto Ingresado"
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Tasa de Cambio (USD a HNL)"
    )
    amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto en Dólares ($ USD)"
    )
    amount_hnl = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto en Lempiras (L HNL)"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Referencia / N° de Transacción (Opcional)"
    )
    payment_proof = models.FileField(
        upload_to='extra_income_proofs/',
        blank=True,
        null=True,
        verbose_name="Comprobante de Pago (Imagen o PDF)"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observaciones (Opcional)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_extra_incomes',
        verbose_name="Registrado por"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ingreso Extra / Externo"
        verbose_name_plural = "Ingresos Extra / Externos"
        ordering = ['-income_date', '-created_at']

    def __str__(self):
        return f"{self.source_display_name} - {self.concept} (L {self.amount_hnl} HNL)"

    @property
    def source_display_name(self):
        if self.source_type == 'registered' and self.client:
            return self.client.name
        return self.external_company_name or (self.client.name if self.client else "Empresa Externa")

    @property
    def source_badge_label(self):
        if self.source_type == 'registered':
            return "Monto Extra (Cliente Registrado)"
        return "Empresa Externa (No Registrada)"

    @property
    def is_proof_image(self):
        if not self.payment_proof:
            return False
        name_lower = self.payment_proof.name.lower()
        return name_lower.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))

    def save(self, *args, **kwargs):
        val = Decimal(str(self.amount or '0.00'))
        rate = Decimal(str(self.exchange_rate or '24.7500'))
        if rate <= Decimal('0.00'):
            rate = Decimal('24.7500')

        if self.currency == 'USD':
            self.amount_usd = val.quantize(Decimal('0.01'))
            self.amount_hnl = (val * rate).quantize(Decimal('0.01'))
        else:
            self.amount_hnl = val.quantize(Decimal('0.01'))
            self.amount_usd = (val / rate).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

