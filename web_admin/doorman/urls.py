from django.urls import path
from . import views

app_name = 'doorman'
urlpatterns = [
            path('', views.index, name = 'index'),
        ]
