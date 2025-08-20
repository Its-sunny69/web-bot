from django.urls import path
from . import views

app_name = 'preview'

urlpatterns = [
    path('redirect/<int:repo_id>/', views.redirect_to_stackblitz, name='redirect_to_stackblitz'),
    path('api/files/<int:repo_id>/', views.repository_files_api, name='repository_files_api'),
]