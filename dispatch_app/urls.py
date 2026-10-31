from django.urls import path
from . import views

urlpatterns = [
    # Public & Auth
    path('', views.landing_home, name='landing_home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Citizen Portal
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('predict/', views.emergency_prediction, name='emergency_prediction'),
    path('training/', views.model_training_view, name='model_training'),

    # Police Command Admin Dashboard
    path('police-admin/', views.police_dashboard, name='police_dashboard'),
    path('police-admin/toggle-user/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('police-admin/delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('police-admin/dispatch/<int:incident_id>/', views.dispatch_patrol, name='dispatch_patrol'),

    # Real-Time Alert Polling API
    path('api/alerts/', views.api_active_alerts, name='api_active_alerts'),
]
