from django.core.files.storage import FileSystemStorage
from .models import ProcessingJob
def create_processing_job(uploaded_file):
    storage = FileSystemStorage()
    filename = storage.save(uploaded_file.name, uploaded_file)
    job = ProcessingJob.objects.create(filename=filename)
    return job