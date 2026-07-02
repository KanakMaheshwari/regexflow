from django.urls import path
from .views import hello, upload_file, get_job, download_file
urlpatterns = [
    path('hello/', hello),
    path('upload/', upload_file),
    path('jobs/<int:job_id>/', get_job),
    path('download/<int:job_id>/', download_file),]