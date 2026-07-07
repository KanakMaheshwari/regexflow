import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import ProcessingJob
from .regex_validator import validate_regex_safety
from .tasks import apply_pandas_transformation


class RegexSafetyValidatorTests(TestCase):

    def test_valid_email_regex(self):
        regex = (
            r"[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        )

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


class PandasTransformationTests(TestCase):

    def setUp(self):
        self.dataframe = pd.DataFrame(
            {
                "Email": [
                    "kanak@example.com",
                    "alex@example.com",
                    "invalid-value",
                ],
                "Backup_Email": [
                    "backup1@example.com",
                    "backup2@example.com",
                    "another-invalid-value",
                ],
            }
        )

        self.email_regex = (
            r"[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        )

    def test_replace_transformation(self):
        result = apply_pandas_transformation(
            dataframe=self.dataframe.copy(),
            matching_columns=["Email"],
            regex=self.email_regex,
            replacement="REDACTED",
            transformation_type="replace",
        )

        self.assertEqual(
            result.loc[0, "Email"],
            "REDACTED",
        )

        self.assertEqual(
            result.loc[1, "Email"],
            "REDACTED",
        )

        self.assertEqual(
            result.loc[2, "Email"],
            "invalid-value",
        )

    def test_extract_transformation(self):
        result = apply_pandas_transformation(
            dataframe=self.dataframe.copy(),
            matching_columns=["Email"],
            regex=self.email_regex,
            replacement="",
            transformation_type="extract",
        )

        self.assertEqual(
            result.loc[0, "Email"],
            "kanak@example.com",
        )

        self.assertEqual(
            result.loc[1, "Email"],
            "alex@example.com",
        )

        self.assertEqual(
            result.loc[2, "Email"],
            "",
        )

    def test_mask_transformation(self):
        result = apply_pandas_transformation(
            dataframe=self.dataframe.copy(),
            matching_columns=["Email"],
            regex=self.email_regex,
            replacement="",
            transformation_type="mask",
        )

        self.assertEqual(
            result.loc[0, "Email"],
            "********",
        )

        self.assertEqual(
            result.loc[1, "Email"],
            "********",
        )

        self.assertEqual(
            result.loc[2, "Email"],
            "invalid-value",
        )

    def test_transformation_applies_to_multiple_columns(self):
        result = apply_pandas_transformation(
            dataframe=self.dataframe.copy(),
            matching_columns=[
                "Email",
                "Backup_Email",
            ],
            regex=self.email_regex,
            replacement="REDACTED",
            transformation_type="replace",
        )

        self.assertEqual(
            result.loc[0, "Email"],
            "REDACTED",
        )

        self.assertEqual(
            result.loc[0, "Backup_Email"],
            "REDACTED",
        )

    def test_invalid_transformation_type_raises_error(self):
        with self.assertRaises(ValueError):
            apply_pandas_transformation(
                dataframe=self.dataframe.copy(),
                matching_columns=["Email"],
                regex=self.email_regex,
                replacement="",
                transformation_type="invalid",
            )


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


class InspectFileAPITests(TestCase):

    def test_inspect_csv_returns_columns_and_rows(self):
        uploaded_file = SimpleUploadedFile(
            "inspect.csv",
            (
                b"Name,Email,Employee_ID\n"
                b"Kanak,kanak@example.com,EMP-1001\n"
                b"Alex,alex@example.com,EMP-1002\n"
            ),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/inspect/",
            {
                "file": uploaded_file,
            },
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

        self.assertEqual(len(data["rows"]), 2)

        self.assertEqual(
            data["rows"][0]["Name"],
            "Kanak",
        )

    def test_inspect_returns_maximum_ten_rows(self):
        csv_content = "Name,Email\n"

        for number in range(1, 21):
            csv_content += (
                f"User {number},"
                f"user{number}@example.com\n"
            )

        uploaded_file = SimpleUploadedFile(
            "inspect_large.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/inspect/",
            {
                "file": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(response.json()["rows"]),
            10,
        )

    def test_inspect_missing_file_returns_400(self):
        response = self.client.post(
            "/api/inspect/"
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "No file uploaded.",
        )

    def test_inspect_empty_file_returns_400(self):
        uploaded_file = SimpleUploadedFile(
            "empty.csv",
            b"",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/inspect/",
            {
                "file": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "Uploaded file is empty.",
        )

    def test_inspect_unsupported_file_returns_400(self):
        uploaded_file = SimpleUploadedFile(
            "document.txt",
            b"Some text",
            content_type="text/plain",
        )

        response = self.client.post(
            "/api/inspect/",
            {
                "file": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            (
                "Unsupported file format. "
                "Only CSV and XLSX files are supported."
            ),
        )


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

    def test_invalid_preview_page(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 5,
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "Invalid page number.",
        )

    def test_preview_page_below_one(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 0,
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "Page must be at least 1.",
        )

    def test_invalid_preview_page_format(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": "invalid",
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "Page and page size must be valid integers.",
        )

    def test_preview_page_size_below_one(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 1,
                "page_size": 0,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_preview_page_size_above_limit(self):
        response = self.client.get(
            f"/api/jobs/{self.job.id}/preview/",
            {
                "page": 1,
                "page_size": 101,
            },
        )

        self.assertEqual(response.status_code, 400)


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

        job = ProcessingJob.objects.get(
            id=data["job_id"]
        )

        mock_delay.assert_called_once_with(
            job.id,
            "Find employee IDs",
            "XXXX",
            ["Employee_ID"],
            "replace",
        )

    @patch("api.views.process_uploaded_file.delay")
    def test_multiple_target_columns_dispatches_celery_task(
        self,
        mock_delay,
    ):
        mock_task = MagicMock()
        mock_task.id = "multiple-columns-task-id"
        mock_delay.return_value = mock_task

        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                b"Name,Email,Backup_Email\n"
                b"Kanak,kanak@example.com,"
                b"backup@example.com\n"
            ),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_columns": json.dumps(
                    [
                        "Email",
                        "Backup_Email",
                    ]
                ),
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        job = ProcessingJob.objects.get(
            id=data["job_id"]
        )

        self.assertEqual(
            data["target_columns"],
            [
                "Email",
                "Backup_Email",
            ],
        )

        self.assertEqual(
            data["transformation_type"],
            "replace",
        )

        mock_delay.assert_called_once_with(
            job.id,
            "Find email addresses",
            "REDACTED",
            [
                "Email",
                "Backup_Email",
            ],
            "replace",
        )

    @patch("api.views.process_uploaded_file.delay")
    def test_extract_transformation_dispatches_task(
        self,
        mock_delay,
    ):
        mock_task = MagicMock()
        mock_task.id = "extract-task-id"
        mock_delay.return_value = mock_task

        uploaded_file = SimpleUploadedFile(
            "extract.csv",
            b"Text\nContact user@example.com today\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "",
                "target_columns": json.dumps(["Text"]),
                "transformation_type": "extract",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        job = ProcessingJob.objects.get(
            id=data["job_id"]
        )

        self.assertEqual(
            data["transformation_type"],
            "extract",
        )

        mock_delay.assert_called_once_with(
            job.id,
            "Find email addresses",
            "",
            ["Text"],
            "extract",
        )

    @patch("api.views.process_uploaded_file.delay")
    def test_mask_transformation_dispatches_task(
        self,
        mock_delay,
    ):
        mock_task = MagicMock()
        mock_task.id = "mask-task-id"
        mock_delay.return_value = mock_task

        uploaded_file = SimpleUploadedFile(
            "mask.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "",
                "target_columns": json.dumps(["Email"]),
                "transformation_type": "mask",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        job = ProcessingJob.objects.get(
            id=data["job_id"]
        )

        self.assertEqual(
            data["transformation_type"],
            "mask",
        )

        mock_delay.assert_called_once_with(
            job.id,
            "Find email addresses",
            "",
            ["Email"],
            "mask",
        )

    @patch("api.views.process_uploaded_file.delay")
    def test_invalid_transformation_type_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "invalid.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "",
                "target_columns": json.dumps(["Email"]),
                "transformation_type": "invalid",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            (
                "Transformation type must be "
                "replace, extract, or mask."
            ),
        )

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_invalid_target_columns_json_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_columns": "invalid-json",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            (
                "Target columns must be "
                "a valid JSON array of strings."
            ),
        )

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_empty_target_columns_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_columns": json.dumps([]),
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "At least one target column is required.",
        )

        mock_delay.assert_not_called()

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

    @patch("api.views.process_uploaded_file.delay")
    def test_empty_file_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "empty.csv",
            b"",
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

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "Uploaded file is empty.",
        )

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_unsupported_file_format_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "document.txt",
            b"Some text data",
            content_type="text/plain",
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

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            (
                "Unsupported file format. "
                "Only CSV and XLSX files are supported."
            ),
        )

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_missing_replacement_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "",
                "target_column": "Email",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            (
                "Replacement value is required "
                "for replace transformation."
            ),
        )

        mock_delay.assert_not_called()

    @patch("api.views.process_uploaded_file.delay")
    def test_missing_target_column_returns_400(
        self,
        mock_delay,
    ):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            b"Email\nuser@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/upload/",
            {
                "file": uploaded_file,
                "instruction": "Find email addresses",
                "replacement": "REDACTED",
                "target_column": "",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["error"],
            "At least one target column is required.",
        )

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