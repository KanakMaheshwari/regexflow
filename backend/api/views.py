from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404
from .models import ProcessingJob
# Create your views here.
@api_view(['GET'])
def hello(request):
    return Response({"message":"Hello from Django!"})

@api_view(['POST'])
def upload_file(request):
    uploaded_file=request.FILES.get('file')
    if not uploaded_file:
        return Response({"error":"No file uploaded."},status=400)
    storage=FileSystemStorage()
    filename=storage.save(uploaded_file.name,uploaded_file)
    job=ProcessingJob.objects.create(filename=filename)
    return Response({"message":"Upload successful.",
                     "job_id":job.id,
                     "status":job.status,
                     "filename":job.filename})

@api_view(['GET'])
def get_job(request,job_id):
    job=get_object_or_404(ProcessingJob,id=job_id)
    return Response({"job_id":job.id,
                     "status":job.status,
                     "filename":job.filename,
                     "uploaded_at":job.uploaded_at})