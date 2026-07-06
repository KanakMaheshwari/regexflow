from django.db import models


class ProcessingJob(models.Model):

    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled')
    ]

    filename = models.FileField(
        upload_to="uploads/"
    )

    output_file = models.FileField(
        upload_to="processed/",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='QUEUED'
    )

    progress = models.IntegerField(
        default=0
    )

    task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return str(self.filename)