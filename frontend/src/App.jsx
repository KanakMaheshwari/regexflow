import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("");
  const [progress, setProgress] = useState(0);

  // Check job status
  const checkJobStatus = async (id) => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/jobs/${id}/`
      );

      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      if (response.data.status === "SUCCESS") {
        setMessage("✅ Processing Complete!");
      }

      return response.data.status;
    } catch (error) {
      console.error(error);
    }
  };

  // Upload file
  const uploadFile = async () => {
    if (!file) {
      setMessage("Please select a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        "http://localhost:8000/api/upload/",
        formData
      );

      setMessage("Upload Successful!");
      setJobId(response.data.job_id);
      setJobStatus(response.data.status);
      setProgress(response.data.progress);

      const id = response.data.job_id;

      // Poll every 2 seconds
      const interval = setInterval(async () => {
        const status = await checkJobStatus(id);

        if (status === "SUCCESS") {
          clearInterval(interval);
        }
      }, 2000);

    } catch (error) {
      setMessage("Upload Failed");
      console.error(error);
    }
  };

  return (
    <div style={{ padding: "40px" }}>
      <h1>Upload Dataset</h1>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br />
      <br />

      <button onClick={uploadFile}>
        Upload
      </button>

      <br />
      <br />

      {message && <p>{message}</p>}

      {jobId && (
        <>
          <p><strong>Job ID:</strong> {jobId}</p>
          <p><strong>Status:</strong> {jobStatus}</p>
          <p><strong>Progress:</strong> {progress}%</p>
        </>
      )}

      {file && (
        <p>
          Selected File: <strong>{file.name}</strong>
        </p>
      )}
    </div>
  );
}

export default App;