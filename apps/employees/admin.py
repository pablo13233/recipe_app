from django.contrib import admin
from .models import CompanyMembership, EmployeeProfile


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'is_default', 'created_at']
    list_filter = ['company', 'role', 'is_default']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'company__name']


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'job_title', 'phone', 'created_at']
    search_fields = ['user__username', 'job_title', 'phone']
