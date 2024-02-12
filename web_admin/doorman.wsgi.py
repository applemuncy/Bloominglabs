

import os
#import sys
#sys.path.append('/home/pi/Bloominglabs/')
#sys.path.append('/home/pi/Bloominglabs/web_admin')
#sys.path.append('/home/pi/Bloominglabs/web_admin/doorman')

#os.environ['DJANGO_SETTINGS_MODULE'] = 'web_admin.settings'

#print (sys.path)
#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()


"""
WSGI config for testing_log project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""


from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

application = get_wsgi_application()
