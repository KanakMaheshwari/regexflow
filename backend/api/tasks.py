import time
import os
import pandas as pd
from celery import shared_task

from .models import ProcessingJob


@shared_task
def process_uploaded_file(job_id):
    job = ProcessingJob.objects.get(id=job_id)

    try:
        job.status = "RUNNING"
        job.progress = 0
        job.save()

        print(f"Started Job {job.id}")

        file_path = os.path.join("uploads", job.filename)

        if job.filename.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif job.filename.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            job.status = "FAILED"
            job.save()
            return False

        rows = len(df)

        for i in range(rows):
            time.sleep(0.02)

            job.progress = int(((i + 1) / rows) * 100)
            job.save()

        output_path = os.path.join(
            "uploads",
            f"processed_{job.filename}"
        )

        if job.filename.endswith(".csv"):
            df.to_csv(output_path, index=False)
        else:
            df.to_excel(output_path, index=False)
        job.output_file=output_path
        # We'll add this after adding the model field
        # job.output_file = output_path

        job.status = "SUCCESS"
        job.progress = 100
        job.save()

        print("Finished!")

        return True

    except Exception as e:
        print(e)

        job.status = "FAILED"
        job.save()

        return False