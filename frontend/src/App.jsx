import { useState } from "react";
import axios from "axios";
function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("");
  const[progress, setProgress] = useState(0);
  const checkJobStatus = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/jobs/${id}/`);
      setJobStatus(response.data.status);
      setProgress(response.data.progress);

    } catch (error){
      console.error(error);
    }
  };
  const uploadFile = async () => {
    if (!file) {
      setMessage("Please select a file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try{
      const response = await axios.post("http://localhost:8000/api/upload/", formData, );
      setMessage(`Job Created!
        Job ID: ${response.data.job_id}
        Status: ${response.data.status}
        Progress: ${response.data.progress}%`);
      setJobId(response.data.job_id);
      setJobStatus(response.data.job_id);
    }
    catch (error) {
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

      <button onClick={uploadFile}>Upload</button>

      <br />
      <br />

      {message && <p>{message}</p>}

      {file && (
        <p>
          Selected File: <strong>{file.name}</strong>
        </p>
      )}
    </div>
  );
}

export default App;