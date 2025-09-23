from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import loader
@login_required(login_url='/wsgi-scripts/accounts/login/')
def open_door(request):
    template = loader.get_template("doorman/open_door.html")	
    success =  rfid_sock.open_fucking_door(local_settings.RFID_PASSWORD,
        local_settings.RFID_HOST, 
    	local_settings.RFID_PORT) 
    return HttpResponse(template.render( "success" , success ))

def index(request):
    template = loader.get_template("doorman/index.html")
    stuff = ['Stuff' , 'More Stuff']

    context = { "Success": stuff } 
    return HttpResponse(template.render (context, request)) 	
			
