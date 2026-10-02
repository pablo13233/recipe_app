from decimal import Decimal
from django import forms
from .models import Company, ExchangeRateLog


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'tax_id', 'address', 'phone', 'email', 'logo',
            'receipt_prefix', 'receipt_start_number', 'receipt_padding', 
            'receipt_footer_note', 'current_exchange_rate', 'default_exchange_rate', 
            'exchange_rate_api_url', 'exchange_rate_api_key', 'exchange_rate_auto_update',
            'initial_balance_hnl', 'initial_balance_usd', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Mi Empresa S. de R.L.'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razón Social / Propietario'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 08011990123456'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección física de la empresa'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. +504 9999-9999'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@empresa.hn'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'receipt_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. REC- o dejar vacío'}),
            'receipt_start_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'receipt_padding': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'receipt_footer_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'current_exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '24.7500'}),
            'default_exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '24.7500'}),
            'exchange_rate_api_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://open.er-api.com/v6/latest/USD'}),
            'exchange_rate_api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional si tu proveedor la requiere'}),
            'exchange_rate_auto_update': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'initial_balance_hnl': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'initial_balance_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'receipt_start_number': 'Número correlativo inicial (ej: 1 para 0001)',
            'receipt_padding': 'Cantidad de dígitos para ceros a la izquierda (ej: 4 genera 0001)',
            'current_exchange_rate': 'Tasa de cambio actual almacenada (USD a HNL)',
            'default_exchange_rate': 'Tasa de cambio predeterminada / de respaldo (USD a HNL)',
            'exchange_rate_api_url': 'URL del Endpoint de la API',
            'exchange_rate_api_key': 'API Key del Proveedor (Opcional)',
            'exchange_rate_auto_update': 'Actualizar API automáticamente 1 vez al día (Tarea Programada)',
            'initial_balance_hnl': 'Saldo Inicial de Caja (L HNL) - Opcional',
            'initial_balance_usd': 'Saldo Inicial de Caja ($ USD) - Opcional',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'current_exchange_rate' in self.fields:
            self.fields['current_exchange_rate'].required = False


class ExchangeRateForm(forms.Form):
    rate = forms.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        min_value=Decimal('1.0000'),
        label="Tasa USD a HNL para hoy",
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.0001',
            'placeholder': 'Ej. 24.7500'
        })
    )
