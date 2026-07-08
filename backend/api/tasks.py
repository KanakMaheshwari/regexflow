import glob
import os
import shutil

import pandas as pd

from celery import shared_task
from django.core.files.base import File
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from .cache import cache_regex, get_cached_regex
from .llm_service import generate_regex
from .models import ProcessingJob
from .regex_validator import validate_regex_safety
from .spark_service import apply_regex_with_spark


SPARK_FILE_SIZE_THRESHOLD = 10 * 1024 * 1024

SUPPORTED_TRANSFORMATIONS = {
    "replace",
    "extract",
    "mask",
}


def combine_spark_csv_parts(part_files, output_path):
    if not part_files:
        raise ValueError(
            "PySpark did not generate any output CSV files."
        )

    part_files = sorted(part_files)

    with open(output_path, "wb") as output_file:
        for index, part_file in enumerate(part_files):
            with open(part_file, "rb") as input_file:
                if index == 0:
                    shutil.copyfileobj(
                        input_file,
                        output_file
                    )
                else:
                    input_file.readline()

                    shutil.copyfileobj(
                        input_file,
                        output_file
                    )


def find_matching_columns(
    dataframe_columns,
    target_columns
):
    column_lookup = {
        column.lower(): column
        for column in dataframe_columns
    }

    matching_columns = []
    missing_columns = []

    for target_column in target_columns:
        matching_column = column_lookup.get(
            target_column.lower()
        )

        if matching_column is None:
            missing_columns.append(target_column)
        else:
            matching_columns.append(matching_column)

    if missing_columns:
        raise ValueError(
            "Target column(s) not found: "
            + ", ".join(missing_columns)
        )

    return matching_columns


def get_sample_values(
    dataframe,
    matching_columns,
    sample_limit=10
):
    sample_values = []

    for column in matching_columns:
        values = (
            dataframe[column]
            .dropna()
            .astype(str)
            .head(sample_limit)
            .tolist()
        )

        sample_values.extend(values)

    return sample_values[:sample_limit]


def apply_pandas_transformation(
    dataframe,
    matching_columns,
    regex,
    replacement,
    transformation_type
):
    for matching_column in matching_columns:
        series = (
            dataframe[matching_column]
            .fillna("")
            .astype(str)
        )

        if transformation_type == "replace":
            dataframe[matching_column] = (
                series.str.replace(
                    regex,
                    replacement,
                    regex=True
                )
            )

        elif transformation_type == "extract":
            dataframe[matching_column] = (
                series.str.extract(
                    f"({regex})",
                    expand=False
                )
                .fillna("")
            )

        elif transformation_type == "mask":
            dataframe[matching_column] = (
                series.str.replace(
                    regex,
                    "********",
                    regex=True
                )
            )

        else:
            raise ValueError(
                "Unsupported transformation type: "
                f"{transformation_type}"
            )

    return dataframe


