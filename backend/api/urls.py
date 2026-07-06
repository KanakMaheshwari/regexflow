from django.urls import path

from .views import (
    hello,
    upload_file,
    get_job,
    download_file,
    cancel_job,
    preview_file
)


urlpatterns = [
    path(
        "hello/",
        hello,
        name="hello"
    ),

    path(
        "upload/",
        upload_file,
        name="upload_file"
    ),

    path(
        "jobs/<int:job_id>/",
        get_job,
        name="get_job"
    ),

    path(
        "download/<int:job_id>/",
        download_file,
        name="download_file"
    ),

    path(
        "jobs/<int:job_id>/cancel/",
        cancel_job,
        name="cancel_job"
    ),

    path(
        "jobs/<int:job_id>/preview/",
        preview_file,
        name="preview_file"
    ),
]