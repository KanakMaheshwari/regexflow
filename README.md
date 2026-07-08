# RegexFlow

RegexFlow is a distributed natural-language data processing platform built with Django, React, Celery, Redis, PySpark, and OpenAI.

The application allows users to upload CSV or Excel datasets, select one or more target columns, describe a text pattern in natural language, and asynchronously transform matching data at scale.

The natural-language instruction is converted into a safe Python-compatible regular expression using an LLM. The generated regex is validated, cached in Redis, and applied to the selected columns through either Pandas or PySpark depending on the size and format of the uploaded dataset.

The frontend provides live processing progress, processed-data preview with pagination, job cancellation, and result download.

---

## Features

### Natural Language to Regex

Users can describe patterns using natural language.

Examples:

- Find email addresses
- Find phone numbers
- Find dates in YYYY-MM-DD format
- Find URLs
- Find customer IDs beginning with CUST-

The instruction is sent to OpenAI, which generates a Python-compatible regular expression.

Before execution, every generated regex is validated to reject invalid or potentially unsafe expressions.

---

## Data Transformations

RegexFlow supports three transformation types.

### 1. Replace Matches

Replaces matching patterns with a user-specified value.

Example:

```text
Input:
john@example.com

Instruction:
Find email addresses

Replacement:
REDACTED

Output:
REDACTED
```

### 2. Extract Pattern Matches

Extracts only the part of the target-column value that matches the generated regex.

Example:

```text
Input:
Contact John at john@example.com

Instruction:
Find email addresses

Output:
john@example.com
```

### 3. Privacy Masking

Replaces matching values with a masked representation.

Example:

```text
Input:
john@example.com

Instruction:
Find email addresses

Output:
********
```

The Extract and Privacy Masking transformations are additional transformations implemented through the same asynchronous data-processing pipeline.

---

## Technology Stack

### Frontend

- React
- Vite
- Axios
- CSS

### Backend

- Django
- Django REST Framework
- Pandas

### Distributed Processing

- Celery
- Redis
- PySpark

### LLM Integration

- OpenAI API

### Development and Infrastructure

- Docker
- Docker Compose
- Flower
- Git
- GitHub

---

## System Architecture

```text
                         User
                           |
                           v
                    React Frontend
                           |
                           | HTTP / REST API
                           v
                     Django Backend
                           |
                           | Create ProcessingJob
                           |
                           | Dispatch Async Task
                           v
                      Redis Broker
                           |
                           v
                      Celery Worker
                           |
              +------------+------------+
              |                         |
              v                         v
         Redis Cache                 OpenAI API
              |                         |
              |                 Natural Language
              |                    to Regex
              |                         |
              +------------+------------+
                           |
                           v
                   Regex Validation
                           |
                           v
                  Processing Engine
                           |
                 +---------+---------+
                 |                   |
                 v                   v
              Pandas              PySpark
          Small Datasets       Large CSV Files
                 |                   |
                 +---------+---------+
                           |
                           v
                    Processed File
                           |
                           v
                 Paginated Preview
                           |
                           v
                      File Download
```

---

## Processing Workflow

1. The user selects a CSV or Excel file.

2. The frontend sends the file to the inspection endpoint.

3. Django reads a limited sample of the dataset and returns the available columns.

4. The user selects one or more target columns.

5. The user selects a transformation type.

6. The user enters a natural-language pattern description.

7. For Replace transformations, the user also provides a replacement value.

8. The frontend uploads the processing request.

9. Django creates a persistent `ProcessingJob`.

10. The API immediately returns the job ID without waiting for processing to complete.

11. The processing task is dispatched to Celery through Redis.

12. The Celery worker checks Redis for a previously cached regex.

13. If no cached regex exists, OpenAI generates a regex from the natural-language instruction and dataset samples.

14. The generated regex is validated for syntax and safety.

15. The validated regex is cached in Redis.

16. The appropriate processing engine is selected.

17. Small datasets and Excel files are processed with Pandas.

18. Large CSV files are processed using PySpark.

19. Celery reports processing progress.

20. The React frontend polls the job-status endpoint.

21. After processing reaches `SUCCESS`, the frontend automatically requests the processed output.

