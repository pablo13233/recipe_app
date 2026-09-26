from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company', 'monthly_fee_usd', 'payment_parts',
        'billing_day', 'first_payment_usd', 'second_billing_day',
        'second_payment_usd', 'phone', 'is_active'
    ]
    list_filter = ['company', 'payment_parts', 'is_active', 'billing_day']
    search_fields = ['name', 'tax_id', 'phone', 'email']
