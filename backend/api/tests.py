import os
import tempfile
from unittest.mock import patch, MagicMock

import pandas as pd

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import ProcessingJob
from .regex_validator import validate_regex_safety


class RegexSafetyValidatorTests(TestCase):

    def test_valid_email_regex(self):
        regex = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

        result = validate_regex_safety(regex)

        self.assertTrue(result)

    def test_invalid_regex_syntax(self):
        regex = r"([A-Z]+"

        with self.assertRaises(ValueError):
            validate_regex_safety(regex)

    def test_nested_quantifier_is_rejected(self):
        regex = r"(a+)+"

        with self.assertRaises(ValueError):
            validate_regex_safety(regex)

    def test_regex_too_long_is_rejected(self):
        regex = "a" * 501

        with self.assertRaises(ValueError):
            validate_regex_safety(regex)

    def test_regex_must_be_string(self):
        with self.assertRaises(ValueError):
            validate_regex_safety(12345)


class ProcessingJobModelTests(TestCase):

    def test_processing_job_creation(self):
        uploaded_file = SimpleUploadedFile(
            "test.csv",
            b"Name,Email\nKanak,kanak@example.com\n",
            content_type="text/csv",
        )

        job = ProcessingJob.objects.create(
            filename=uploaded_file,
            status="QUEUED",
            progress=0,
        )

        self.assertIsNotNone(job.id)
        self.assertEqual(job.status, "QUEUED")
        self.assertEqual(job.progress, 0)


class JobStatusAPITests(TestCase):

    def setUp(self):
        uploaded_file = SimpleUploadedFile(
            "status_test.csv",
            b"Name,Email\nKanak,kanak@example.com\n",
            content_type="text/csv",
        )

        self.job = ProcessingJob.objects.create(
            filename=uploaded_file,
            status="RUNNING",
            progress=45,
        )

    def test_get_job_status(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["status"], "RUNNING")
        self.assertEqual(data["progress"], 45)

    def test_nonexistent_job_returns_404(self):
        response = self.client.get(
            "/api/jobs/999999/"
        )

        self.assertEqual(response.status_code, 404)


class PreviewPaginationTests(TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()

        self.csv_path = os.path.join(
            self.temp_directory.name,
            "preview_test.csv",
        )

        dataframe = pd.DataFrame(
            {
                "Name": [
                    f"User {number}"
                    for number in range(1, 21)
                ],
                "Email": [
                    f"user{number}@example.com"
                    for number in range(1, 21)
                ],
                "Employee_ID": [
                    f"EMP-{number:04d}"
                    for number in range(1, 21)
                ],
            }
        )

        dataframe.to_csv(
            self.csv_path,
            index=False,
        )

        with open(self.csv_path, "rb") as file:
            uploaded_file = SimpleUploadedFile(
                "preview_test.csv",
                file.read(),
                content_type="text/csv",
            )

        self.job = ProcessingJob.objects.create(
            filename=uploaded_file,
            status="SUCCESS",
            progress=100,
        )

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_first_preview_page(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 1,
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_rows"], 20)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["rows"]), 10)

    def test_second_preview_page(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 2,
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["page"], 2)
        self.assertEqual(len(data["rows"]), 10)

        self.assertEqual(
            data["rows"][0]["Name"],
            "User 11",
        )

    def test_preview_columns(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data["columns"],
            [
                "Name",
                "Email",
                "Employee_ID",
            ],
        )


class UploadAPITests(TestCase):

    @patch("api.views.process_uploaded_file.delay")
    def test_successful_csv_upload_dispatches_celery_task(
        self,
        mock_delay,
    ):
        mock_task = MagicMock()
        mock_task.id = "test-celery-task-id"
        mock_delay.return_value = mock_task

        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                b"Name,Email,Employee_ID\n"
                b"Kanak,kanak@example.com,EMP-1001\n"
            ),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find employee IDs",
                "replacement": "XXXX",
                "target_column": "Employee_ID",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("job_id", data)

        self.assertEqual(
            data["task_id"],
            "test-celery-task-id",
        )

        job = ProcessingJob.objects.get(
            id=data["job_id"]
        )

        self.assertEqual(
            job.task_id,
            "test-celery-task-id",
        )

        mock_delay.assert_called_once_with(
            job.id,
            "Find employee IDs",
            "XXXX",
            "Employee_ID",
        )

    @patch("api.views.process_uploaded_file.delay")
    def test_upload_creates_processing_job(
        self,
        mock_delay,
    ):
        mock_task = MagicMock()
        mock_task.id = "another-task-id"
        mock_delay.return_value = mock_task

        uploaded_file = SimpleUploadedFile(
            "emails.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_column": "Email",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            ProcessingJob.objects.count(),
            1,
        )

        job = ProcessingJob.objects.first()

        self.assertEqual(job.status, "QUEUED")
        self.assertEqual(job.progress, 0)

    @patch("api.views.process_uploaded_file.delay")
    def test_missing_file_returns_400(
        self,
        mock_delay,
    ):
        response = self.client.post(
            "/api/upload/",
            {
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_column": "Email",
            },
        )

        self.assertEqual(response.status_code, 400)

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_missing_instruction_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            b"Name,Email\nKanak,kanak@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "",
                "replacement": "REDACTED",
                "target_column": "Email",
            },
        )

        self.assertEqual(response.status_code, 400)

        mock_delay.assert_not_called()


class CancellationAPITests(TestCase):

    def setUp(self):
        uploaded_file = SimpleUploadedFile(
            "cancel_test.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        self.job = ProcessingJob.objects.create(
            filename=uploaded_file,
            status="RUNNING",
            progress=50,
            task_id="celery-task-to-cancel",
        )

    @patch("api.views.celery_app.control.revoke")
    def test_running_job_can_be_cancelled(
        self,
        mock_revoke,
    ):
        response = self.client.post(
            f"/api/jobs/{self.job.id}/cancel/"
        )

        self.assertEqual(response.status_code, 200)

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "CANCELLED",
        )

        mock_revoke.assert_called_once_with(
            "celery-task-to-cancel",
            terminate=True,
        )

    @patch("api.views.celery_app.control.revoke")
    def test_successful_job_cannot_be_cancelled(
        self,
        mock_revoke,
    ):
        self.job.status = "SUCCESS"
        self.job.save()

        response = self.client.post(
            f"/api/jobs/{self.job.id}/cancel/"
        )

        self.assertEqual(response.status_code, 400)

        mock_revoke.assert_not_called()


class DownloadAPITests(TestCase):

    def test_incomplete_job_cannot_be_downloaded(self):
        uploaded_file = SimpleUploadedFile(
            "download_test.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        job = ProcessingJob.objects.create(
            filename=uploaded_file,
            status="RUNNING",
            progress=50,
        )

        response = self.client.get(
            f"/api/download/{job.id}/"
        )

        self.assertEqual(response.status_code, 400)

    def test_successful_job_can_be_downloaded(self):
        uploaded_file = SimpleUploadedFile(
            "download_input.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        processed_file = SimpleUploadedFile(
            "processed_download.csv",
            b"Email\nREDACTED\n",
            content_type="text/csv",
        )

        job = ProcessingJob.objects.create(
            filename=uploaded_file,
            output_file=processed_file,
            status="SUCCESS",
            progress=100,
        )

        response = self.client.get(
            f"/api/download/{job.id}/"
        )

        self.assertEqual(response.status_code, 200)

        content_disposition = response[
            "Content-Disposition"
        ]

        self.assertTrue(
            content_disposition.startswith(
                'attachment; filename="processed_download'
            )
        )

        self.assertTrue(
            content_disposition.endswith('.csv"')
        )