22. The processed dataset is displayed using paginated preview endpoints.

23. The completed output file can be downloaded.

---

## Asynchronous Processing

File processing is performed outside the Django request-response cycle.

Django is responsible for:

- validating API requests;
- creating persistent processing jobs;
- dispatching Celery tasks;
- returning job information;
- reporting job status and progress;
- serving paginated previews;
- serving completed files.

Celery is responsible for:

- reading uploaded datasets;
- obtaining sample values;
- retrieving or generating regex patterns;
- validating regex patterns;
- selecting the processing engine;
- applying transformations;
- saving processed output;
- reporting task progress;
- handling retryable failures.

This design prevents long-running processing operations from blocking the web server.

---

## Job Status and Progress

Processing jobs are persisted in the database.

Supported job states include:

```text
QUEUED
RUNNING
SUCCESS
FAILED
CANCELLED
```

The frontend polls the job-status API and displays live progress.

Processing progress is reported at major pipeline stages, including:

- task startup;
- dataset validation;
- regex generation;
- regex validation;
- data processing;
- output combination;
- result storage;
- completion.

---

## Redis

Redis performs three responsibilities in RegexFlow.

### Celery Message Broker

Django sends processing tasks to Redis.

Celery workers retrieve tasks asynchronously.

### Celery Result Backend

Celery task state and execution information are stored using Redis.

### Regex Cache

LLM-generated regex patterns are cached using the natural-language instruction as the cache key.

When an identical instruction is submitted again, RegexFlow attempts to reuse the cached regex instead of making another LLM API request.

Cached expressions are validated again before use.

---

## OpenAI Integration

RegexFlow uses the OpenAI API to convert natural-language descriptions into regular expressions.

Example:

```text
Natural Language Instruction:

Find email addresses
```

Possible generated regex:

```text
\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b
```

The LLM is instructed to return structured JSON containing exactly one regex pattern.

Dataset sample values are included in the request to improve generation accuracy.

If an invalid or unsafe regex is generated, RegexFlow provides failure feedback and attempts generation again.

Transient API, rate-limit, timeout, and network failures are retried with exponential backoff.

---

## Regex Safety

LLM-generated expressions are never applied directly without validation.

RegexFlow performs validation before execution.

The validation layer checks for:

- invalid regular-expression syntax;
- dangerous nested quantifiers;
- potentially catastrophic backtracking patterns;
- unnecessarily unsafe expressions.

Unsafe expressions are rejected.

Cached expressions are also validated again before execution.

---

## Pandas and PySpark Processing Strategy

RegexFlow uses a hybrid processing architecture.

### Pandas

Pandas is used for:

- small CSV datasets;
- Excel files;
- efficient local processing.

### PySpark

PySpark is used for large CSV datasets.

Large datasets are processed using Spark DataFrame transformations instead of Python row-by-row iteration.

Spark distributes dataset processing across partitions, allowing transformations to scale more effectively as dataset size increases.

The current implementation selects PySpark when a CSV file reaches the configured file-size threshold.

---

## Partitioning and Parallelism

PySpark performs transformations over distributed DataFrame partitions.

Regex transformations are applied using Spark SQL/DataFrame operations rather than manual Python loops.

This approach was selected because:

- partitions can be processed in parallel;
- data transformations remain within Spark's execution engine;
- processing scales better than row-by-row Python iteration;
- Spark can process datasets larger than the available memory of a single application process.

Spark output may contain multiple partition files.

RegexFlow combines the generated CSV partition files into a single downloadable result while preserving only one CSV header.

### Trade-off

Combining partition files into one downloadable file introduces additional output-processing overhead.

For a larger production system, processed data could instead remain in distributed object storage or a columnar format such as Parquet and be queried directly using paginated APIs.

---

## Processed Data Preview

The frontend supports two preview states.

### Original Dataset Preview

Before processing completes, the UI displays the original uploaded dataset.

### Processed Data Preview

After the job reaches `SUCCESS`, the frontend automatically requests the preview again.

The backend detects the completed job and reads from the processed output file.

The frontend then displays:

```text
Processed Data Preview
```

Pagination requests continue to read from the processed output.

This prevents the application from attempting to send an entire large dataset to the browser.

