from django.urls import path

from .views import (
    cancel_job,
    download_file,
    get_job,
    hello,
    inspect_file,
    preview_file,
    upload_file,
)


urlpatterns = [
    path(
        "hello/",
        hello,
        name="hello"
    ),
    path(
        "inspect/",
        inspect_file,
        name="inspect-file"
    ),
    path(
        "upload/",
        upload_file,
        name="upload-file"
    ),
    path(
        "jobs/<int:job_id>/",
        get_job,
        name="get-job"
    ),
    path(
        "jobs/<int:job_id>/preview/",
        preview_file,
        name="preview-file"
    ),
    path(
        "jobs/<int:job_id>/cancel/",
        cancel_job,
        name="cancel-job"
    ),
    path(
        "download/<int:job_id>/",
        download_file,
        name="download-file"
    ),
]