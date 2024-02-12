from django.urls import  include, path
from django.contrib.auth import login
#from views import open_door

import settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
        path ('', include('doorman.urls')),
        # Examples:
    # url(r'^$', 'BloomingLabs.views.home', name='home'),
    # url(r'^BloomingLabs/', include('BloomingLabs.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
        path('admin/', admin.site.urls),
#    url(r'^open_door/', open_door),
        path('accounts/login/', login),
        ]
# SDC 12/20/2012
"""
urlpatterns += ['',
        path(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            }),
        ]
"""    
# final resort
"""
urlpatterns += [ path(r'^(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.WWW_ROOT,
            }),
                ]
"""                
