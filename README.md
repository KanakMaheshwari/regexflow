# NL-to-Regex Data Processing Platform

NL-to-Regex is a full-stack data processing platform that allows users to upload CSV or Excel datasets, describe a pattern in natural language, and replace matching values within a selected column.

The system uses a local Large Language Model through Ollama to convert natural-language instructions into regular expressions. Processing jobs run asynchronously using Celery and Redis, while Pandas and PySpark provide separate processing paths for small and large datasets.

The application includes job progress tracking, dataset preview, pagination, cancellation, processed-file downloads, regex caching, regex safety validation, automated testing, and task monitoring through Flower.

## Features

- Upload CSV and XLSX datasets
- Preview uploaded datasets
- Paginated dataset preview
- Select a target column
- Enter natural-language pattern instructions
- Generate regular expressions using Ollama
- Validate generated regex patterns
- Retry regex generation when generated patterns do not match sample data
- Cache generated regex patterns using Redis
- Replace matching values with user-defined replacements
- Process small datasets using Pandas
- Process large CSV datasets using PySpark
- Run processing jobs asynchronously using Celery
- Track job status and processing progress
- Cancel running jobs
- Download processed datasets
- Monitor Celery workers and tasks using Flower
- Handle successful, failed, and revoked tasks
- Validate file uploads and API inputs
- Automated Django test suite with 28 tests
- Docker-based backend infrastructure

## Technology Stack

### Frontend

- React
- Vite
- JavaScript
- CSS

### Backend

- Python
- Django
- Django REST Framework

### Data Processing

- Pandas
- PySpark

### AI and Pattern Generation

- Ollama
- Local Large Language Model

### Distributed Task Processing

- Celery
- Redis

### Monitoring

- Flower

### Infrastructure

- Docker
- Docker Compose

## System Architecture

```text
                         User
                           |
                           v
                    React Frontend
                           |
                           | HTTP API
                           v
                    Django REST API
                           |
                           | Creates Processing Job
                           v
                    Celery Task Queue
                           |
                           v
                         Redis
                  Broker + Regex Cache
                           |
                           v
                    Celery Worker
                           |
              +------------+------------+
              |                         |
              v                         v
        Ollama LLM               Processing Engine
              |                         |
              v                  +------+------+
       Regex Generation          |             |
              |                  v             v
              |               Pandas        PySpark
              |             Small Files    Large CSVs
              |                  |             |
              +------------------+-------------+
                                 |
                                 v
                         Processed Dataset
                                 |
                                 v
                         Django REST API
                                 |
                                 v
                         React Frontend


                    Flower Dashboard
                           |
                           v
                 Celery Task Monitoring
```

## Application Workflow

1. The user uploads a CSV or XLSX dataset.

2. The React frontend sends the file to the Django REST API.

3. Django validates:

   - file presence
   - file size
   - supported file format
   - processing instruction
   - replacement value
   - target column

4. Django creates a `ProcessingJob`.

5. The processing request is dispatched to Celery.

6. Celery executes the processing job asynchronously.

7. The worker reads sample values from the selected column.

8. The system checks Redis for an existing cached regex.

9. If no valid cached regex exists, the instruction and sample values are sent to Ollama.

10. Ollama generates a regex pattern.

11. The regex is validated for safety and tested against sample values.

12. Invalid or ineffective regex patterns are rejected and regenerated.

13. Valid regex patterns are cached in Redis.

14. The processing engine is selected based on the uploaded file.

15. Small files are processed using Pandas.

16. Large CSV files are processed using PySpark.

17. The processed file is stored by the backend.

18. The job status is updated to `SUCCESS`.

19. The user can download the processed dataset.

20. Celery task execution can be monitored through Flower.

## Processing Architecture

### Small Dataset Processing

Small CSV and XLSX files are processed using Pandas.

The complete dataset is loaded into memory and the generated regex is applied to the selected column.

```text
Uploaded File
     |
     v
   Pandas
     |
     v
Regex Replacement
     |
     v
Processed File
```

### Large Dataset Processing

Large CSV files are processed using PySpark.

The application reads only a small sample using Pandas for regex generation. The complete dataset is then processed using Spark.

