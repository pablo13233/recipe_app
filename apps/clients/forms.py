from decimal import Decimal
from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name', 'tax_id', 'address', 'phone', 'email',
            'monthly_fee_usd', 'payment_parts',
            'billing_day', 'first_payment_usd',
            'second_billing_day', 'second_payment_usd',
            'default_concept', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Completo o Cliente'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional (no requerido)'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección (Opcional)'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. +504 9999-9999'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'cliente@correo.com'}),
            'monthly_fee_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_monthly_fee_usd'}),
            'payment_parts': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_parts'}),
            'billing_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31, 'id': 'id_billing_day'}),
            'first_payment_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_first_payment_usd'}),
            'second_billing_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31, 'id': 'id_second_billing_day'}),
            'second_payment_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_second_payment_usd'}),
            'default_concept': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Cuota mensual de servicio'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Detalles adicionales, recordatorios, etc.'}),
        }
        labels = {
            'tax_id': 'DNI / RTN (Opcional)',
            'monthly_fee_usd': 'Cobro Mensual Total ($ USD)',
            'payment_parts': '¿En cuántos pagos divide el mes?',
            'billing_day': 'Día del 1er Cobro (1-31)',
            'first_payment_usd': 'Monto 1er Pago ($ USD)',
            'second_billing_day': 'Día del 2do Cobro (1-31)',
            'second_payment_usd': 'Monto 2do Pago ($ USD)',
            'default_concept': 'Concepto Predeterminado de Recibo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tax_id'].required = False
        self.fields['address'].required = False
        self.fields['phone'].required = False
        self.fields['email'].required = False
        self.fields['first_payment_usd'].required = False
        self.fields['second_billing_day'].required = False
        self.fields['second_payment_usd'].required = False
