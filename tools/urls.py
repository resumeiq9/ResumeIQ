from django.urls import path

from . import views

app_name = 'tools'

urlpatterns = [
    path('', views.home, name='home'),
    path('get-started/', views.get_started, name='get_started'),
    path('tools/', views.tools_page, name='tools_page'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('chatbot/ask/', views.chatbot_ask, name='chatbot_ask'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('resume-creator/', views.resume_creator, name='resume_creator'),
    path('resume-analyser/', views.resume_analyser, name='resume_analyser'),
    path('resume-optimizer/', views.resume_optimizer, name='resume_optimizer'),
]
