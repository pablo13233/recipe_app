from django.contrib import admin
from .models import Company, ExchangeRateLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tax_id', 'phone', 'receipt_prefix', 'receipt_start_number',
        'current_exchange_rate', 'exchange_rate_updated_at', 'exchange_rate_auto_update', 'is_active'
    ]
    search_fields = ['name', 'legal_name', 'tax_id', 'email']
    list_filter = ['is_active', 'exchange_rate_auto_update']
    readonly_fields = ['exchange_rate_updated_at']

    fieldsets = (
        ('Datos Generales de la Empresa', {
            'fields': ('name', 'legal_name', 'tax_id', 'address', 'phone', 'email', 'logo', 'is_active')
        }),
        ('Formato y Correlativo de Recibos', {
            'fields': ('receipt_prefix', 'receipt_start_number', 'receipt_padding', 'receipt_footer_note'),
            'description': 'Define en qué número inician tus recibos y el formato (ej. 0001, REC-0001).'
        }),
        ('Configuración de Tasa de Cambio y API de Divisas (USD -> HNL)', {
            'fields': (
                ('current_exchange_rate', 'exchange_rate_updated_at'),
                'default_exchange_rate',
                'exchange_rate_api_url',
                'exchange_rate_api_key',
                'exchange_rate_auto_update',
            ),
            'description': (
                'El campo "Tasa de cambio actual almacenada" se actualiza automáticamente 1 vez al día '
                'entre 1:00 AM y 4:00 AM mediante la tarea programada. Es el valor mostrado en el sistema '
                'y en la página pública de inicio. La app no consulta la API al cargar páginas web.'
            )
        }),
        ('Saldos Iniciales de Caja (Opcional)', {
            'fields': ('initial_balance_hnl', 'initial_balance_usd'),
            'classes': ('collapse',),
            'description': 'Saldo previo con el que arrancó la empresa para el cálculo de balances y arrastre mensual.'
        }),
    )


@admin.register(ExchangeRateLog)
class ExchangeRateLogAdmin(admin.ModelAdmin):
    list_display = ['company', 'date', 'rate_usd_to_hnl', 'source', 'created_at']
    list_filter = ['company', 'source', 'date']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
