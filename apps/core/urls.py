from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('switch-company/<int:company_id>/', views.switch_company_view, name='switch_company'),
    path('companies/', views.company_list_view, name='company_list'),
    path('companies/new/', views.company_create_view, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_edit_view, name='company_edit'),
    path('update-exchange-rate/', views.update_exchange_rate_view, name='update_exchange_rate'),
    path('reports/', views.reports_view, name='reports'),
    path('reminders/', views.reminders_view, name='reminders'),
]
