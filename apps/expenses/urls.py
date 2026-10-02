from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list_view, name='expense_list'),
    path('new/', views.expense_create_view, name='expense_create'),
    path('<int:pk>/edit/', views.expense_edit_view, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete_view, name='expense_delete'),
    path('reports/financial-pdf/', views.expense_financial_pdf_view, name='expense_financial_pdf'),
    # Pagos recurrentes y presupuesto mensual
    path('recurring/', views.recurring_payment_list_view, name='recurring_payment_list'),
    path('recurring/new/', views.recurring_payment_create_view, name='recurring_payment_create'),
    path('recurring/<int:pk>/edit/', views.recurring_payment_edit_view, name='recurring_payment_edit'),
    path('recurring/<int:pk>/delete/', views.recurring_payment_delete_view, name='recurring_payment_delete'),
]
