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

```text
Select Dataset
      |
      v
Load Dataset Columns
      |
      v
Select Target Columns
      |
      v
Choose Transformation
      |
      v
Enter Natural-Language Instruction
      |
      v
Process Dataset
      |
      v
Monitor Job Progress
      |
      v
Preview / Download Result
```

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

```text
http://localhost:8000/api
```

The API base URL is configured in:

```text
src/App.jsx
```

## Project Structure

```text
frontend/
│
├── public/
│
├── src/
│   ├── App.css
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── eslint.config.js
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
└── README.md
```

## Running with Docker Compose

From the root project directory:

```bash
docker compose up --build
```

The frontend is available at:

```text
http://localhost:5173
```

## Running Locally

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

## Linting

Run:

```bash
npm run lint
```

Or, when using Docker Compose:

```bash
docker compose exec frontend npm run lint
```

## Production Build

Run:

```bash
npm run build
```

Or, when using Docker Compose:

```bash
docker compose exec frontend npm run build
```

The current frontend implementation has been verified with:

```text
ESLint             PASS
Production Build   PASS
```

## Related Documentation

For complete project architecture, backend setup, Celery and Redis configuration, Ollama integration, PySpark processing, automated tests, design decisions, and deployment information, see the root project `README.md`.