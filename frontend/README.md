cat > frontend/README.md <<'EOF'
# NL-to-Regex Frontend

The frontend for the NL-to-Regex Distributed Data Processing Platform is built using React and Vite.

It provides the user interface for uploading datasets, inspecting dataset columns, selecting target columns, configuring transformations, monitoring asynchronous processing jobs, previewing datasets, cancelling jobs, and downloading processed results.

## Technology Stack

- React
- Vite
- JavaScript
- CSS
- Axios

## Features

- Upload CSV and XLSX datasets
- Inspect datasets before processing
- Dynamically load dataset columns
- Select one or more target columns
- Enter natural-language processing instructions
- Select Replace, Extract, or Mask transformations
- Enter replacement values for Replace transformations
- Submit asynchronous processing jobs
- Display job status and progress
- Preview dataset records
- Navigate paginated previews
- Cancel active jobs
- Download processed datasets
- Display validation and processing errors

## Application Workflow

Select Dataset → Load Dataset Columns → Select Target Columns → Choose Transformation → Enter Instruction → Process Dataset → Monitor Progress → Download Result

## Transformation Modes

### Replace

Replaces regex matches with a user-provided replacement value.

### Extract

Extracts content matching the generated regular expression.

### Mask

Masks content matching the generated regular expression.

## Backend Communication

The frontend communicates with the Django REST API using Axios.

The default backend API URL is:

http://localhost:8000/api

## Running with Docker Compose

From the root project directory:

docker compose up --build

The frontend is available at:

http://localhost:5173

## Linting

docker compose exec frontend npm run lint

## Production Build

docker compose exec frontend npm run build

## Related Documentation

For complete project documentation, architecture, backend setup, Celery, Redis, Ollama, PySpark, testing, and design decisions, see the root project README.
EOF