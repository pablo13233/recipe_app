from django.contrib import admin
from .models import Receipt, ExtraIncome


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'company', 'client_display_name', 'issue_date', 'billing_month', 'billing_year', 'amount_usd', 'amount_hnl', 'is_extra_charge', 'status']
    list_filter = ['company', 'status', 'is_extra_charge', 'billing_year', 'billing_month']
    search_fields = ['receipt_number', 'client__name', 'external_client_name', 'concept', 'payment_reference']
    date_hierarchy = 'issue_date'


@admin.register(ExtraIncome)
class ExtraIncomeAdmin(admin.ModelAdmin):
    list_display = ['income_date', 'company', 'source_type', 'source_display_name', 'concept', 'amount_usd', 'amount_hnl']
    list_filter = ['company', 'source_type', 'currency', 'income_date']
    search_fields = ['client__name', 'external_company_name', 'concept', 'payment_reference']
    date_hierarchy = 'income_date'