@shared_task(
    bind=True,
    max_retries=3
)
def process_uploaded_file(
    self,
    job_id,
    instruction,
    replacement,
    target_columns,
    transformation_type="replace"
):
    job = ProcessingJob.objects.get(id=job_id)

    try:
        if isinstance(target_columns, str):
            target_columns = [target_columns]

        target_columns = [
            column.strip()
            for column in target_columns
            if isinstance(column, str)
            and column.strip()
        ]

        transformation_type = (
            transformation_type
            .strip()
            .lower()
        )

        if not target_columns:
            raise ValueError(
                "At least one target column is required."
            )

        if (
            transformation_type
            not in SUPPORTED_TRANSFORMATIONS
        ):
            raise ValueError(
                "Unsupported transformation type: "
                f"{transformation_type}"
            )

        job.status = "RUNNING"
        job.progress = 5

        job.save(
            update_fields=[
                "status",
                "progress"
            ]
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 5,
                "message": "Starting processing job."
            }
        )

        print(
            f"\n========== JOB {job.id} ==========",
            flush=True
        )
        print(
            f"Instruction: {instruction}",
            flush=True
        )
        print(
            f"Replacement: {replacement}",
            flush=True
        )
        print(
            f"Target Columns: {target_columns}",
            flush=True
        )
        print(
            f"Transformation Type: "
            f"{transformation_type}",
            flush=True
        )

        file_path = job.filename.path
        file_size = os.path.getsize(file_path)

        print(
            f"File path: {file_path}",
            flush=True
        )
        print(
            f"File size: {file_size} bytes",
            flush=True
        )

        use_spark = (
            file_path.lower().endswith(".csv")
            and file_size >= SPARK_FILE_SIZE_THRESHOLD
        )

        if use_spark:
            print(
                "Large CSV detected. Reading sample only.",
                flush=True
            )

            dataframe = pd.read_csv(
                file_path,
                dtype=str,
                nrows=100
            )

        elif file_path.lower().endswith(".csv"):
            print(
                "Small CSV detected. Using Pandas.",
                flush=True
            )

            dataframe = pd.read_csv(
                file_path,
                dtype=str
            )

        elif file_path.lower().endswith(".xlsx"):
            print(
                "Excel file detected. Using Pandas.",
                flush=True
            )

            dataframe = pd.read_excel(
                file_path,
                dtype=str
            )

        else:
            raise ValueError(
                "Unsupported file format."
            )

        matching_columns = find_matching_columns(
            dataframe.columns,
            target_columns
        )

        sample_values = get_sample_values(
            dataframe,
            matching_columns
        )

        print(
            f"Matching columns: {matching_columns}",
            flush=True
        )
        print(
            f"Sample values: {sample_values}",
            flush=True
        )

        job.progress = 15
        job.save(update_fields=["progress"])

        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 15,
                "message": "Dataset validated."
            }
        )

        regex_data = get_cached_regex(
            instruction
        )

        if regex_data:
            try:
                validate_regex_safety(
                    regex_data["regex"]
                )

                print(
                    "Safe regex loaded from Redis cache.",
                    flush=True
                )

            except (
                ValueError,
                KeyError,
                TypeError
            ):
                print(
                    "Invalid or unsafe cached regex ignored.",
                    flush=True
                )

                regex_data = None

        if not regex_data:
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": 20,
                    "message": "Generating regex."
                }
            )

            print(
                "Generating regex using OpenAI...",
                flush=True
            )

            regex_data = generate_regex(
                instruction,
                sample_values
            )

            validate_regex_safety(
                regex_data["regex"]
            )

            cache_regex(
                instruction,
                regex_data
            )

            print(
                "Safe regex stored in Redis cache.",
                flush=True
            )

        regex = regex_data["regex"]

        print(
            f"Regex: {regex}",
            flush=True
        )

        job.progress = 30
        job.save(update_fields=["progress"])

        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 30,
                "message": "Regex ready."
            }
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

        if use_spark:
            print(
                "Processing engine: PySpark",
                flush=True
            )

            spark_output_dir = os.path.join(
                processed_dir,
                f"spark_job_{job.id}"
            )

            if os.path.exists(spark_output_dir):
                shutil.rmtree(spark_output_dir)

            job.progress = 40
            job.save(update_fields=["progress"])

            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": 40,
                    "message": (
                        "Processing large dataset "
                        "with PySpark."
                    )
                }
            )

            apply_regex_with_spark(
                input_path=file_path,
                output_path=spark_output_dir,
                regex=regex,
                replacement=replacement,
                target_columns=matching_columns,
                transformation_type=transformation_type
            )

            job.progress = 80
            job.save(update_fields=["progress"])

            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": 80,
                    "message": (
                        "Combining Spark output partitions."
                    )
                }
            )

            part_files = glob.glob(
                os.path.join(
                    spark_output_dir,
                    "part-*.csv"
                )
            )

            print(
                f"Spark generated "
                f"{len(part_files)} partition files.",
                flush=True
            )

            combine_spark_csv_parts(
                part_files,
                output_path
            )

            print(
                "Spark partition files "
                "combined successfully.",
                flush=True
            )

            shutil.rmtree(spark_output_dir)

        else:
            print(
                "Processing engine: Pandas",
                flush=True
            )

            job.progress = 40
            job.save(update_fields=["progress"])

            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": 40,
                    "message": (
                        "Processing dataset with Pandas."
                    )
                }
            )

            dataframe = apply_pandas_transformation(
                dataframe=dataframe,
                matching_columns=matching_columns,
                regex=regex,
                replacement=replacement,
                transformation_type=transformation_type
            )

            if filename.lower().endswith(".csv"):
                dataframe.to_csv(
                    output_path,
                    index=False
                )
            else:
                dataframe.to_excel(
                    output_path,
                    index=False
                )

        job.progress = 90
        job.save(update_fields=["progress"])

        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 90,
                "message": "Saving processed result."
            }
        )

        print(
            f"Saving file to: {output_path}",
            flush=True
        )

        with open(output_path, "rb") as file:
            job.output_file.save(
                f"processed_{filename}",
                File(file),
                save=False
            )

        job.status = "SUCCESS"
        job.progress = 100

        job.save(
            update_fields=[
                "output_file",
                "status",
                "progress"
            ]
        )

        self.update_state(
            state="SUCCESS",
            meta={
                "progress": 100,
                "message": (
                    "Processing completed successfully."
                )
            }
        )

        print("Finished!", flush=True)
        print(
            "=============================\n",
            flush=True
        )

        return True

    except (
        APIConnectionError,
        APITimeoutError,
        RateLimitError,
        InternalServerError,
    ) as error:
        print(
            f"OpenAI API/network error: {error}",
            flush=True
        )

        if self.request.retries >= self.max_retries:
            job.status = "FAILED"

            job.save(
                update_fields=["status"]
            )

            print(
                "Maximum OpenAI retry attempts exhausted.",
                flush=True
            )

            raise

        retry_number = self.request.retries + 1

        retry_delay = 2 ** self.request.retries

        print(
            f"Retrying task. "
            f"Retry number: {retry_number}. "
            f"Retry delay: {retry_delay} seconds.",
            flush=True
        )

        raise self.retry(
            exc=error,
            countdown=retry_delay
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

        job.save(
            update_fields=["status"]
        )

        raise