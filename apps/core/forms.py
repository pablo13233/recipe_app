from decimal import Decimal
from django import forms
from .models import Company, ExchangeRateLog


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'tax_id', 'address', 'phone', 'email', 'logo',
            'receipt_prefix', 'receipt_start_number', 'receipt_padding', 
            'receipt_footer_note', 'default_exchange_rate', 'is_active'
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
            'default_exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'receipt_start_number': 'Número correlativo inicial (ej: 1 para 0001)',
            'receipt_padding': 'Cantidad de dígitos para ceros a la izquierda (ej: 4 genera 0001)',
        }


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
