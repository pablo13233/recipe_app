from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_list_view, name='employee_list'),
    path('new/', views.employee_create_view, name='employee_create'),
    path('<int:pk>/edit/', views.membership_edit_view, name='membership_edit'),
    path('<int:pk>/delete/', views.membership_delete_view, name='membership_delete'),
]
