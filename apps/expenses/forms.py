from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Expense, RecurringPayment


class RecurringPaymentForm(forms.ModelForm):
    class Meta:
        model = RecurringPayment
        fields = [
            'title', 'category', 'expense_type', 'due_day',
            'currency', 'estimated_amount', 'beneficiary',
            'service_code', 'notes', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Energía Eléctrica (Luz), Internet de Oficina, Renta'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'expense_type': forms.Select(attrs={'class': 'form-select'}),
            'due_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31, 'placeholder': 'Día del mes (1-31)'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'estimated_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'beneficiary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. ENEE, Claro, Inmobiliaria'}),
            'service_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Clave 123456, Contador 9876'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas, condiciones o detalles'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Concepto / Servicio Recurrente',
            'category': 'Categoría',
            'expense_type': 'Tipo de Gasto',
            'due_day': 'Día Límite de Pago Mensual (1-31)',
            'currency': 'Moneda',
            'estimated_amount': 'Monto Presupuestado / Estimado',
            'beneficiary': 'Beneficiario / Proveedor',
            'service_code': 'N° de Cuenta / Clave / Contador',
            'notes': 'Notas u Observaciones',
            'is_active': 'Servicio Activo para Presupuesto',
        }


class ExpenseForm(forms.ModelForm):
    recurring_payment = forms.ModelChoiceField(
        queryset=RecurringPayment.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Pago Recurrente / Presupuesto Vinculado (Opcional)'
    )

    class Meta:
        model = Expense
        fields = [
            'expense_type', 'category', 'title', 'description',
            'expense_date', 'currency', 'amount', 'exchange_rate',
            'beneficiary', 'payment_method', 'recurring_payment', 'receipt_voucher'
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
            'recurring_payment': 'Pago Recurrente / Presupuesto Asociado',
            'receipt_voucher': 'Comprobante / Factura (Opcional)',
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'expense_date' in self.fields:
            self.fields['expense_date'].initial = timezone.localdate()

        comp = company or (self.instance.company if self.instance.pk else None)
        if comp:
            self.fields['recurring_payment'].queryset = RecurringPayment.objects.filter(
                company=comp,
                is_active=True
            ).order_by('due_day', 'title')
        else:
            self.fields['recurring_payment'].queryset = RecurringPayment.objects.all().order_by('title')
