use std::{process::Child, sync::Mutex};

use serde::Serialize;
use serde_json::Value;
use tauri::State;

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
