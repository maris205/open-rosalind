use tauri::State;

use super::{
    storage::{is_terminal_status, AgentJobDetail, DesktopStore},
    DesktopCore,
};

#[tauri::command]
pub fn desktop_get_agent_job(
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    store.get_agent_job_detail(job_id.trim())
}

#[tauri::command]
pub fn desktop_start_agent_job(
    core: State<'_, DesktopCore>,
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    let job_id = job_id.trim();
    let job = store.get_agent_job(job_id)?;
    if job.status != "queued" {
        return Err(format!(
            "Agent job can only start from queued status; current status is {}",
            job.status
        ));
    }
    let worker_status = core.start_agent_job(&job.id, &job.request)?;
    store.apply_worker_status(job_id, worker_status)
}

#[tauri::command]
pub fn desktop_refresh_agent_job(
    core: State<'_, DesktopCore>,
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    let job_id = job_id.trim();
    let detail = store.get_agent_job_detail(job_id)?;
    if detail.job.status == "queued" || is_terminal_status(&detail.job.status) {
        return Ok(detail);
    }
    let worker_status = core.refresh_agent_job(job_id)?;
    store.apply_worker_status(job_id, worker_status)
}

#[tauri::command]
pub fn desktop_cancel_agent_job(
    core: State<'_, DesktopCore>,
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    let job_id = job_id.trim();
    let detail = store.request_cancellation(job_id)?;
    if detail.job.status != "cancelling" {
        return Ok(detail);
    }
    let worker_status = core.cancel_agent_job(job_id)?;
    store.apply_worker_status(job_id, worker_status)
}