```text
Large CSV
    |
    +----------------------+
    |                      |
    v                      v
Pandas Sample          PySpark
    |                      |
    v                      |
Ollama Regex                |
    |                      |
    +----------+-----------+
               |
               v
        Regex Replacement
               |
               v
        Processed CSV
```

The current large-file threshold is:

```text
10 MB
```

CSV files equal to or larger than this threshold use PySpark.

## Regex Generation

Natural-language instructions are converted into regex patterns using Ollama.

Example:

```text
Instruction:
Find email addresses
```

The system sends the instruction and sample values to the local LLM.

Example sample data:

```text
user1@example.com
user2@example.com
user3@example.com
```

The generated regex is validated before processing.

## Regex Validation

Generated regular expressions are checked before they can be used for dataset processing.

Validation includes:

- regex syntax validation
- regex length limits
- detection of unsafe nested quantifiers
- sample matching
- retrying ineffective generated patterns

This helps prevent invalid or potentially unsafe regex patterns from being executed against datasets.

## Redis Regex Caching

Generated regex patterns are stored in Redis.

The cache workflow is:

```text
Natural-Language Instruction
            |
            v
       Redis Lookup
            |
       +----+----+
       |         |
       v         v
   Cache Hit   Cache Miss
       |         |
       |         v
       |      Ollama
       |         |
       |         v
       |    Generate Regex
       |         |
       |         v
       |     Cache Regex
       |         |
       +----+----+
            |
            v
       Process Dataset
```

Caching reduces unnecessary LLM requests when the same processing instruction is used again.

## Asynchronous Processing

Celery handles data-processing tasks asynchronously.

This prevents long-running processing operations from blocking Django API requests.

The asynchronous workflow is:

```text
React
   |
   v
Django API
   |
   v
Redis Broker
   |
   v
Celery Worker
   |
   v
Processing Task
```

## Job States

Processing jobs can have the following states:

```text
QUEUED
RUNNING
SUCCESS
FAILED
CANCELLED
```

Celery and Flower additionally expose task execution states such as:

```text
SUCCESS
FAILURE
REVOKED
```

The project has verified all three major Celery outcomes through Flower.

## Task Cancellation

Running tasks can be cancelled through the application.

The Django backend revokes the Celery task using its task ID.

Cancelled tasks are:

- marked as `CANCELLED` in the application database
- revoked through Celery
- displayed as `REVOKED` in Flower

## Flower Monitoring

Flower provides monitoring for Celery workers and tasks.

The dashboard displays:

- worker availability
- successful tasks
- failed tasks
- revoked tasks
- task arguments
- task execution time
- task results

Flower is available locally at:

```text
http://localhost:5555
```

## API Endpoints

### Health Check

```text
GET /api/hello/
```

### Upload Dataset

```text
POST /api/upload/
```

Request fields:

```text
file
instruction
replacement
target_column
```

### Get Job Status

```text
GET /api/jobs/<job_id>/
```

### Preview Dataset

```text
GET /api/jobs/<job_id>/preview/
```

Optional query parameters:

```text
page
page_size
```

### Cancel Job

```text
POST /api/jobs/<job_id>/cancel/
```

### Download Processed Dataset

```text
GET /api/download/<job_id>/
```

## Project Structure

```text
NLtoRegex/
|
├── backend/
│   |
│   ├── api/
│   │   ├── cache.py
│   │   ├── llm_service.py
│   │   ├── models.py
│   │   ├── regex_validator.py
│   │   ├── services.py
│   │   ├── spark_service.py
│   │   ├── tasks.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   |
│   ├── config/
│   │   ├── celery.py
│   │   ├── settings.py
│   │   └── urls.py
│   |
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
|
├── frontend/
│   |
│   ├── public/
│   |
│   ├── src/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   |
│   ├── package.json
│   └── vite.config.js
|
├── docker-compose.yml
├── generate_large_csv.py
├── .gitignore
└── README.md
```

## Prerequisites

Before running the project, install:

- Docker
- Docker Compose
- Node.js
- npm
- Ollama

## Running Ollama

Ollama runs locally and is used for regex generation.

Start Ollama before processing datasets.

