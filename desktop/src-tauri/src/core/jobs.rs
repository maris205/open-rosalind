use std::{thread, time::Duration};

use serde_json::to_value;
use tauri::{State, WebviewWindow};

use super::{
    provider::{execute_provider_chat, ProviderManager},
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
    window: WebviewWindow,
    core: State<'_, DesktopCore>,
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    let job_id = job_id.trim();
    let detail = store.get_agent_job_detail(job_id)?;
    if detail.job.status == "queued" || is_terminal_status(&detail.job.status) {
        return Ok(detail);
    }
    let worker_status = core.refresh_agent_job(job_id)?;
    let Some(model_request) = worker_status.pending_model_request.clone() else {
        return store.apply_worker_status(job_id, worker_status);
    };
    store.apply_worker_status(job_id, worker_status)?;

    let provider_result = (|| {
        let profile_id = model_request
            .provider_profile_id
            .as_deref()
            .unwrap_or(super::storage::DEFAULT_PROVIDER_ID);
        let profile = store.get_provider_profile(profile_id)?;
        let cancellation = manager.begin_request(&model_request.request_id)?;
        let result = execute_provider_chat(
            &manager,
            &profile,
            &model_request.request_id,
            &model_request.messages,
            model_request.temperature,
            &window,
            &cancellation,
        );
        manager.end_request(&model_request.request_id);
        let result = result?;
        to_value(result).map_err(|error| format!("Unable to encode Provider result: {error}"))
    })();
    match provider_result {
        Ok(value) => {
            core.complete_agent_model_request(
                job_id,
                &model_request.request_id,
                Some(value),
                None,
            )?;
        }
        Err(error) => {
            core.complete_agent_model_request(
                job_id,
                &model_request.request_id,
                None,
                Some(error),
            )?;
        }
    }

    for _ in 0..20 {
        let worker_status = core.refresh_agent_job(job_id)?;
        let waiting = worker_status.pending_model_request.is_some();
        let terminal = is_terminal_status(&worker_status.status);
        let detail = store.apply_worker_status(job_id, worker_status)?;
        if terminal || !waiting {
            return Ok(detail);
        }
        thread::sleep(Duration::from_millis(10));
    }
    Err("Agent Worker did not accept the Provider result".into())
}

#[tauri::command]
pub fn desktop_cancel_agent_job(
    core: State<'_, DesktopCore>,
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
    job_id: String,
) -> Result<AgentJobDetail, String> {
    let job_id = job_id.trim();
    let detail = store.request_cancellation(job_id)?;
    if detail.job.status != "cancelling" {
        return Ok(detail);
    }
    if let Some(model_request) = core.refresh_agent_job(job_id)?.pending_model_request {
        manager.cancel_request(&model_request.request_id)?;
    }
    let worker_status = core.cancel_agent_job(job_id)?;
    store.apply_worker_status(job_id, worker_status)
}
