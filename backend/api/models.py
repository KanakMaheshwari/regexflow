from django.db import models

# Create your models here.
class ProcessingJob(models.Model):
    filename=models.CharField(max_length=255)
    status=models.CharField(max_length=20,default='UPLOADED')
    uploaded_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.filename