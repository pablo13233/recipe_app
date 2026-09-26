from decimal import Decimal
from django.db import models
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre Comercial")
    legal_name = models.CharField(max_length=250, blank=True, verbose_name="Razón Social / Propietario")
    tax_id = models.CharField(max_length=50, blank=True, verbose_name="RTN / Identificación Fiscal")
    address = models.TextField(blank=True, verbose_name="Dirección")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Teléfono / WhatsApp")
    email = models.EmailField(blank=True, verbose_name="Correo Electrónico")
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True, verbose_name="Logo de la Empresa")
    
    # Configuración de correlativo de recibos
    receipt_prefix = models.CharField(
        max_length=20, 
        blank=True, 
        default="", 
        verbose_name="Prefijo de Recibo (opcional, ej: REC- o vacío)"
    )
    receipt_start_number = models.PositiveIntegerField(
        default=1, 
        verbose_name="Número inicial de recibos (ej: 1 para 0001)"
    )
    receipt_padding = models.PositiveSmallIntegerField(
        default=4, 
        verbose_name="Dígitos de relleno con ceros (ej: 4 genera 0001)"
    )
    receipt_footer_note = models.TextField(
        blank=True, 
        default="Gracias por su pago puntual. Este documento es un comprobante válido.",
        verbose_name="Nota al pie de los recibos"
    )
    
    # Tasa de cambio por defecto para esta empresa
    default_exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=Decimal('24.7500'),
        verbose_name="Tasa de cambio predeterminada (USD -> HNL)"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_next_sequence_number(self):
        """Retorna el próximo número secuencial entero para la empresa."""
        from apps.receipts.models import Receipt
        last_receipt = Receipt.objects.filter(company=self).order_by('-sequence_number').first()
        if not last_receipt:
            return self.receipt_start_number
        return max(last_receipt.sequence_number + 1, self.receipt_start_number)

    def format_receipt_number(self, sequence_num):
        """Formatea el número con ceros a la izquierda y prefijo según configuración."""
        formatted_num = f"{sequence_num:0{self.receipt_padding}d}"
        if self.receipt_prefix:
            return f"{self.receipt_prefix}{formatted_num}"
        return formatted_num

    def get_next_receipt_number_formatted(self):
        """Retorna el próximo número formateado como string (ej: '0001')."""
        return self.format_receipt_number(self.get_next_sequence_number())


class ExchangeRateLog(models.Model):
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    rate_usd_to_hnl = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Tasa USD a HNL"
    )
    source = models.CharField(max_length=50, default='API', verbose_name="Fuente (API / Manual)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Tasa de Cambio"
        verbose_name_plural = "Registros de Tasa de Cambio"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date}: $1 USD = L {self.rate_usd_to_hnl} HNL ({self.source})"
