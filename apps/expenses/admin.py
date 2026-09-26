from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'expense_type', 'category', 'expense_date', 'currency', 'amount', 'amount_hnl', 'amount_usd']
    list_filter = ['company', 'expense_type', 'category', 'currency', 'expense_date']
    search_fields = ['title', 'description', 'beneficiary']
    date_hierarchy = 'expense_date'
