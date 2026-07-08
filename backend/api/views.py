import csv
import json
import os

import pandas as pd

from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response

from config.celery import app as celery_app

from .models import ProcessingJob
from .services import create_processing_job
from .tasks import process_uploaded_file


ALLOWED_FILE_EXTENSIONS = {".csv", ".xlsx"}
MAX_PREVIEW_PAGE_SIZE = 100

SUPPORTED_TRANSFORMATIONS = {
    "replace",
    "extract",
    "mask",
}


def parse_target_columns(request):
    target_columns_value = request.POST.get(
        "target_columns",
        ""
    )

    if target_columns_value:
        try:
            target_columns = json.loads(
                target_columns_value
            )

            if not isinstance(target_columns, list):
                raise ValueError

        except (
            json.JSONDecodeError,
            ValueError,
            TypeError
        ):
            return None

    else:
        legacy_target_column = request.POST.get(
            "target_column",
            ""
        ).strip()

        target_columns = (
            [legacy_target_column]
            if legacy_target_column
            else []
        )

    cleaned_columns = []

    for column in target_columns:
        if not isinstance(column, str):
            return None

        cleaned_column = column.strip()

        if (
            cleaned_column
            and cleaned_column not in cleaned_columns
        ):
            cleaned_columns.append(
                cleaned_column
            )

    return cleaned_columns


def get_csv_preview(
    file_path,
    page,
    page_size
):
    start_row = (
        page - 1
    ) * page_size

    end_row = start_row + page_size

    rows = []
    total_rows = 0

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        columns = reader.fieldnames or []

        for row_index, row in enumerate(reader):
            if (
                start_row
                <= row_index
                < end_row
            ):
                rows.append(row)

            total_rows += 1

    return columns, rows, total_rows


@api_view(["GET"])
def hello(request):
    return Response({
        "message": "Hello from Django!"
    })


@api_view(["POST"])
def inspect_file(request):
    uploaded_file = request.FILES.get("file")

    if uploaded_file is None:
        return Response(
            {
                "error": "No file uploaded."
            },
            status=400
        )

    if uploaded_file.size == 0:
        return Response(
            {
                "error": "Uploaded file is empty."
            },
            status=400
        )

    file_extension = os.path.splitext(
        uploaded_file.name
    )[1].lower()

    if file_extension not in ALLOWED_FILE_EXTENSIONS:
        return Response(
            {
                "error": (
                    "Unsupported file format. "
                    "Only CSV and XLSX files are supported."
                )
            },
            status=400
        )

    try:
        uploaded_file.seek(0)

        if file_extension == ".csv":
            dataframe = pd.read_csv(
                uploaded_file,
                dtype=str,
                nrows=10
            ).fillna("")

        else:
            dataframe = pd.read_excel(
                uploaded_file,
                dtype=str,
                nrows=10
            ).fillna("")

        columns = dataframe.columns.tolist()

        if not columns:
            return Response(
                {
                    "error": "Dataset contains no columns."
                },
                status=400
            )

        return Response({
            "columns": columns,
            "rows": dataframe.to_dict(
                orient="records"
            )
        })

    except UnicodeDecodeError:
        return Response(
            {
                "error": (
                    "Unable to decode CSV file. "
                    "Please upload a UTF-8 encoded CSV file."
                )
            },
            status=400
        )

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError
    ) as error:
        return Response(
            {
                "error": (
                    f"Unable to read uploaded file: "
                    f"{error}"
                )
            },
            status=400
        )

    except Exception as error:
        print(
            error,
            flush=True
        )

        return Response(
            {
                "error": str(error)
            },
            status=500
        )


