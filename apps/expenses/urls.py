from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list_view, name='expense_list'),
    path('new/', views.expense_create_view, name='expense_create'),
    path('<int:pk>/edit/', views.expense_edit_view, name='expense_edit'),
    path('<int:pk>/delete/', views.expense_delete_view, name='expense_delete'),
    path('reports/financial-pdf/', views.expense_financial_pdf_view, name='expense_financial_pdf'),
]
