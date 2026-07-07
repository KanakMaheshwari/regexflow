import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("");
  const [progress, setProgress] = useState(0);

  const [instruction, setInstruction] = useState("");
  const [replacement, setReplacement] = useState("");
  const [targetColumn, setTargetColumn] = useState("");

  const [previewColumns, setPreviewColumns] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [previewPage, setPreviewPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalRows, setTotalRows] = useState(0);

  const checkJobStatus = async (id) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/jobs/${id}/`
      );

      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      if (response.data.status === "SUCCESS") {
        setMessage("Processing completed successfully.");
      }

      if (response.data.status === "FAILED") {
        setMessage("Processing failed.");
      }

      if (response.data.status === "CANCELLED") {
        setMessage("Job cancelled.");
      }

      return response.data.status;
    } catch (error) {
      console.error(error);
      setMessage("Unable to check job status.");
      return "ERROR";
    }
  };

  const fetchPreview = async (id, page = 1) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/jobs/${id}/preview/`,
        {
          params: {
            page,
            page_size: 10,
          },
        }
      );

      setPreviewColumns(response.data.columns);
      setPreviewRows(response.data.rows);
      setPreviewPage(response.data.page);
      setTotalPages(response.data.total_pages);
      setTotalRows(response.data.total_rows);
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Unable to load file preview."
      );
    }
  };

  const uploadFile = async () => {
    if (!file) {
      setMessage("Please select a CSV or Excel file.");
      return;
    }

    if (!instruction.trim()) {
      setMessage("Please enter a processing instruction.");
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("instruction", instruction);
    formData.append("replacement", replacement);
    formData.append("target_column", targetColumn);

    try {
      setMessage("Uploading dataset...");
      setProgress(0);
      setJobStatus("");

      setPreviewColumns([]);
      setPreviewRows([]);
      setPreviewPage(1);
      setTotalPages(0);
      setTotalRows(0);

      const response = await axios.post(
        "http://localhost:8000/api/upload/",
        formData
      );

      const id = response.data.job_id;

      setMessage("Dataset uploaded successfully.");
      setJobId(id);
      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      await fetchPreview(id, 1);

      const interval = setInterval(async () => {
        const status = await checkJobStatus(id);

        if (
          status === "SUCCESS" ||
          status === "FAILED" ||
          status === "CANCELLED" ||
          status === "ERROR"
        ) {
          clearInterval(interval);
        }
      }, 2000);
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Upload failed."
      );
    }
  };

  const cancelJob = async () => {
    if (!jobId) {
      return;
    }

    try {
      const response = await axios.post(
        `http://localhost:8000/api/jobs/${jobId}/cancel/`
      );

      setJobStatus(response.data.status);
      setMessage("Job cancelled.");
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Unable to cancel job."
      );
    }
  };

  const resetForm = () => {
    setFile(null);
    setMessage("");
    setJobId(null);
    setJobStatus("");
    setProgress(0);

    setInstruction("");
    setReplacement("");
    setTargetColumn("");

    setPreviewColumns([]);
    setPreviewRows([]);
    setPreviewPage(1);
    setTotalPages(0);
    setTotalRows(0);
  };

  const getStatusClass = () => {
    if (jobStatus === "SUCCESS") {
      return "status success";
    }

    if (jobStatus === "FAILED") {
      return "status failed";
    }

    if (jobStatus === "CANCELLED") {
      return "status cancelled";
    }

    return "status running";
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>RegexFlow</h1>

          <p>
            Distributed Natural Language Data Processing
          </p>
        </div>
      </header>

      <main className="main-container">
        <section className="card">
          <div className="section-heading">
            <div>
              <h2>Process Dataset</h2>

              <p>
                Upload your dataset and describe the
                transformation you want to perform.
              </p>
            </div>
          </div>

          <div className="form-group">
            <label>Dataset</label>

            <div className="file-upload">
              <input
                id="fileInput"
                type="file"
                accept=".csv,.xlsx"
                onChange={(event) =>
                  setFile(event.target.files[0])
                }
              />

              <label
                htmlFor="fileInput"
                className="file-button"
              >
                Choose Dataset
              </label>

              <span className="file-name">
                {file
                  ? file.name
                  : "No file selected"}
              </span>
            </div>
          </div>

          <div className="form-group">
            <label>
              Natural Language Instruction
            </label>

            <textarea
              placeholder="Example: Find email addresses"
              value={instruction}
              onChange={(event) =>
                setInstruction(event.target.value)
              }
            />
          </div>

          <div className="input-grid">
            <div className="form-group">
              <label>Replacement Value</label>

              <input
                type="text"
                placeholder="Example: REDACTED"
                value={replacement}
                onChange={(event) =>
                  setReplacement(event.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Target Column</label>

              <input
                type="text"
                placeholder="Example: Email"
                value={targetColumn}
                onChange={(event) =>
                  setTargetColumn(event.target.value)
                }
              />
            </div>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              onClick={uploadFile}
            >
              Process Dataset
            </button>

            <button
              className="secondary-button"
              onClick={resetForm}
            >
              Reset
            </button>
          </div>

          {message && (
            <div className="message">
              {message}
            </div>
          )}
        </section>

        {jobId && (
          <section className="card">
            <div className="section-heading">
              <div>
                <h2>Processing Job</h2>

                <p>
                  Track asynchronous processing progress.
                </p>
              </div>

              <span className={getStatusClass()}>
                {jobStatus}
              </span>
            </div>

            <div className="job-details">
              <div>
                <span>Job ID</span>
                <strong>{jobId}</strong>
              </div>

              <div>
                <span>Progress</span>
                <strong>{progress}%</strong>
              </div>

              <div>
                <span>Rows</span>
                <strong>{totalRows}</strong>
              </div>
            </div>

            <div className="progress-track">
              <div
                className="progress-bar"
                style={{
                  width: `${progress}%`,
                }}
              />
            </div>

            <div className="button-row">
              {(jobStatus === "QUEUED" ||
                jobStatus === "RUNNING") && (
                <button
                  className="danger-button"
                  onClick={cancelJob}
                >
                  Cancel Job
                </button>
              )}

              {jobStatus === "SUCCESS" && (
                <a
                  href={`http://localhost:8000/api/download/${jobId}/`}
                >
                  <button className="primary-button">
                    Download Result
                  </button>
                </a>
              )}
            </div>
          </section>
        )}

        {previewRows.length > 0 && (
          <section className="card">
            <div className="section-heading">
              <div>
                <h2>Dataset Preview</h2>

                <p>
                  Showing 10 rows per page from the
                  uploaded dataset.
                </p>
              </div>

              <span className="row-count">
                {totalRows.toLocaleString()} rows
              </span>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    {previewColumns.map((column) => (
                      <th key={column}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {previewRows.map(
                    (row, rowIndex) => (
                      <tr key={rowIndex}>
                        {previewColumns.map(
                          (column) => (
                            <td key={column}>
                              {row[column]}
                            </td>
                          )
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button
                onClick={() =>
                  fetchPreview(
                    jobId,
                    previewPage - 1
                  )
                }
                disabled={previewPage <= 1}
              >
                Previous
              </button>

              <span>
                Page {previewPage} of {totalPages}
              </span>

              <button
                onClick={() =>
                  fetchPreview(
                    jobId,
                    previewPage + 1
                  )
                }
                disabled={
                  previewPage >= totalPages
                }
              >
                Next
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;