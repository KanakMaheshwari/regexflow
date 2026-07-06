import glob
import os
import shutil
import time

import pandas as pd
import requests

from celery import shared_task
from django.core.files.base import File

from .models import ProcessingJob
from .cache import get_cached_regex, cache_regex
from .llm_service import generate_regex
from .spark_service import apply_regex_with_spark


SPARK_FILE_SIZE_THRESHOLD = 10 * 1024 * 1024


@shared_task(bind=True, max_retries=3)
def process_uploaded_file(
    self,
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
        file_size = os.path.getsize(file_path)

        print(f"Reading file: {file_path}", flush=True)
        print(f"File size: {file_size} bytes", flush=True)

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
            raise ValueError(
                "Unsupported file format."
            )

        print("Original DataFrame:", flush=True)
        print(df.head(), flush=True)

        sample_values = []
        matching_column = None

        if target_column:
            for column in df.columns:
                if column.lower() == target_column.lower():
                    matching_column = column
                    break

            if matching_column is None:
                raise ValueError(
                    f"Target column '{target_column}' not found."
                )

            sample_values = (
                df[matching_column]
                .dropna()
                .astype(str)
                .head(10)
                .tolist()
            )

            print(
                f"Sample values: {sample_values}",
                flush=True
            )

        regex_data = get_cached_regex(instruction)

        if regex_data:
            print(
                "Regex loaded from Redis cache.",
                flush=True
            )

        else:
            print(
                "Generating regex using Ollama...",
                flush=True
            )

            regex_data = generate_regex(
                instruction,
                sample_values
            )

            cache_regex(
                instruction,
                regex_data
            )

        regex = regex_data["regex"]

        print(
            f"Regex: {regex}",
            flush=True
        )

        filename = os.path.basename(
            job.filename.name
        )

        processed_dir = os.path.join(
            "uploads",
            "processed"
        )

        os.makedirs(
            processed_dir,
            exist_ok=True
        )

        output_path = os.path.join(
            processed_dir,
            f"processed_{filename}"
        )

        use_spark = (
            file_path.lower().endswith(".csv")
            and file_size >= SPARK_FILE_SIZE_THRESHOLD
        )

        if use_spark:
            print(
                "Processing engine: PySpark",
                flush=True
            )

            job.progress = 30
            job.save()

            spark_output_dir = os.path.join(
                processed_dir,
                f"spark_job_{job.id}"
            )

            if os.path.exists(spark_output_dir):
                shutil.rmtree(spark_output_dir)

            apply_regex_with_spark(
                input_path=file_path,
                output_path=spark_output_dir,
                regex=regex,
                replacement=replacement,
                target_column=target_column
            )

            job.progress = 80
            job.save()

            part_files = glob.glob(
                os.path.join(
                    spark_output_dir,
                    "part-*.csv"
                )
            )

            if not part_files:
                raise ValueError(
                    "PySpark did not generate an output CSV file."
                )

            shutil.move(
                part_files[0],
                output_path
            )

            shutil.rmtree(
                spark_output_dir
            )

        else:
            print(
                "Processing engine: Pandas",
                flush=True
            )

            if target_column:
                df[matching_column] = (
                    df[matching_column]
                    .astype(str)
                    .str.replace(
                        regex,
                        replacement,
                        regex=True
                    )
                )

            else:
                text_columns = (
                    df
                    .select_dtypes(include="object")
                    .columns
                )

                for column in text_columns:
                    df[column] = (
                        df[column]
                        .astype(str)
                        .str.replace(
                            regex,
                            replacement,
                            regex=True
                        )
                    )

            rows = max(len(df), 1)

            for i in range(rows):
                progress = int(
                    ((i + 1) / rows) * 80
                )

                if progress > job.progress:
                    job.progress = progress
                    job.save()

                time.sleep(0.02)

            print(
                "Processed DataFrame:",
                flush=True
            )

            print(
                df.head(),
                flush=True
            )

            if filename.lower().endswith(".csv"):
                df.to_csv(
                    output_path,
                    index=False
                )

            else:
                df.to_excel(
                    output_path,
                    index=False
                )

        print(
            f"Saving file to: {output_path}",
            flush=True
        )

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

    except requests.exceptions.RequestException as error:
        print(
            f"Ollama/network error: {error}",
            flush=True
        )

        if self.request.retries >= self.max_retries:
            job.status = "FAILED"
            job.save()

            print(
                "Maximum retries reached. Job failed.",
                flush=True
            )

            raise

        print(
            f"Retrying task. Retry number: {self.request.retries + 1}",
            flush=True
        )

        raise self.retry(
            exc=error,
            countdown=2 ** self.request.retries
        )

    except Exception as error:
        print(
            "TASK FAILED",
            flush=True
        )

        print(
            error,
            flush=True
        )

        job.status = "FAILED"
        job.save()

        return False