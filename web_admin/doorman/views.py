from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import loader
from django.http import HttpResponse
from . rfid_sock import open_fucking_door
from django_app.settings import *
from django.views import generic
from .models import AccessEvent
@login_required(login_url='/wsgi-scripts/accounts/login/')
def open_door(request):
    
    success =  open_fucking_door(
        RFID_PASSWORD,
        RFID_HOST, 
        RFID_PORT
    )

    context = {"success" : success }
    return render(request, 'doorman/door_open.html',  context) 


def index(request):
    last10  = ["stuff","stuff2"]


    context = { "doorevents" : last10  } 
    return render(request , "doorman/index.html", context)
			

class IndexView(generic.ListView):
    template_name = "doorman/index.html"
    context_object_name = "latest_access_list"

    def get_queryset(self):
        return AccessEvent.objects.order_by("-event_date")[:10]

class AccessView(generic.ListView):
    template_name = 'doorman/access.html'
    context_object_name = "all_access_list"
    paginate_by = 20 


    def get_queryset(self, **kwargs):
        post_pk = self.kwargs['pk']
        print(f"pk: {post_pk}")

        return AccessEvent.objects.filter(user = post_pk)


    
