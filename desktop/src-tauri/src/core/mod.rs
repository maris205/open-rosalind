use std::{process::Child, sync::Mutex};

use serde::Serialize;
use tauri::State;

mod agent;
pub mod storage;

pub use agent::{AgentWorkerInfo, AgentWorkerProcess};

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
