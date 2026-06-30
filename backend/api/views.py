from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404
from .models import ProcessingJob
from .services import create_processing_job
from .tasks import process_uploaded_file
# Create your views here.
@api_view(['GET'])
def hello(request):
    return Response({"message":"Hello from Django!"})

@api_view(['POST'])
def upload_file(request):
    uploaded_file=request.FILES.get('file')
    if not uploaded_file:
        return Response({"error":"No file uploaded."},status=400)
    
    job=create_processing_job(uploaded_file)
    # Start the background task
    process_uploaded_file.delay(job.id)
    return Response({"job_id":job.id,
                     "status":job.status,
                    "progress": job.progress,
                     "filename":job.filename})

@api_view(['GET'])
def get_job(request,job_id):
    job=get_object_or_404(ProcessingJob,id=job_id)
    return Response({"job_id":job.id,
                     "status":job.status,
                     "filename":job.filename,
                     "progress":job.progress})