@api_view(["POST"])
def upload_file(request):
    uploaded_file = request.FILES.get("file")

    instruction = request.POST.get(
        "instruction",
        ""
    ).strip()

    replacement = request.POST.get(
        "replacement",
        ""
    )

    transformation_type = request.POST.get(
        "transformation_type",
        "replace"
    ).strip().lower()

    target_columns = parse_target_columns(
        request
    )

    if uploaded_file is None:
        return Response(
            {
                "error": "No file uploaded."
            },
            status=400
        )

    if uploaded_file.size == 0:
        return Response(
            {
                "error": "Uploaded file is empty."
            },
            status=400
        )

    file_extension = os.path.splitext(
        uploaded_file.name
    )[1].lower()

    if file_extension not in ALLOWED_FILE_EXTENSIONS:
        return Response(
            {
                "error": (
                    "Unsupported file format. "
                    "Only CSV and XLSX files are supported."
                )
            },
            status=400
        )

    if not instruction:
        return Response(
            {
                "error": (
                    "Processing instruction is required."
                )
            },
            status=400
        )

    if (
        transformation_type
        not in SUPPORTED_TRANSFORMATIONS
    ):
        return Response(
            {
                "error": (
                    "Transformation type must be "
                    "replace, extract, or mask."
                )
            },
            status=400
        )

    if (
        transformation_type == "replace"
        and not replacement.strip()
    ):
        return Response(
            {
                "error": (
                    "Replacement value is required "
                    "for replace transformation."
                )
            },
            status=400
        )

    if target_columns is None:
        return Response(
            {
                "error": (
                    "Target columns must be "
                    "a valid JSON array of strings."
                )
            },
            status=400
        )

    if not target_columns:
        return Response(
            {
                "error": (
                    "At least one target column "
                    "is required."
                )
            },
            status=400
        )

    try:
        job = create_processing_job(
            uploaded_file
        )

        task = process_uploaded_file.delay(
            job.id,
            instruction,
            replacement,
            target_columns,
            transformation_type
        )

        job.task_id = task.id

        job.save(
            update_fields=["task_id"]
        )

        return Response({
            "message": "Upload successful.",
            "job_id": job.id,
            "task_id": job.task_id,
            "status": job.status,
            "filename": str(job.filename),
            "progress": job.progress,
            "target_columns": target_columns,
            "transformation_type": transformation_type
        })

    except Exception as error:
        print(
            error,
            flush=True
        )

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
                "error": (
                    "File processing "
                    "is not complete."
                )
            },
            status=400
        )

    if not job.output_file:
        return Response(
            {
                "error": (
                    "Processed file not found."
                )
            },
            status=404
        )

    if not os.path.exists(
        job.output_file.path
    ):
        return Response(
            {
                "error": (
                    "Processed file does not exist."
                )
            },
            status=404
        )

    return FileResponse(
        open(
            job.output_file.path,
            "rb"
        ),
        as_attachment=True,
        filename=os.path.basename(
            job.output_file.name
        )
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

    job.save(
        update_fields=["status"]
    )

    return Response({
        "message": (
            "Job cancelled successfully."
        ),
        "job_id": job.id,
        "status": job.status
    })


@api_view(["GET"])
def preview_file(request, job_id):
    job = get_object_or_404(
        ProcessingJob,
        id=job_id
    )

    try:
        page = int(
            request.GET.get(
                "page",
                1
            )
        )

        page_size = int(
            request.GET.get(
                "page_size",
                10
            )
        )

    except ValueError:
        return Response(
            {
                "error": (
                    "Page and page size "
                    "must be valid integers."
                )
            },
            status=400
        )

    if page < 1:
        return Response(
            {
                "error": (
                    "Page must be at least 1."
                )
            },
            status=400
        )

    if (
        page_size < 1
        or page_size > MAX_PREVIEW_PAGE_SIZE
    ):
        return Response(
            {
                "error": (
                    "Page size must be "
                    "between 1 and 100."
                )
            },
            status=400
        )

    if (
        job.status == "SUCCESS"
        and job.output_file
    ):
        file_path = job.output_file.path
        preview_type = "processed"

    else:
        if not job.filename:
            return Response(
                {
                    "error": (
                        "Uploaded file not found."
                    )
                },
                status=404
            )

        file_path = job.filename.path
        preview_type = "original"

    if not os.path.exists(file_path):
        return Response(
            {
                "error": (
                    "Preview file does not exist."
                )
            },
            status=404
        )

    try:
        if file_path.lower().endswith(".csv"):
            (
                columns,
                rows,
                total_rows
            ) = get_csv_preview(
                file_path,
                page,
                page_size
            )

        elif file_path.lower().endswith(".xlsx"):
            dataframe = pd.read_excel(
                file_path,
                dtype=str
            )

            dataframe = dataframe.fillna("")

            columns = dataframe.columns.tolist()

            total_rows = len(dataframe)

            start = (
                page - 1
            ) * page_size

            end = start + page_size

            rows = (
                dataframe
                .iloc[start:end]
                .to_dict(orient="records")
            )

        else:
            return Response(
                {
                    "error": (
                        "Unsupported file format."
                    )
                },
                status=400
            )

        total_pages = max(
            1,
            (
                total_rows
                + page_size
                - 1
            )
            // page_size
        )

        if page > total_pages:
            return Response(
                {
                    "error": (
                        "Invalid page number."
                    )
                },
                status=400
            )

        return Response({
            "job_id": job.id,
            "preview_type": preview_type,
            "columns": columns,
            "rows": rows,
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": total_pages
        })

    except UnicodeDecodeError:
        return Response(
            {
                "error": (
                    "Unable to decode CSV file. "
                    "Please upload a UTF-8 "
                    "encoded CSV file."
                )
            },
            status=400
        )

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError
    ) as error:
        return Response(
            {
                "error": (
                    f"Unable to read "
                    f"preview file: {error}"
                )
            },
            status=400
        )

    except Exception as error:
        print(
            error,
            flush=True
        )

        return Response(
            {
                "error": str(error)
            },
            status=500
        )