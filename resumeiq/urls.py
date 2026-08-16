from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path('accounts/', include('allauth.urls')),  # Google sign-in lives under /accounts/google/...
    path('', include('tools.urls')),
]

urlpatterns += staticfiles_urlpatterns()
