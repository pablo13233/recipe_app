from django.contrib import admin
from .models import Company, ExchangeRateLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_id', 'phone', 'receipt_prefix', 'receipt_start_number', 'default_exchange_rate', 'is_active']
    search_fields = ['name', 'legal_name', 'tax_id', 'email']
    list_filter = ['is_active']


@admin.register(ExchangeRateLog)
class ExchangeRateLogAdmin(admin.ModelAdmin):
    list_display = ['date', 'rate_usd_to_hnl', 'source', 'created_at']
    list_filter = ['source', 'date']
    date_hierarchy = 'date'
