from django.db import models

# Create your models here.
class ProcessingJob(models.Model):
    STATUS_CHOICES = [('QUEUED', 'Queued'), 
                      ('RUNNING', 'Running'), 
                      ('SUCCESS', 'Success'), 
                      ('FAILED', 'Failed')]
    filename=models.CharField(max_length=255)
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='QUEUED')
    progress=models.IntegerField(default=0)
    uploaded_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.filename