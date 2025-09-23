from django.urls import path

from . import views 

urlpatterns = [
    path("", views.index, name="index"),
    path("", views.open_door, name="open_door"),
]

