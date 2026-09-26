from django.urls import path
from . import views

urlpatterns = [
    path('', views.receipt_list_view, name='receipt_list'),
    path('new/', views.receipt_create_view, name='receipt_create'),
    path('<int:pk>/', views.receipt_detail_view, name='receipt_detail'),
    path('<int:pk>/upload-proof/', views.receipt_upload_proof_view, name='receipt_upload_proof'),
    path('<int:pk>/pdf/', views.receipt_pdf_view, name='receipt_pdf'),
    path('<int:pk>/cancel/', views.receipt_cancel_view, name='receipt_cancel'),
    path('reports/monthly-pdf/', views.receipt_monthly_pdf_report_view, name='receipt_monthly_pdf'),

    # Ingresos Extra (Fuera de cobro mensual) e Ingresos de Empresas Externas (No registradas)
    path('extra-incomes/', views.extra_income_list_view, name='extra_income_list'),
    path('extra-incomes/new/', views.extra_income_create_view, name='extra_income_create'),
    path('extra-incomes/<int:pk>/edit/', views.extra_income_edit_view, name='extra_income_edit'),
    path('extra-incomes/<int:pk>/delete/', views.extra_income_delete_view, name='extra_income_delete'),
]

