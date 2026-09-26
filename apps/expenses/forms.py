from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'expense_type', 'category', 'title', 'description',
            'expense_date', 'currency', 'amount', 'exchange_rate',
            'beneficiary', 'payment_method', 'receipt_voucher'
        ]
        widgets = {
            'expense_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_expense_type'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Pago servicio de energía eléctrica'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Detalle o justificación del gasto'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'currency': forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_amount'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'id': 'id_exchange_rate'}),
            'beneficiary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. ENEE, Supermercado, Proveedor X'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'receipt_voucher': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'expense_type': 'Tipo de Gasto (Empresa vs Personal)',
            'category': 'Categoría',
            'title': 'Concepto del Gasto',
            'description': 'Descripción',
            'expense_date': 'Fecha',
            'currency': 'Moneda',
            'amount': 'Monto',
            'exchange_rate': 'Tasa de Cambio',
            'beneficiary': 'Beneficiario / Proveedor',
            'payment_method': 'Forma de Pago',
            'receipt_voucher': 'Comprobante / Factura (Opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['expense_date'].initial = timezone.localdate()
