from django.contrib import admin
from django.urls import path, include
from bookings.views import dashboard_view

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('', include('accounts.urls')),
    path('bookings/', include('bookings.urls')),
    path('reports/', include('reports.urls')),
]
