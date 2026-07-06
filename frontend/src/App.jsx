import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("");
  const [progress, setProgress] = useState(0);

  const [instruction, setInstruction] = useState("");
  const [replacement, setReplacement] = useState("");
  const [targetColumn, setTargetColumn] = useState("");

  const checkJobStatus = async (id) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/jobs/${id}/`
      );

      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      if (response.data.status === "SUCCESS") {
        setMessage("Processing Complete!");
      }

      if (response.data.status === "FAILED") {
        setMessage("Processing Failed.");
      }

      if (response.data.status === "CANCELLED") {
        setMessage("Job Cancelled.");
      }

      return response.data.status;

    } catch (error) {
      console.error(error);
      setMessage("Unable to check job status.");

      return "ERROR";
    }
  };


  const uploadFile = async () => {
    if (!file) {
      setMessage("Please select a file first.");
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
      setMessage("Uploading...");
      setProgress(0);
      setJobStatus("");

      const response = await axios.post(
        "http://localhost:8000/api/upload/",
        formData
      );

      setMessage("Upload Successful!");

      setJobId(response.data.job_id);
      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      const id = response.data.job_id;

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
        "Upload Failed"
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
      setMessage("Job Cancelled.");

    } catch (error) {
      console.error(error);

      setMessage(
        error.response?.data?.error ||
        "Unable to cancel job."
      );
    }
  };


  return (
    <div style={{ padding: "40px" }}>

      <h1>Upload Dataset</h1>


      <input
        type="file"
        accept=".csv,.xlsx"
        onChange={(e) => setFile(e.target.files[0])}
      />


      <br />
      <br />


      <input
        type="text"
        placeholder="Enter processing instruction"
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        style={{
          width: "400px",
          padding: "8px"
        }}
      />


      <br />
      <br />


      <input
        type="text"
        placeholder="Replacement Value"
        value={replacement}
        onChange={(e) => setReplacement(e.target.value)}
        style={{
          width: "400px",
          padding: "8px"
        }}
      />


      <br />
      <br />


      <input
        type="text"
        placeholder="Target Column (Optional)"
        value={targetColumn}
        onChange={(e) => setTargetColumn(e.target.value)}
        style={{
          width: "400px",
          padding: "8px"
        }}
      />


      <br />
      <br />


      <button onClick={uploadFile}>
        Upload
      </button>


      <br />
      <br />


      {message && (
        <p>{message}</p>
      )}


      {file && (
        <p>
          Selected File:{" "}
          <strong>{file.name}</strong>
        </p>
      )}


      {jobId && (
        <>
          <p>
            <strong>Job ID:</strong>{" "}
            {jobId}
          </p>

          <p>
            <strong>Status:</strong>{" "}
            {jobStatus}
          </p>

          <p>
            <strong>Progress:</strong>{" "}
            {progress}%
          </p>


          {(
            jobStatus === "QUEUED" ||
            jobStatus === "RUNNING"
          ) && (
            <button onClick={cancelJob}>
              Cancel Job
            </button>
          )}


          {jobStatus === "SUCCESS" && (
            <>
              <br />
              <br />

              <a
                href={
                  `http://localhost:8000/api/download/${jobId}/`
                }
                target="_blank"
                rel="noreferrer"
              >
                <button>
                  Download Processed File
                </button>
              </a>
            </>
          )}

        </>
      )}

    </div>
  );
}

export default App;