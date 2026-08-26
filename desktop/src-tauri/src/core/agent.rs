use std::{
    env,
    ffi::OsStr,
    io::{BufRead, BufReader, Write},
    path::Path,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::mpsc::{self, Receiver},
    thread::{self, JoinHandle},
    time::Duration,
};

use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::{json, Value};

use super::provider::ProviderChatMessage;

const PROTOCOL_VERSION: u32 = 3;
const MAX_RESPONSE_BYTES: usize = 1024 * 1024;
const REQUEST_TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Clone, Debug)]
pub struct AgentWorkerInfo {
    pub pid: u32,
    pub protocol_version: u32,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct InitializeResult {
    protocol_version: u32,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkerJobProgress {
    pub sequence: i64,
    pub kind: String,
    pub payload: Value,
    pub created_at: i64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkerJobStatus {
    pub job_id: String,
    pub status: String,
    pub cancellation_requested: bool,
    pub progress: Vec<WorkerJobProgress>,
    pub result: Option<Value>,
    pub error: Option<String>,
    pub started_at: Option<i64>,
    pub ended_at: Option<i64>,
    pub pending_model_request: Option<WorkerModelRequest>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkerModelRequest {
    pub request_id: String,
    pub provider_profile_id: Option<String>,
    pub messages: Vec<ProviderChatMessage>,
    pub temperature: f32,
}

#[derive(Debug, Deserialize)]
struct RpcError {
    code: i64,
    message: String,
}

#[derive(Debug, Deserialize)]
struct RpcResponse {
    jsonrpc: String,
    id: u64,
    result: Option<Value>,
    error: Option<RpcError>,
}

pub struct AgentWorkerProcess {
    child: Child,
    input: ChildStdin,
    responses: Receiver<Result<String, String>>,
    reader_thread: Option<JoinHandle<()>>,
    next_id: u64,
    stopped: bool,
}

impl AgentWorkerProcess {
    pub fn spawn(
        python: &Path,
        repository_root: &Path,
        python_path: &OsStr,
        data_root: &Path,
    ) -> Result<(Self, AgentWorkerInfo), String> {
        let mut command = Command::new(python);
        command
            .env_clear()
            .arg("-m")
            .arg("web_app.desktop_agent_worker")
            .current_dir(repository_root)
            .env("PYTHONPATH", python_path)
            .env("ROSALIND_AGENT_DATA_ROOT", data_root)
            .env("PYTHONUNBUFFERED", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        for name in [
            "PATH",
            "SystemRoot",
            "WINDIR",
            "TEMP",
            "TMP",
            "TMPDIR",
            "LANG",
            "LC_ALL",
        ] {
            if let Some(value) = env::var_os(name) {
                command.env(name, value);
            }
        }
        let mut child = command
            .spawn()
            .map_err(|error| format!("Unable to start the local Agent Worker: {error}"))?;
        let input = child
            .stdin
            .take()
            .ok_or("Unable to open Agent Worker stdin")?;
        let output = child
            .stdout
            .take()
            .ok_or("Unable to open Agent Worker stdout")?;
        let (response_sender, responses) = mpsc::sync_channel(8);
        let reader_thread = thread::spawn(move || read_responses(output, response_sender));
        let pid = child.id();
        let mut worker = Self {
            child,
            input,
            responses,
            reader_thread: Some(reader_thread),
            next_id: 1,
            stopped: false,
        };
        let initialized: InitializeResult = worker.request(
            "initialize",
            json!({
                "client": "open-rosalind-desktop",
                "protocolVersion": PROTOCOL_VERSION,
            }),
        )?;
        if initialized.protocol_version != PROTOCOL_VERSION {
            return Err(format!(
                "Unsupported Agent Worker protocol version {}",
                initialized.protocol_version
            ));
        }
        Ok((
            worker,
            AgentWorkerInfo {
                pid,
                protocol_version: initialized.protocol_version,
            },
        ))
    }

    fn request<T: DeserializeOwned>(&mut self, method: &str, params: Value) -> Result<T, String> {
        self.request_with_timeout(method, params, REQUEST_TIMEOUT)
    }

    fn request_with_timeout<T: DeserializeOwned>(
        &mut self,
        method: &str,
        params: Value,
        timeout: Duration,
    ) -> Result<T, String> {
        let id = self.next_id;
        self.next_id += 1;
        let request = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        serde_json::to_writer(&mut self.input, &request)
            .map_err(|error| format!("Unable to encode Agent Worker request: {error}"))?;
        self.input
            .write_all(b"\n")
            .and_then(|_| self.input.flush())
            .map_err(|error| format!("Unable to send Agent Worker request: {error}"))?;

        let response_line = self
            .responses
            .recv_timeout(timeout)
            .map_err(|error| format!("Timed out waiting for Agent Worker response: {error}"))??;
        let response: RpcResponse = serde_json::from_str(&response_line)
            .map_err(|error| format!("Invalid Agent Worker response: {error}"))?;
        if response.jsonrpc != "2.0" || response.id != id {
            return Err("Agent Worker returned a mismatched JSON-RPC response".into());
        }
        if let Some(error) = response.error {
            return Err(format!(
                "Agent Worker error {}: {}",
                error.code, error.message
            ));
        }
        let result = response
            .result
            .ok_or("Agent Worker response did not contain a result")?;
        serde_json::from_value(result)
            .map_err(|error| format!("Invalid Agent Worker result: {error}"))
    }

    pub fn start_job(&mut self, job_id: &str, request: &Value) -> Result<WorkerJobStatus, String> {
        self.request(
            "job.start",
            json!({
                "jobId": job_id,
                "request": request,
            }),
        )
    }

    pub fn job_status(&mut self, job_id: &str) -> Result<WorkerJobStatus, String> {
        self.request("job.status", json!({"jobId": job_id}))
    }

    pub fn cancel_job(&mut self, job_id: &str) -> Result<WorkerJobStatus, String> {
        self.request("job.cancel", json!({"jobId": job_id}))
    }

    pub fn complete_model_request(
        &mut self,
        job_id: &str,
        request_id: &str,
        result: Option<Value>,
        error: Option<String>,
    ) -> Result<WorkerJobStatus, String> {
        self.request(
            "model.complete",
            json!({
                "jobId": job_id,
                "requestId": request_id,
                "result": result,
                "error": error,
            }),
        )
    }

    pub fn stop(&mut self) {
        if self.stopped {
            return;
        }
        self.stopped = true;
        let _ =
            self.request_with_timeout::<Value>("shutdown", json!({}), Duration::from_millis(250));
        for _ in 0..20 {
            if self.child.try_wait().ok().flatten().is_some() {
                self.join_reader();
                return;
            }
            thread::sleep(Duration::from_millis(50));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
        self.join_reader();
    }

    fn join_reader(&mut self) {
        if let Some(reader_thread) = self.reader_thread.take() {
            let _ = reader_thread.join();
        }
    }
}

impl Drop for AgentWorkerProcess {
    fn drop(&mut self) {
        self.stop();
    }
}

fn read_responses(output: ChildStdout, sender: mpsc::SyncSender<Result<String, String>>) {
    let mut output = BufReader::new(output);
    loop {
        let mut response_line = String::new();
        match output.read_line(&mut response_line) {
            Ok(0) => {
                let _ = sender.send(Err("Agent Worker closed its protocol stream".into()));
                return;
            }
            Ok(bytes) if bytes > MAX_RESPONSE_BYTES => {
                let _ = sender.send(Err(
                    "Agent Worker response exceeded the protocol limit".into()
                ));
                return;
            }
            Ok(_) => {
                if sender.send(Ok(response_line)).is_err() {
                    return;
                }
            }
            Err(error) => {
                let _ = sender.send(Err(format!(
                    "Unable to read Agent Worker response: {error}"
                )));
                return;
            }
        }
    }
}
