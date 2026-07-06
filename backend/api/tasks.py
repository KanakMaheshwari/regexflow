import os
import time
import pandas as pd

from celery import shared_task
from django.core.files.base import File
# from .transformations import apply_instruction
from .models import ProcessingJob
from .cache import get_cached_regex, cache_regex
from .llm_service import generate_regex


@shared_task
def process_uploaded_file(
    job_id,
    instruction,
    replacement,
    target_column
):

    job = ProcessingJob.objects.get(id=job_id)

    try:
        job.status = "RUNNING"
        job.progress = 0
        job.save()

        print(f"\n========== JOB {job.id} ==========", flush=True)
        print(f"Instruction: {instruction}", flush=True)
        print(f"Replacement: {replacement}", flush=True)
        print(f"Target Column: {target_column}", flush=True)

        file_path = job.filename.path

        print(f"Reading file: {file_path}", flush=True)

        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)

        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)

        else:
            job.status = "FAILED"
            job.save()
            print("Unsupported file format", flush=True)
            return False

        print("Original DataFrame:", flush=True)
        print(df.head(), flush=True)

        regex_data = get_cached_regex(instruction)

        if regex_data:
            print("Regex loaded from Redis cache.", flush=True)

        else:
            print("Generating regex...", flush=True)

            regex_data = generate_regex(instruction)

            cache_regex(instruction, regex_data)

        regex = regex_data["regex"]

        print(f"Regex: {regex}", flush=True)

        if target_column:

            matching_column = None

            for column in df.columns:
                if column.lower() == target_column.lower():
                    matching_column = column
                    break

            if matching_column is None:
                raise ValueError(
                    f"Target column '{target_column}' not found."
                )

            df[matching_column] = (
                df[matching_column]
                .astype(str)
                .str.replace(regex, replacement, regex=True)
            )

        else:

            for column in df.select_dtypes(include="object").columns:
                df[column] = (
                    df[column]
                    .astype(str)
                    .str.replace(regex, replacement, regex=True)
                )

        rows = max(len(df), 1)

        for i in range(rows):
            time.sleep(0.02)

            progress = int(((i + 1) / rows) * 100)

            if progress > job.progress:
                job.progress = progress
                job.save()

        filename = os.path.basename(job.filename.name)

        processed_dir = os.path.join("uploads", "processed")
        os.makedirs(processed_dir, exist_ok=True)

        output_path = os.path.join(
            processed_dir,
            f"processed_{filename}"
        )

        print(f"Saving file to: {output_path}", flush=True)

        if filename.endswith(".csv"):
            df.to_csv(output_path, index=False)

        else:
            df.to_excel(output_path, index=False)

        with open(output_path, "rb") as f:
            job.output_file.save(
                f"processed_{filename}",
                File(f),
                save=False
            )

        job.status = "SUCCESS"
        job.progress = 100
        job.save()

        print("Finished!", flush=True)
        print("=============================\n", flush=True)

        return True

    except Exception as e:
        print("TASK FAILED", flush=True)
        print(e, flush=True)

        job.status = "FAILED"
        job.save()

        return False