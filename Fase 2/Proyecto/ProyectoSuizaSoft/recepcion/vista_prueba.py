from django.urls import path
from . import views

urlpatterns = [
    # Esta es la ruta que vamos a probar
    path('api/prueba/', views.vista_prueba, name='prueba_conexion'),
]