from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    # Authenticated routes
    path("admin/", admin.site.urls),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    # Portfolio routes
    path('portfolio/', include('portfolio.urls')),
    # Asset routes
    path('public/', include('asset.urls')),
    # Chatbot routes
    path("api/", include("chatbot.urls")),

]

# Catch all other urls that are not in the above urlpatterns
urlpatterns += [re_path(r'^.*', TemplateView.as_view(template_name='index.html'))] # this is for react router to work