Ensure the required model is installed locally.

The exact model configuration is defined in:

```text
backend/api/llm_service.py
```

## Backend Setup

From the project root, build and start the Docker services:

```bash
docker compose up --build
```

This starts:

- Django
- Redis
- Celery
- Flower

Check running containers:

```bash
docker compose ps
```

Expected services:

```text
django_backend
redis_server
celery_worker
flower_dashboard
```

## Database Setup

Run migrations using:

```bash
docker compose exec django python manage.py makemigrations
```

Then:

```bash
docker compose exec django python manage.py migrate
```

## Frontend Setup

Open another terminal.

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open the frontend URL displayed by Vite in the terminal.

## Running Automated Tests

Run the Django test suite from the project root:

```bash
docker compose exec django python manage.py test api
```

The current test suite contains:

```text
28 automated tests
```

The tests cover:

- regex safety validation
- invalid regex syntax
- unsafe nested quantifiers
- regex length validation
- processing job creation
- job status API
- missing jobs
- dataset preview
- pagination
- invalid preview pages
- invalid page parameters
- upload API
- Celery task dispatch
- missing files
- empty files
- unsupported file formats
- missing instructions
- missing replacement values
- missing target columns
- job cancellation
- completed-job cancellation rejection
- processed-file downloads
- incomplete-job download rejection

## Large Dataset Testing

The repository contains:

```text
generate_large_csv.py
```

This script can be used to generate a large test dataset.

The generated dataset itself is excluded from Git to avoid storing large generated artifacts in the repository.

Large CSV files can be used to verify:

- PySpark processing
- asynchronous Celery execution
- job progress
- cancellation
- Flower monitoring
- processed-file downloads

The application has been tested with a dataset containing:

```text
500,000 rows
```

## Verified Flower Task States

The following Celery outcomes have been tested successfully.

### Successful Task

```text
SUCCESS
```

The dataset is processed and the output file becomes available for download.

### Failed Task

```text
FAILURE
```

Exceptions are raised by the Celery task after the application job is marked as failed.

This ensures Flower correctly displays failed tasks instead of incorrectly recording them as successful tasks returning `False`.

### Cancelled Task

```text
REVOKED
```

Running jobs can be cancelled through the application and are correctly displayed as revoked tasks in Flower.

## Input Validation

The upload API validates:

- missing files
- empty files
- unsupported file extensions
- missing processing instructions
- missing replacement values
- missing target columns

The preview API validates:

- invalid page numbers
- invalid page formats
- page sizes below the minimum
- page sizes above the maximum

## Error Handling

The system handles:

- invalid file formats
- empty datasets
- missing columns
- invalid regex patterns
- unsafe regex patterns
- ineffective LLM-generated patterns
- Ollama connection failures
- PySpark processing failures
- missing processed files
- invalid pagination parameters
- task failures
- task cancellation

## Current Limitations

- Ollama must be running locally.
- LLM regex generation quality depends on the selected local model.
- PySpark processing currently runs in local mode.
- Large-file processing currently supports CSV files.
- XLSX files are processed using Pandas.
- SQLite is used as the development database.
- The React frontend runs separately from Docker.
- Flower is intended for local development and should be secured before production deployment.
- Celery task termination behavior can depend on the worker environment and operating system.

## Future Improvements

Potential future improvements include:

- PostgreSQL database support
- authentication and user accounts
- user-specific processing jobs
- processing history
- multiple simultaneous transformations
- multiple target-column selection
- improved LLM prompting
- support for additional file formats
- distributed Spark clusters
- cloud object storage
- production deployment
- secured Flower authentication
- configurable processing thresholds
- more detailed performance metrics
- frontend automated testing
- CI/CD pipelines

## Development Status

The current implementation includes:

- working React frontend
- working Django REST API
- local Ollama integration
- regex generation and validation
- Redis regex caching
- Celery asynchronous processing
- Pandas processing
- PySpark large-file processing
- dataset preview
- pagination
- progress tracking
- task cancellation
- processed-file downloads
- Flower monitoring
- API input validation
- error handling
- 28 passing automated tests
- successful 500,000-row dataset processing

The core implementation and testing phases are complete.