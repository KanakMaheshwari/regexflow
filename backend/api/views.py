from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import FileResponse
import os

from .models import ProcessingJob
from .services import create_processing_job
from .tasks import process_uploaded_file


@api_view(["GET"])
def hello(request):
    return Response({
        "message": "Hello from Django!"
    })


@api_view(["POST"])
def upload_file(request):
    uploaded_file = request.FILES.get("file")
    instruction=request.POST.get("instruction","")  

    if uploaded_file is None:
        return Response(
            {"error": "No file uploaded."},
            status=400
        )

    try:
        # Save uploaded file and create ProcessingJob
        job = create_processing_job(uploaded_file)

        # Send task to Celery
        process_uploaded_file.delay(job.id,instruction)

        return Response({
            "message": "Upload successful.",
            "job_id": job.id,
            "status": job.status,
            "filename": str(job.filename),
            "progress": job.progress
        })

    except Exception as e:
        print(e)

        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(["GET"])
def get_job(request, job_id):
    job = get_object_or_404(ProcessingJob, id=job_id)

    return Response({
        "job_id": job.id,
        "status": job.status,
        "filename": str(job.filename),
        "progress": job.progress
    })


@api_view(["GET"])
def download_file(request, job_id):

    job = get_object_or_404(ProcessingJob, id=job_id)

    if not job.output_file:
        return Response(
            {"error": "Processed file not found."},
            status=404
        )

    return FileResponse(
        open(job.output_file.path, "rb"),
        as_attachment=True,
        filename=job.output_file.name.split("/")[-1]
    )