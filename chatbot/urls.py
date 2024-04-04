from django.urls import path
from . import views

urlpatterns = [
    path('new', views.post_new),
    path('chat/<str:thread_id>', views.chat),
    path('uploadfile/<str:pid>',views.uploadfile_and_update),
    path('deletefile', views.delete_file),
]