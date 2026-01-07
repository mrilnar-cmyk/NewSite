from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('formulas/', include('formulas.urls')),
    path('calculator/', include('calculator.urls')),
]