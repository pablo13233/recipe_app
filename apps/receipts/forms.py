from django import forms
from django.utils import timezone
from .models import Receipt, ExtraIncome
from apps.clients.models import Client


class ReceiptForm(forms.ModelForm):
    MONTH_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]

    billing_month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_billing_month'}),
        label="Mes que Corresponde el Cobro"
    )

    class Meta:
        model = Receipt
        fields = [
            'client', 'external_client_name', 'is_extra_charge',
            'issue_date', 'billing_month', 'billing_year',
            'concept', 'amount_usd', 'exchange_rate', 'amount_hnl', 'notes'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select', 'id': 'id_client'}),
            'external_client_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_external_client_name',
                'placeholder': 'Nombre de empresa o cliente externo (si no está registrado)'
            }),
            'is_extra_charge': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_extra_charge'
            }),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'billing_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2100, 'id': 'id_billing_year'}),
            'concept': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Cuota mensual del servicio'}),
            'amount_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_amount_usd'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'id': 'id_exchange_rate'}),
            'amount_hnl': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_amount_hnl', 'readonly': 'readonly'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas u observaciones adicionales (Opcional)'}),
        }
        labels = {
            'client': 'Cliente Registrado',
            'external_client_name': 'O Nombre de Empresa Externa (No registrada)',
            'is_extra_charge': 'Es Monto Extra / Adicional (No afecta la cuota mensual fija del cliente)',
            'issue_date': 'Fecha de Emisión',
            'billing_year': 'Año Correspondiente',
            'concept': 'Concepto del Recibo',
            'amount_usd': 'Monto Base ($ USD)',
            'exchange_rate': 'Tasa de Cambio (USD -> HNL)',
            'amount_hnl': 'Total del Recibo en Lempiras (L HNL)',
            'notes': 'Observaciones (Opcional)',
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields['notes'].required = False
        self.fields['client'].required = False
        self.fields['external_client_name'].required = False
        self.fields['is_extra_charge'].required = False

        if not self.instance.pk:
            self.fields['issue_date'].initial = today
            self.fields['billing_month'].initial = today.month
            self.fields['billing_year'].initial = today.year

        if company:
            self.fields['client'].queryset = Client.objects.filter(company=company, is_active=True).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        external_name = (cleaned_data.get('external_client_name') or '').strip()

        if not client and not external_name:
            self.add_error('client', 'Debes seleccionar un cliente registrado o escribir el nombre de la empresa externa.')
        return cleaned_data


class ReceiptProofForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['payment_proof', 'payment_reference']
        widgets = {
            'payment_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. N° de transferencia o depósito (Opcional)'
            }),
        }
        labels = {
            'payment_proof': 'Archivo de Comprobante (Imagen o PDF) *',
            'payment_reference': 'Referencia / Nota del Comprobante (Opcional)',
        }


class ExtraIncomeForm(forms.ModelForm):
    class Meta:
        model = ExtraIncome
        fields = [
            'source_type', 'client', 'external_company_name',
            'income_date', 'concept', 'currency', 'amount',
            'exchange_rate', 'payment_reference', 'payment_proof', 'notes'
        ]
        widgets = {
            'source_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_source_type'}),
            'client': forms.Select(attrs={'class': 'form-select', 'id': 'id_extra_client'}),
            'external_company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_external_company_name',
                'placeholder': 'Ej. Comercial Los Pinos S.A. / Cliente Externo'
            }),
            'income_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'concept': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Trabajo adicional, soporte puntual, consultoría externa...'
            }),
            'currency': forms.Select(attrs={'class': 'form-select', 'id': 'id_extra_currency'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'id_extra_amount',
                'placeholder': '0.00'
            }),
            'exchange_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'id': 'id_extra_rate'
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Transferencia #458921 (Opcional)'
            }),
            'payment_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Detalles adicionales de este ingreso (Opcional)'
            }),
        }
        labels = {
            'source_type': 'Origen del Ingreso *',
            'client': 'Seleccionar Empresa / Cliente Registrado *',
            'external_company_name': 'Nombre de la Empresa o Cliente Externo (No Registrado) *',
            'income_date': 'Fecha del Ingreso *',
            'concept': 'Concepto / Motivo del Ingreso *',
            'currency': 'Moneda en que se registra *',
            'amount': 'Monto del Ingreso *',
            'exchange_rate': 'Tasa de Cambio Aplicada (USD -> HNL) *',
            'payment_reference': 'Referencia / N° Transacción (Opcional)',
            'payment_proof': 'Comprobante de Pago (Opcional)',
            'notes': 'Observaciones (Opcional)',
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['client'].required = False
        self.fields['external_company_name'].required = False
        self.fields['payment_reference'].required = False
        self.fields['payment_proof'].required = False
        self.fields['notes'].required = False

        if not self.instance.pk:
            self.fields['income_date'].initial = timezone.localdate()

        if company:
            self.fields['client'].queryset = Client.objects.filter(company=company, is_active=True).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        client = cleaned_data.get('client')
        external_name = (cleaned_data.get('external_company_name') or '').strip()

        if source_type == 'registered':
            if not client:
                self.add_error('client', 'Selecciona la empresa/cliente registrado al que corresponde este monto extra.')
            cleaned_data['external_company_name'] = ''
        else:
            if not external_name:
                self.add_error('external_company_name', 'Escribe el nombre de la empresa o cliente externo.')
            cleaned_data['client'] = None

        return cleaned_data

