from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import FileResponse
import pandas as pd
from .models import ProcessingJob
from .services import create_processing_job
from .tasks import process_uploaded_file
from config.celery import app as celery_app


@api_view(["GET"])
def hello(request):
    return Response({
        "message": "Hello from Django!"
    })


@api_view(["POST"])
def upload_file(request):
    uploaded_file = request.FILES.get("file")
    instruction = request.POST.get("instruction", "")
    replacement = request.POST.get("replacement", "")
    target_column = request.POST.get("target_column", "")

    if uploaded_file is None:
        return Response(
            {
                "error": "No file uploaded."
            },
            status=400
        )

    if not instruction.strip():
        return Response(
            {
                "error": "Processing instruction is required."
            },
            status=400
        )

    try:
        job = create_processing_job(uploaded_file)

        task = process_uploaded_file.delay(
            job.id,
            instruction,
            replacement,
            target_column
        )

        job.task_id = task.id
        job.save()

        return Response({
            "message": "Upload successful.",
            "job_id": job.id,
            "task_id": job.task_id,
            "status": job.status,
            "filename": str(job.filename),
            "progress": job.progress
        })

    except Exception as error:
        print(error, flush=True)

        return Response(
            {
                "error": str(error)
            },
            status=500
        )


@api_view(["GET"])
def get_job(request, job_id):
    job = get_object_or_404(
        ProcessingJob,
        id=job_id
    )

    return Response({
        "job_id": job.id,
        "task_id": job.task_id,
        "status": job.status,
        "filename": str(job.filename),
        "progress": job.progress
    })


@api_view(["GET"])
def download_file(request, job_id):
    job = get_object_or_404(
        ProcessingJob,
        id=job_id
    )

    if job.status != "SUCCESS":
        return Response(
            {
                "error": "File processing is not complete."
            },
            status=400
        )

    if not job.output_file:
        return Response(
            {
                "error": "Processed file not found."
            },
            status=404
        )

    return FileResponse(
        open(job.output_file.path, "rb"),
        as_attachment=True,
        filename=job.output_file.name.split("/")[-1]
    )


@api_view(["POST"])
def cancel_job(request, job_id):
    job = get_object_or_404(
        ProcessingJob,
        id=job_id
    )

    if job.status in [
        "SUCCESS",
        "FAILED",
        "CANCELLED"
    ]:
        return Response(
            {
                "error": (
                    f"Cannot cancel a job "
                    f"with status {job.status}."
                )
            },
            status=400
        )

    if job.task_id:
        celery_app.control.revoke(
            job.task_id,
            terminate=True
        )

    job.status = "CANCELLED"
    job.save()

    return Response({
        "message": "Job cancelled successfully.",
        "job_id": job.id,
        "status": job.status
    })

@api_view(["GET"])
def preview_file(request, job_id):
    job = get_object_or_404(
        ProcessingJob,
        id=job_id
    )

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))

    file_path = job.filename.path

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(
                file_path,
                dtype=str
            )

        elif file_path.lower().endswith(".xlsx"):
            df = pd.read_excel(
                file_path,
                dtype=str
            )

        else:
            return Response(
                {"error": "Unsupported file format."},
                status=400
            )

        df = df.fillna("")

        total_rows = len(df)
        total_pages = max(
            1,
            (total_rows + page_size - 1) // page_size
        )

        if page < 1 or page > total_pages:
            return Response(
                {"error": "Invalid page number."},
                status=400
            )

        start = (page - 1) * page_size
        end = start + page_size

        preview_df = df.iloc[start:end]

        return Response({
            "job_id": job.id,
            "columns": df.columns.tolist(),
            "rows": preview_df.to_dict(orient="records"),
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages
        })

    except Exception as error:
        return Response(
            {"error": str(error)},
            status=500
        )