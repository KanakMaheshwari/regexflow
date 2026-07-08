import { useEffect, useRef, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api";

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("");
  const [progress, setProgress] = useState(0);

  const [instruction, setInstruction] = useState("");
  const [replacement, setReplacement] = useState("");

  const [transformationType, setTransformationType] =
    useState("replace");

  const [availableColumns, setAvailableColumns] = useState([]);
  const [targetColumns, setTargetColumns] = useState([]);

  const [previewColumns, setPreviewColumns] = useState([]);
  const [previewRows, setPreviewRows] = useState([]);
  const [previewPage, setPreviewPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalRows, setTotalRows] = useState(0);
  const [previewType, setPreviewType] = useState("original");

  const [isInspecting, setIsInspecting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] =
    useState(false);

  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);

      pollingIntervalRef.current = null;
    }
  };

  const fetchPreview = async (id, page = 1) => {
    try {
      setIsLoadingPreview(true);

      const response = await axios.get(
        `${API_BASE_URL}/jobs/${id}/preview/`,
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

      setPreviewType(
        response.data.preview_type || "original"
      );

      return response.data;
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Unable to load file preview."
      );

      return null;
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const checkJobStatus = async (id) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/jobs/${id}/`
      );

      const status = response.data.status;

      setJobStatus(status);
      setProgress(response.data.progress);

      if (status === "SUCCESS") {
        stopPolling();

        setMessage(
          "Processing completed. Loading processed data..."
        );

        const previewData = await fetchPreview(id, 1);

        if (previewData) {
          setMessage(
            "Processing completed successfully. Processed data is ready."
          );
        }

        return status;
      }

      if (status === "FAILED") {
        stopPolling();

        setMessage("Processing failed.");
      }

      if (status === "CANCELLED") {
        stopPolling();

        setMessage("Job cancelled.");
      }

      return status;
    } catch (error) {
      console.error(error);

      stopPolling();

      setMessage("Unable to check job status.");

      return "ERROR";
    }
  };

  const previewSelectedFile = async () => {
    if (!file) {
      setMessage("Please select a CSV or Excel file.");

      return;
    }

    const formData = new FormData();

    formData.append("file", file);

    try {
      setIsInspecting(true);

      setMessage("Reading dataset columns...");

      const response = await axios.post(
        `${API_BASE_URL}/inspect/`,
        formData
      );

      setAvailableColumns(response.data.columns);

      setPreviewColumns(response.data.columns);
      setPreviewRows(response.data.rows);

      setPreviewPage(1);
      setTotalPages(1);
      setTotalRows(response.data.rows.length);

      setPreviewType("original");

      setTargetColumns([]);

      setMessage(
        "Dataset preview loaded. Select one or more target columns."
      );
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Unable to preview dataset."
      );
    } finally {
      setIsInspecting(false);
    }
  };

  const handleTargetColumnChange = (column) => {
    setTargetColumns((currentColumns) => {
      if (currentColumns.includes(column)) {
        return currentColumns.filter(
          (currentColumn) =>
            currentColumn !== column
        );
      }

      return [
        ...currentColumns,
        column,
      ];
    });
  };

  const uploadFile = async () => {
    if (!file) {
      setMessage("Please select a CSV or Excel file.");

      return;
    }

    if (!instruction.trim()) {
      setMessage(
        "Please enter a processing instruction."
      );

      return;
    }

    if (
      transformationType === "replace" &&
      !replacement.trim()
    ) {
      setMessage(
        "Please enter a replacement value for the replace transformation."
      );

      return;
    }

    if (targetColumns.length === 0) {
      setMessage(
        "Please select at least one target column."
      );

      return;
    }

    stopPolling();

    const formData = new FormData();

    formData.append("file", file);
    formData.append("instruction", instruction);
    formData.append("replacement", replacement);

    formData.append(
      "target_columns",
      JSON.stringify(targetColumns)
    );

    formData.append(
      "transformation_type",
      transformationType
    );

    try {
      setIsUploading(true);

      setMessage("Uploading dataset...");

      setProgress(0);
      setJobStatus("");
      setPreviewType("original");

      const response = await axios.post(
        `${API_BASE_URL}/upload/`,
        formData
      );

      const id = response.data.job_id;

      setMessage(
        "Dataset uploaded. Processing started."
      );

      setJobId(id);
      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      await fetchPreview(id, 1);

      pollingIntervalRef.current = setInterval(
        async () => {
          await checkJobStatus(id);
        },
        2000
      );
    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
          "Upload failed."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const cancelJob = async () => {
    if (!jobId) {
      return;
    }

    try {
      const response = await axios.post(
        `${API_BASE_URL}/jobs/${jobId}/cancel/`
      );

      stopPolling();

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
    stopPolling();

    setFile(null);
    setMessage("");

    setJobId(null);
    setJobStatus("");
    setProgress(0);

    setInstruction("");
    setReplacement("");
    setTransformationType("replace");

    setAvailableColumns([]);
    setTargetColumns([]);

    setPreviewColumns([]);
    setPreviewRows([]);

    setPreviewPage(1);
    setTotalPages(0);
    setTotalRows(0);

    setPreviewType("original");

    setIsInspecting(false);
    setIsUploading(false);
    setIsLoadingPreview(false);

    const fileInput =
      document.getElementById("fileInput");

    if (fileInput) {
      fileInput.value = "";
    }
  };

  const handleFileChange = (event) => {
    const selectedFile =
      event.target.files[0];

    stopPolling();

    setFile(selectedFile || null);

    setMessage("");

    setJobId(null);
    setJobStatus("");
    setProgress(0);

    setAvailableColumns([]);
    setTargetColumns([]);

    setPreviewColumns([]);
    setPreviewRows([]);

    setPreviewPage(1);
    setTotalPages(0);
    setTotalRows(0);

    setPreviewType("original");
  };

  const handleTransformationChange = (event) => {
    const selectedTransformation =
      event.target.value;

    setTransformationType(
      selectedTransformation
    );

    if (selectedTransformation !== "replace") {
      setReplacement("");
    }
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

  const isJobActive =
    jobStatus === "QUEUED" ||
    jobStatus === "RUNNING";

  const isProcessedPreview =
    previewType === "processed";

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
                Upload a dataset, inspect its columns,
                and select one or more target columns.
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
                onChange={handleFileChange}
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

          {file &&
            availableColumns.length === 0 && (
              <div className="button-row">
                <button
                  className="secondary-button"
                  onClick={previewSelectedFile}
                  disabled={isInspecting}
                >
                  {isInspecting
                    ? "Loading..."
                    : "Load Dataset Columns"}
                </button>
              </div>
            )}

          <div className="form-group">
            <label>Target Columns</label>

            {availableColumns.length === 0 ? (
              <p>
                Choose a dataset and load its columns
                to select one or more target columns.
              </p>
            ) : (
              <>
                <p>
                  Select one or more columns to transform.
                </p>

                <div className="target-columns">
                  {availableColumns.map(
                    (column) => (
                      <label
                        key={column}
                        className="target-column-option"
                      >
                        <input
                          type="checkbox"
                          checked={targetColumns.includes(
                            column
                          )}
                          onChange={() =>
                            handleTargetColumnChange(
                              column
                            )
                          }
                        />

                        <span>{column}</span>
                      </label>
                    )
                  )}
                </div>
              </>
            )}
          </div>

          <div className="form-group">
            <label>Transformation Type</label>

            <select
              value={transformationType}
              onChange={handleTransformationChange}
            >
              <option value="replace">
                Replace Matches
              </option>

              <option value="extract">
                Extract Matches
              </option>

              <option value="mask">
                Mask Matches
              </option>
            </select>

            {transformationType === "replace" && (
              <p>
                Replace every regex match with the
                replacement value.
              </p>
            )}

            {transformationType === "extract" && (
              <p>
                Keep only the values matched by the
                generated regex.
              </p>
            )}

            {transformationType === "mask" && (
              <p>
                Replace matched values with a masked
                value.
              </p>
            )}
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

          {transformationType === "replace" && (
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
          )}

          <div className="button-row">
            <button
              className="primary-button"
              onClick={uploadFile}
              disabled={
                isUploading ||
                isJobActive
              }
            >
              {isUploading
                ? "Uploading..."
                : "Process Dataset"}
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

        {jobId && jobStatus && (
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

                <strong>
                  {totalRows.toLocaleString()}
                </strong>
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
              {isJobActive && (
                <button
                  className="danger-button"
                  onClick={cancelJob}
                >
                  Cancel Job
                </button>
              )}

              {jobStatus === "SUCCESS" && (
                <a
                  href={`${API_BASE_URL}/download/${jobId}/`}
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
                <h2>
                  {isProcessedPreview
                    ? "Processed Data Preview"
                    : "Dataset Preview"}
                </h2>

                <p>
                  {isProcessedPreview
                    ? "Previewing transformed dataset records."
                    : "Previewing original uploaded dataset records."}
                </p>
              </div>

              {totalRows > 0 && (
                <span className="row-count">
                  {totalRows.toLocaleString()} rows
                </span>
              )}
            </div>

            {isLoadingPreview && (
              <div className="message">
                Loading preview...
              </div>
            )}

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    {previewColumns.map(
                      (column) => (
                        <th key={column}>
                          {column}
                        </th>
                      )
                    )}
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

            {jobId && totalPages > 1 && (
              <div className="pagination">
                <button
                  onClick={() =>
                    fetchPreview(
                      jobId,
                      previewPage - 1
                    )
                  }
                  disabled={
                    previewPage <= 1 ||
                    isLoadingPreview
                  }
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
                    previewPage >= totalPages ||
                    isLoadingPreview
                  }
                >
                  Next
                </button>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;