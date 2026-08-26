use std::{process::Child, sync::Mutex};

use serde::Serialize;
use tauri::State;

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRuntimeStatus {
    ready: bool,
    transport: &'static str,
    port: u16,
    backend_pid: u32,
    data_root: String,
    agent_runtime: String,
}

impl DesktopRuntimeStatus {
    pub fn new(
        port: u16,
        backend_pid: u32,
        data_root: &std::path::Path,
        agent_runtime: String,
    ) -> Self {
        Self {
            ready: true,
            transport: "authenticated-loopback",
            port,
            backend_pid,
            data_root: data_root.to_string_lossy().into_owned(),
            agent_runtime,
        }
    }
}

pub struct DesktopCore {
    backend: Mutex<Option<Child>>,
    status: DesktopRuntimeStatus,
}

impl DesktopCore {
    pub fn new(backend: Child, status: DesktopRuntimeStatus) -> Self {
        Self {
            backend: Mutex::new(Some(backend)),
            status,
        }
    }

    pub fn stop(&self) {
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
