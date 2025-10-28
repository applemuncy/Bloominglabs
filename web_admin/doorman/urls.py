from django.urls import path

from . import views 

app_nane = 'doorman'
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("last/", views.IndexView.as_view(), name="index"),
    path("All/<int:pk>/", views.AccessView.as_view(), name="event_list"),
    path("open_door/", views.open_door, name="open_door"),
    path("AccessEvent", views.AccessEvent, name="AccessEvent"),
]