---

## API Endpoints

### Health Check

```text
GET /api/hello/
```

### Inspect Dataset

```text
POST /api/inspect/
```

Reads a limited dataset sample and returns available columns and preview rows.

### Upload and Process Dataset

```text
POST /api/upload/
```

Creates a processing job and dispatches asynchronous work.

### Get Job Status

```text
GET /api/jobs/<job_id>/
```

Returns job status and progress.

### Preview Dataset

```text
GET /api/jobs/<job_id>/preview/
```

Supported query parameters:

```text
page
page_size
```

Before processing completes, the endpoint previews the original dataset.

After successful processing, the endpoint previews the processed dataset.

### Cancel Job

```text
POST /api/jobs/<job_id>/cancel/
```

Cancels an active processing job.

### Download Result

```text
GET /api/download/<job_id>/
```

Downloads the completed output file.

---

## Project Structure

```text
NLtoRegex/
│
├── backend/
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
│   │
│   ├── config/
│   │   ├── celery.py
│   │   ├── settings.py
│   │   └── urls.py
│   │
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── generate_large_csv.py
└── README.md
```

---

## Environment Variables

Create a `.env` file in the project root.

```text
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini

VITE_API_BASE_URL=http://localhost:8000/api

DJANGO_SECRET_KEY=your_django_secret_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
```

Never commit the `.env` file.

The repository should include an `.env.example` file containing variable names and safe placeholder values instead.

---

## Running the Application

### Prerequisites

Install:

- Docker
- Docker Compose

An OpenAI API key is also required.

### Clone the Repository

```bash
git clone <repository-url>
cd NLtoRegex
```

### Configure Environment Variables

Create the local environment file:

```bash
cp .env.example .env
```

Add your OpenAI API key to `.env`.

### Start the Application

```bash
docker compose up --build
```

The development services are available at:

```text
Frontend:
http://localhost:5173

Django API:
http://localhost:8000

Flower:
http://localhost:5555
```

---

## Running Tests

Run the Django test suite:

```bash
docker compose exec django python manage.py test api
```

---

## Frontend Validation

Run ESLint:

```bash
docker compose exec frontend npm run lint
```

Create a production frontend build:

```bash
docker compose exec frontend npm run build
```

---

## Full Validation

```bash
docker compose exec django python manage.py check

docker compose exec django python manage.py test api

docker compose exec frontend npm run lint

docker compose exec frontend npm run build
```

---

## Large Dataset Testing

The repository includes a dataset-generation utility:

```text
generate_large_csv.py
```

This can be used to create a sizeable CSV dataset for testing the PySpark processing pipeline.

Example workflow:

```bash
python generate_large_csv.py
```

Upload the generated dataset through the React interface and submit a processing instruction.

During the test, verify:

- the API returns a job ID without waiting for completion;
- the UI remains responsive;
- the Celery worker processes the task;
- the job reports progress;
- the large CSV is processed through the PySpark path;
- the job reaches `SUCCESS`;
- processed data is displayed using pagination;
- the completed result can be downloaded.

---

## Error Handling

RegexFlow handles errors across multiple application layers.

### Frontend

- missing file;
- missing natural-language instruction;
- missing target columns;
- missing replacement value;
- upload failures;
- preview failures;
- job-status failures;
- processing failures.

### Django API

- missing files;
- empty files;
- unsupported file types;
- invalid transformations;
- invalid target-column requests;
- invalid pagination;
- missing output files.

### Celery

- failed processing jobs;
- retryable OpenAI errors;
- exponential retry backoff;
- task cancellation;
- failed output generation.

### Regex Validation

- invalid regex syntax;
- potentially unsafe regex structures.

---

## Monitoring

RegexFlow includes Flower for basic Celery observability.

Flower can be accessed locally at:

```text
http://localhost:5555
```

It can be used to inspect:

- Celery workers;
- task execution;
- task states;
- task failures.

---

## Testing Strategy

The backend test suite covers key application functionality including:

- job creation;
- file uploads;
- file validation;
- target-column validation;
- transformation validation;
- job status;
- pagination;
- file downloads;
- task behavior;
- regex validation;
- cache behavior;
- Pandas transformations;
- PySpark-related processing logic.

