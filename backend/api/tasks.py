import time

from celery import shared_task

from .models import ProcessingJob


@shared_task
def process_uploaded_file(job_id):

    job = ProcessingJob.objects.get(id=job_id)

    job.status = "RUNNING"
    job.progress = 0
    job.save()

    print(f"Started Job {job.id}")

    for i in range(1, 11):

        time.sleep(1)

        job.progress = i * 10
        job.save()

        print(f"Progress: {job.progress}%")

    job.status = "SUCCESS"
    job.progress = 100
    job.save()

    print("Finished!")