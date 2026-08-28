use std::{
    fs,
    process::Child,
    sync::Mutex,
    time::{SystemTime, UNIX_EPOCH},
};

use serde::Serialize;
use serde_json::{json, Value};
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use self::storage::DesktopStore;

mod agent;
pub mod jobs;
pub mod provider;
pub mod storage;
pub mod tools;

pub use agent::{AgentWorkerInfo, AgentWorkerProcess, WorkerJobStatus};

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRuntimeStatus {
    ready: bool,
    transport: &'static str,
    port: u16,
    backend_pid: u32,
    agent_worker_pid: u32,
    agent_worker_ready: bool,
    agent_protocol_version: u32,
    data_root: String,
    agent_runtime: String,
}

impl DesktopRuntimeStatus {
    pub fn new(
        port: u16,
        backend_pid: u32,
        agent_worker: &AgentWorkerInfo,
        data_root: &std::path::Path,
        agent_runtime: String,
    ) -> Self {
        Self {
            ready: true,
            transport: "authenticated-loopback",
            port,
            backend_pid,
            agent_worker_pid: agent_worker.pid,
            agent_worker_ready: true,
            agent_protocol_version: agent_worker.protocol_version,
            data_root: data_root.to_string_lossy().into_owned(),
            agent_runtime,
        }
    }
}

pub struct DesktopCore {
    backend: Mutex<Option<Child>>,
    agent_worker: Mutex<Option<AgentWorkerProcess>>,
    status: DesktopRuntimeStatus,
}

impl DesktopCore {
    pub fn new(
        backend: Child,
        agent_worker: AgentWorkerProcess,
        status: DesktopRuntimeStatus,
    ) -> Self {
        Self {
            backend: Mutex::new(Some(backend)),
            agent_worker: Mutex::new(Some(agent_worker)),
            status,
        }
    }

    pub fn stop(&self) {
        if let Ok(mut agent_worker) = self.agent_worker.lock() {
            if let Some(worker) = agent_worker.as_mut() {
                worker.stop();
            }
            agent_worker.take();
        }
        if let Ok(mut backend) = self.backend.lock() {
            if let Some(child) = backend.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            backend.take();
        }
    }

    pub fn start_agent_job(
        &self,
        job_id: &str,
        request: &Value,
    ) -> Result<WorkerJobStatus, String> {
        let mut worker = self
            .agent_worker
            .lock()
            .map_err(|_| "Agent Worker lock was poisoned".to_string())?;
        worker
            .as_mut()
            .ok_or_else(|| "Agent Worker is not running".to_string())?
            .start_job(job_id, request)
    }

    pub fn refresh_agent_job(&self, job_id: &str) -> Result<WorkerJobStatus, String> {
        let mut worker = self
            .agent_worker
            .lock()
            .map_err(|_| "Agent Worker lock was poisoned".to_string())?;
        worker
            .as_mut()
            .ok_or_else(|| "Agent Worker is not running".to_string())?
            .job_status(job_id)
    }

    pub fn cancel_agent_job(&self, job_id: &str) -> Result<WorkerJobStatus, String> {
        let mut worker = self
            .agent_worker
            .lock()
            .map_err(|_| "Agent Worker lock was poisoned".to_string())?;
        worker
            .as_mut()
            .ok_or_else(|| "Agent Worker is not running".to_string())?
            .cancel_job(job_id)
    }

    pub fn complete_agent_model_request(
        &self,
        job_id: &str,
        request_id: &str,
        result: Option<Value>,
        error: Option<String>,
    ) -> Result<WorkerJobStatus, String> {
        let mut worker = self
            .agent_worker
            .lock()
            .map_err(|_| "Agent Worker lock was poisoned".to_string())?;
        worker
            .as_mut()
            .ok_or_else(|| "Agent Worker is not running".to_string())?
            .complete_model_request(job_id, request_id, result, error)
    }

    pub fn complete_agent_tool_request(
        &self,
        job_id: &str,
        request_id: &str,
        result: Option<Value>,
        error: Option<String>,
    ) -> Result<WorkerJobStatus, String> {
        let mut worker = self
            .agent_worker
            .lock()
            .map_err(|_| "Agent Worker lock was poisoned".to_string())?;
        worker
            .as_mut()
            .ok_or_else(|| "Agent Worker is not running".to_string())?
            .complete_tool_request(job_id, request_id, result, error)
    }
}

impl Drop for DesktopCore {
    fn drop(&mut self) {
        if let Ok(agent_worker) = self.agent_worker.get_mut() {
            if let Some(worker) = agent_worker.as_mut() {
                worker.stop();
            }
            agent_worker.take();
        }
        if let Ok(backend) = self.backend.get_mut() {
            if let Some(child) = backend.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            backend.take();
        }
    }
}

#[tauri::command]
pub fn desktop_core_status(state: State<'_, DesktopCore>) -> Result<DesktopRuntimeStatus, String> {
    Ok(state.status.clone())
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DiagnosticsExport {
    file_name: String,
    size_bytes: u64,
}

#[tauri::command]
pub fn desktop_export_diagnostics(
    app: AppHandle,
    core: State<'_, DesktopCore>,
    store: State<'_, DesktopStore>,
) -> Result<Option<DiagnosticsExport>, String> {
    let generated_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or_default();
    let agent_runtime = match core.status.agent_runtime.as_str() {
        "legacy" => "legacy",
        "openhands" => "openhands",
        _ => "custom",
    };
    let report = json!({
        "reportSchemaVersion": 1,
        "generatedAtUnixMillis": generated_at,
        "application": {
            "name": "OpenRosalind",
            "version": env!("CARGO_PKG_VERSION"),
            "os": std::env::consts::OS,
            "architecture": std::env::consts::ARCH,
        },
        "runtime": {
            "ready": core.status.ready,
            "transport": core.status.transport,
            "agentWorkerReady": core.status.agent_worker_ready,
            "agentProtocolVersion": core.status.agent_protocol_version,
            "agentRuntime": agent_runtime,
        },
        "storage": store.diagnostics_snapshot()?,
        "privacy": {
            "containsApiKeys": false,
            "containsPromptsOrResponses": false,
            "containsFileContents": false,
            "containsFilesystemPaths": false,
            "note": "This report contains only runtime capability and aggregate status counts."
        }
    });
    let bytes = serde_json::to_vec_pretty(&report)
        .map_err(|error| format!("Unable to encode diagnostics report: {error}"))?;
    let Some(destination) = app
        .dialog()
        .file()
        .set_title("导出 OpenRosalind 诊断报告")
        .set_file_name(format!("OpenRosalind-diagnostics-{generated_at}.json"))
        .add_filter("JSON", &["json"])
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let path = destination
        .into_path()
        .map_err(|_| "Diagnostics export requires a local filesystem destination".to_string())?;
    fs::write(&path, &bytes)
        .map_err(|error| format!("Unable to save diagnostics report: {error}"))?;
    Ok(Some(DiagnosticsExport {
        file_name: path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("OpenRosalind-diagnostics.json")
            .to_string(),
        size_bytes: bytes.len() as u64,
    }))
}
