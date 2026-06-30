from celery import shared_task
import time
from .models import ProcessingJob
@shared_task
def process_uploaded_file(job_id):
    job = ProcessingJob.objects.get(id=job_id)
    job.status="RUNNING"
    job.progress=0
    job.save()
    for i in range(1, 11):
        time.sleep(1)  
        job.progress=i*10
        job.save()
    job.status="SUCCESS"
    job.progress=100
    job.save()
    return True

