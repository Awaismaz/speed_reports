from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_file, name='upload_file'),
    path('update/', views.filter_data, name='filter_data'),
    path('preview/', views.preview_report, name='preview_report'),
    path('community_report/', views.community_report, name='community_report'),
    path('school_zone/', views.school_zone, name='school_zone'),
]
