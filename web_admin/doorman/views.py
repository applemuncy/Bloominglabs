import rfid_sock
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import local_settings

@login_required(login_url='/wsgi-scripts/accounts/login/')
def open_door(request):
    success =  rfid_sock.open_fucking_door(local_settings.RFID_PASSWORD,
        local_settings.RFID_HOST, 
    	local_settings.RFID_PORT) 
    return render('door_open.html',
                              { "success":success })

def index(request):
    return render(request, 'doorman/index.html')

