from django.contrib import admin
from .models import Expense, RecurringPayment


@admin.register(RecurringPayment)
class RecurringPaymentAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'category', 'expense_type', 'due_day', 'currency', 'estimated_amount', 'beneficiary', 'is_active']
    list_filter = ['company', 'category', 'expense_type', 'is_active', 'currency']
    search_fields = ['title', 'beneficiary', 'service_code', 'notes']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'expense_type', 'category', 'expense_date', 'currency', 'amount', 'amount_hnl', 'amount_usd', 'recurring_payment']
    list_filter = ['company', 'expense_type', 'category', 'currency', 'expense_date']
    search_fields = ['title', 'description', 'beneficiary']
    date_hierarchy = 'expense_date'
