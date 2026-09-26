from decimal import Decimal
import urllib.parse
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from apps.core.models import Company


class Client(models.Model):
    PAYMENT_PARTS_CHOICES = [
        (1, '1 solo pago al mes (Monto completo)'),
        (2, 'En 2 partes al mes (Dos fechas de cobro)'),
    ]

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='clients',
        verbose_name="Empresa"
    )
    name = models.CharField(max_length=200, verbose_name="Nombre Completo / Cliente")
    tax_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        default="",
        verbose_name="DNI / RTN (Opcional)"
    )
    address = models.TextField(blank=True, verbose_name="Dirección")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Teléfono / WhatsApp")
    email = models.EmailField(blank=True, verbose_name="Correo Electrónico")
    
    # Datos de cobro mensual y división de pagos
    monthly_fee_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Cobro Mensual Total ($ USD)"
    )
    payment_parts = models.PositiveSmallIntegerField(
        choices=PAYMENT_PARTS_CHOICES,
        default=1,
        verbose_name="Modalidad de Pago"
    )
    billing_day = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Día del 1er Cobro (1 - 31)"
    )
    first_payment_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        verbose_name="Monto 1er Pago ($ USD)"
    )
    second_billing_day = models.PositiveSmallIntegerField(
        default=30,
        blank=True,
        null=True,
        verbose_name="Día del 2do Cobro (1 - 31)"
    )
    second_payment_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        verbose_name="Monto 2do Pago ($ USD)"
    )
    default_concept = models.CharField(
        max_length=250, 
        default="Cuota mensual de servicio",
        verbose_name="Concepto de cobro predeterminado"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    notes = models.TextField(blank=True, verbose_name="Notas u Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']

    def __str__(self):
        if self.payment_parts == 2:
            return f"{self.name} (${self.monthly_fee_usd} USD en 2 pagos)"
        return f"{self.name} (${self.monthly_fee_usd} USD)"

    def save(self, *args, **kwargs):
        total = Decimal(str(self.monthly_fee_usd or '0.00')).quantize(Decimal('0.01'))
        self.monthly_fee_usd = total

        if self.payment_parts == 1:
            self.first_payment_usd = total
            self.second_payment_usd = Decimal('0.00')
        else:
            first = Decimal(str(self.first_payment_usd or '0.00')).quantize(Decimal('0.01'))
            second = Decimal(str(self.second_payment_usd or '0.00')).quantize(Decimal('0.01'))

            if first <= Decimal('0.00') or first >= total:
                first = (total / Decimal('2')).quantize(Decimal('0.01'))
                second = (total - first).quantize(Decimal('0.01'))
            elif second <= Decimal('0.00') or (first + second != total):
                second = max(Decimal('0.00'), (total - first).quantize(Decimal('0.01')))

            self.first_payment_usd = first
            self.second_payment_usd = second

            if not self.second_billing_day:
                self.second_billing_day = min(30, self.billing_day + 15)

        super().save(*args, **kwargs)

    def get_paid_amount_for_period(self, year, month):
        """Suma el monto en USD de los recibos de cobro mensual (excluyendo cobros extra) en el mes y año dados."""
        total = self.receipts.filter(
            billing_year=year,
            billing_month=month,
            status='paid',
            is_extra_charge=False
        ).aggregate(total_usd=Sum('amount_usd'))['total_usd']
        return (total or Decimal('0.00')).quantize(Decimal('0.01'))

    def get_remaining_balance_for_period(self, year, month):
        """Retorna el saldo en USD que le falta pagar al cliente en el mes y año dados."""
        paid = self.get_paid_amount_for_period(year, month)
        remaining = self.monthly_fee_usd - paid
        return max(Decimal('0.00'), remaining.quantize(Decimal('0.01')))

    def has_paid_for_period(self, year, month):
        """
        Verifica si el cliente ya cubrió la totalidad de su cuota mensual para el periodo.
        """
        paid = self.get_paid_amount_for_period(year, month)
        if self.monthly_fee_usd > Decimal('0.00'):
            return paid >= self.monthly_fee_usd
        return self.receipts.filter(
            billing_year=year,
            billing_month=month,
            status='paid',
            is_extra_charge=False
        ).exists()

    def get_receipt_for_period(self, year, month):
        """Retorna el último recibo emitido para el periodo indicado."""
        return self.receipts.filter(
            billing_year=year,
            billing_month=month,
            status='paid'
        ).order_by('-sequence_number').first()

    def get_receipts_for_period(self, year, month):
        """Retorna todos los recibos pagados del cliente en ese periodo."""
        return self.receipts.filter(
            billing_year=year,
            billing_month=month,
            status='paid'
        ).order_by('sequence_number')

    def get_next_payment_suggestion(self, year, month):
        """
        Calcula cuál es el monto sugerido y concepto para el próximo recibo del mes,
        tomando en cuenta si paga en 2 partes o si ya realizó un abono parcial.
        """
        paid_usd = self.get_paid_amount_for_period(year, month)
        remaining_usd = self.get_remaining_balance_for_period(year, month)

        if self.payment_parts == 2:
            if paid_usd == Decimal('0.00'):
                return {
                    'suggested_usd': self.first_payment_usd,
                    'part_label': '1er Pago',
                    'target_day': self.billing_day,
                    'paid_usd': paid_usd,
                    'remaining_usd': remaining_usd,
                }
            elif remaining_usd > Decimal('0.00'):
                return {
                    'suggested_usd': remaining_usd,
                    'part_label': '2do Pago',
                    'target_day': self.second_billing_day or self.billing_day,
                    'paid_usd': paid_usd,
                    'remaining_usd': remaining_usd,
                }
            else:
                return {
                    'suggested_usd': self.first_payment_usd,
                    'part_label': 'Pago Adicional',
                    'target_day': self.billing_day,
                    'paid_usd': paid_usd,
                    'remaining_usd': Decimal('0.00'),
                }
        else:
            if paid_usd > Decimal('0.00') and remaining_usd > Decimal('0.00'):
                return {
                    'suggested_usd': remaining_usd,
                    'part_label': 'Saldo Restante',
                    'target_day': self.billing_day,
                    'paid_usd': paid_usd,
                    'remaining_usd': remaining_usd,
                }
            return {
                'suggested_usd': self.monthly_fee_usd,
                'part_label': 'Pago Mensual',
                'target_day': self.billing_day,
                'paid_usd': paid_usd,
                'remaining_usd': remaining_usd,
            }

    def get_reminder_status(self, today=None):
        """
        Retorna el estado de cobro para el mes actual considerando pagos en 1 o 2 partes:
        - 'paid': Ya pagó el 100% del mes actual
        - 'overdue': La fecha del cobro actual (1ra o 2da parte) ya pasó
        - 'due_today': El cobro actual (1ra o 2da parte) vence hoy
        - 'upcoming': Faltan 5 días o menos para el próximo cobro del mes
        - 'pending': Cobro pendiente más adelante en el mes
        """
        if today is None:
            today = timezone.localdate()

        paid_usd = self.get_paid_amount_for_period(today.year, today.month)
        remaining_usd = self.get_remaining_balance_for_period(today.year, today.month)
        last_receipt = self.get_receipt_for_period(today.year, today.month)

        if self.has_paid_for_period(today.year, today.month):
            return {
                'status': 'paid',
                'label': 'Pagado Completo',
                'badge_class': 'badge-success',
                'receipt': last_receipt,
                'days_diff': 0,
                'billing_day': self.billing_day,
                'paid_usd': paid_usd,
                'remaining_usd': Decimal('0.00'),
                'next_amount_usd': Decimal('0.00'),
                'is_partial': False,
                'part_label': 'Completo',
            }

        suggestion = self.get_next_payment_suggestion(today.year, today.month)
        target_day = suggestion['target_day']
        part_label = suggestion['part_label']
        is_partial = paid_usd > Decimal('0.00')
        prefix = f"{part_label}: " if (self.payment_parts == 2 or is_partial) else ""

        diff = target_day - today.day
        if diff < 0:
            return {
                'status': 'overdue',
                'label': f'{prefix}Vencido ({abs(diff)} d)',
                'badge_class': 'badge-danger',
                'receipt': last_receipt,
                'days_diff': diff,
                'billing_day': target_day,
                'paid_usd': paid_usd,
                'remaining_usd': remaining_usd,
                'next_amount_usd': suggestion['suggested_usd'],
                'is_partial': is_partial,
                'part_label': part_label,
            }
        elif diff == 0:
            return {
                'status': 'due_today',
                'label': f'{prefix}Vence Hoy',
                'badge_class': 'badge-warning',
                'receipt': last_receipt,
                'days_diff': 0,
                'billing_day': target_day,
                'paid_usd': paid_usd,
                'remaining_usd': remaining_usd,
                'next_amount_usd': suggestion['suggested_usd'],
                'is_partial': is_partial,
                'part_label': part_label,
            }
        elif diff <= 5:
            return {
                'status': 'upcoming',
                'label': f'{prefix}Próximo en {diff} d',
                'badge_class': 'badge-info',
                'receipt': last_receipt,
                'days_diff': diff,
                'billing_day': target_day,
                'paid_usd': paid_usd,
                'remaining_usd': remaining_usd,
                'next_amount_usd': suggestion['suggested_usd'],
                'is_partial': is_partial,
                'part_label': part_label,
            }
        else:
            return {
                'status': 'pending',
                'label': f'{prefix}Día {target_day}',
                'badge_class': 'badge-secondary',
                'receipt': last_receipt,
                'days_diff': diff,
                'billing_day': target_day,
                'paid_usd': paid_usd,
                'remaining_usd': remaining_usd,
                'next_amount_usd': suggestion['suggested_usd'],
                'is_partial': is_partial,
                'part_label': part_label,
            }

    def get_clean_phone(self):
        """Limpia caracteres no numéricos del teléfono para enlaces de WhatsApp."""
        if not self.phone:
            return ""
        clean = "".join([c for c in self.phone if c.isdigit()])
        if len(clean) == 8:
            clean = f"504{clean}"
        return clean

    def get_whatsapp_reminder_url(self, exchange_rate=None):
        phone = self.get_clean_phone()
        if not phone:
            return None
        
        today = timezone.localdate()
        suggestion = self.get_next_payment_suggestion(today.year, today.month)
        due_usd = suggestion['suggested_usd']
        part_label = suggestion['part_label']

        rate = exchange_rate or self.company.default_exchange_rate
        approx_hnl = (due_usd * rate).quantize(Decimal('0.01'))
        
        if self.payment_parts == 2 or suggestion['paid_usd'] > 0:
            msg = (
                f"Hola {self.name}, un cordial saludo de parte de {self.company.name}. "
                f"Le recordamos su {part_label} de {self.default_concept} por valor de "
                f"${due_usd:,.2f} USD (aprox. L {approx_hnl:,.2f} HNL). "
                f"Quedamos a su disposición. ¡Muchas gracias!"
            )
        else:
            msg = (
                f"Hola {self.name}, un cordial saludo de parte de {self.company.name}. "
                f"Le recordamos su cuota mensual de {self.default_concept} por valor de "
                f"${due_usd:,.2f} USD (aprox. L {approx_hnl:,.2f} HNL). "
                f"Quedamos a su disposición. ¡Muchas gracias!"
            )
        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{phone}?text={encoded}"
