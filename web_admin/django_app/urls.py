#from django.conf.urls.defaults import patterns, include, url
#from django.contrib.auth.views import login
#from .views import open_door

from .settings import *
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.urls  import include, path
#admin.autodiscover()

urlpatterns = [
    # Examples:
    # url(r'^$', 'BloomingLabs.views.home', name='home'),
    # url(r'^BloomingLabs/', include('BloomingLabs.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    path('', include('doorman.urls')),	
    path('admin/', admin.site.urls),
 #   path('open_door/', open_door),
 #   path('accounts/login/', login),
    ]
# SDC 12/20/2012
#urlpatterns += patterns('',
#    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
#            'document_root': settings.MEDIA_ROOT,
#            }),
    
# final resort
#    url(r'^(?P<path>.*)$', 'django.views.static.serve', {
#            'document_root': settings.WWW_ROOT,
#            }),
#)