Frontend quality checks include:

- ESLint validation;
- production build validation.

Manual end-to-end testing covers:

- CSV uploads;
- Excel uploads;
- OpenAI regex generation;
- Redis regex caching;
- Replace transformation;
- Extract Pattern Matches transformation;
- Privacy Masking transformation;
- multiple target columns;
- job progress;
- job cancellation;
- processed-data preview;
- pagination;
- file downloads.

---

## Design Decisions

### Why Celery?

Data processing and LLM calls may take significantly longer than normal HTTP requests.

Celery allows these operations to execute asynchronously without blocking Django.

### Why Redis?

Redis provides:

- Celery message brokering;
- Celery result storage;
- low-latency regex caching.

### Why PySpark?

PySpark allows large datasets to be processed using distributed DataFrame transformations across partitions.

### Why Use a Hybrid Pandas/PySpark Strategy?

Starting Spark for very small datasets introduces unnecessary overhead.

Pandas provides faster and simpler processing for smaller datasets, while PySpark provides a scalable path for larger CSV files.

### Why Polling?

Polling provides a simple and reliable method for displaying asynchronous job progress.

A production extension could use WebSockets or Server-Sent Events for real-time status updates.

---

## Current Trade-offs and Limitations

- SQLite is used for development. A production deployment should use PostgreSQL or another production-grade database.
- The frontend currently uses polling rather than WebSockets.
- Excel files are processed with Pandas because Spark does not provide native XLSX support in the current implementation.
- Large-file processing currently uses a configurable file-size threshold to select PySpark.
- Spark CSV partition outputs are combined into a single downloadable file, which adds finalisation overhead.
- Uploaded and processed files currently use local filesystem storage. A production system should use persistent object storage.
- Regex caching currently uses the natural-language instruction as the primary cache identity.
- The LLM generates regex patterns, while replacement expressions are supplied separately by the user.

---

## Security Considerations

- API keys are stored in environment variables.
- `.env` is excluded from Git.
- Generated regex patterns are validated before execution.
- Cached regex patterns are revalidated before use.
- Production deployments should use a strong Django secret key.
- Django debug mode should be disabled in production.
- CORS and allowed hosts should be restricted to deployed domains.

---

## Deployment

The application is designed for container-based deployment.

A production deployment requires:

- Django web service;
- Celery worker;
- Redis;
- PySpark-compatible processing runtime;
- persistent database;
- persistent file storage;
- frontend hosting;
- environment-based OpenAI configuration.

Production environment variables should include:

```text
OPENAI_API_KEY
OPENAI_MODEL
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
VITE_API_BASE_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

The deployment URL will be added after deployment.

---

## Demo Video

A short demonstration video will be added before final submission.

The video will demonstrate:

1. uploading a dataset;
2. loading dataset columns;
3. selecting target columns;
4. entering a natural-language instruction;
5. selecting a transformation;
6. starting asynchronous processing;
7. viewing live job progress;
8. reaching successful completion;
9. viewing the processed-data preview;
10. navigating paginated processed results;
11. downloading the completed file.

Demo video:

```text
To be added after deployment and final recording.
```

---

## Future Improvements

Potential future improvements include:

- PostgreSQL;
- cloud object storage;
- WebSockets or Server-Sent Events;
- authentication and user-specific jobs;
- configurable Spark clusters;
- Parquet output;
- distributed processed-data querying;
- improved row-level progress reporting;
- richer LLM-generated transformation plans;
- automated frontend testing;
- CI/CD pipelines.

---

## Conclusion

RegexFlow demonstrates an end-to-end distributed natural-language data-processing architecture.

The platform combines:

- React for the user interface;
- Django REST APIs for job management;
- Celery for asynchronous task execution;
- Redis for brokering, results, and caching;
- OpenAI for natural-language-to-regex generation;
- regex safety validation;
- Pandas for smaller datasets;
- PySpark for scalable large-file transformations;
- paginated processed-data previews;
- Flower for worker monitoring;
- Docker Compose for local orchestration.

The result is a responsive data-processing application that converts natural-language instructions into validated regex transformations and executes them asynchronously across uploaded datasets.