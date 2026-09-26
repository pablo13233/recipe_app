from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list_view, name='client_list'),
    path('new/', views.client_create_view, name='client_create'),
    path('<int:pk>/edit/', views.client_edit_view, name='client_edit'),
    path('<int:pk>/toggle/', views.client_toggle_status_view, name='client_toggle'),
    path('api/<int:pk>/', views.client_api_detail_view, name='client_api_detail'),
]
