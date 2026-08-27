use std::{thread, time::Duration};

use serde_json::{json, to_value};
use tauri::{State, WebviewWindow};

use super::{
    provider::{execute_provider_chat, ProviderManager},
    storage::{is_terminal_status, AgentJobDetail, DesktopStore},
    tools::{propose_tool_run, run_low_risk_tool},
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
    store.apply_worker_status(job_id, worker_status.clone())?;

    if let Some(model_request) = worker_status.pending_model_request {
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
            Ok(value) => core.complete_agent_model_request(
                job_id,
                &model_request.request_id,
                Some(value),
                None,
            )?,
            Err(error) => core.complete_agent_model_request(
                job_id,
                &model_request.request_id,
                None,
                Some(error),
            )?,
        };
        return settle_worker_request(&core, &store, job_id, &model_request.request_id, true);
    }

    if let Some(tool_request) = worker_status.pending_tool_request {
        if tool_request.tool_name == "project.file.write" {
            let runs = store.list_tool_runs(job_id)?;
            let tool_run = runs.into_iter().find(|run| {
                run.tool_name == "project.file.write"
                    && run
                        .permission_snapshot()
                        .get("workerRequestId")
                        .and_then(serde_json::Value::as_str)
                        == Some(tool_request.request_id.as_str())
            });
            let tool_run = match tool_run {
                Some(run) => run,
                None => match propose_tool_run(
                    &store,
                    job_id,
                    &tool_request.tool_name,
                    tool_request.input,
                    Some(&tool_request.request_id),
                ) {
                    Ok(run) => run,
                    Err(error) => {
                        core.complete_agent_tool_request(
                            job_id,
                            &tool_request.request_id,
                            None,
                            Some(error),
                        )?;
                        return settle_worker_request(
                            &core,
                            &store,
                            job_id,
                            &tool_request.request_id,
                            false,
                        );
                    }
                },
            };
            if matches!(
                tool_run.status.as_str(),
                "awaiting_approval" | "approved" | "running"
            ) {
                return store.get_agent_job_detail(job_id);
            }
            let (result, error) = if tool_run.status == "succeeded" {
                (
                    Some(json!({
                        "toolRunId": tool_run.id,
                        "status": tool_run.status,
                        "output": tool_run.output,
                    })),
                    None,
                )
            } else {
                (
                    None,
                    Some(format!(
                        "project.file.write ended with status {}",
                        tool_run.status
                    )),
                )
            };
            core.complete_agent_tool_request(job_id, &tool_request.request_id, result, error)?;
            return settle_worker_request(&core, &store, job_id, &tool_request.request_id, false);
        }
        let tool_result =
            run_low_risk_tool(&store, job_id, &tool_request.tool_name, tool_request.input).map(
                |tool_run| {
                    json!({
                        "toolRunId": tool_run.id,
                        "status": tool_run.status,
                        "output": tool_run.output,
                    })
                },
            );
        match tool_result {
            Ok(value) => core.complete_agent_tool_request(
                job_id,
                &tool_request.request_id,
                Some(value),
                None,
            )?,
            Err(error) => core.complete_agent_tool_request(
                job_id,
                &tool_request.request_id,
                None,
                Some(error),
            )?,
        };
        return settle_worker_request(&core, &store, job_id, &tool_request.request_id, false);
    }

    store.get_agent_job_detail(job_id)
}

fn settle_worker_request(
    core: &DesktopCore,
    store: &DesktopStore,
    job_id: &str,
    request_id: &str,
    model_request: bool,
) -> Result<AgentJobDetail, String> {
    for _ in 0..20 {
        let worker_status = core.refresh_agent_job(job_id)?;
        let still_waiting = if model_request {
            worker_status
                .pending_model_request
                .as_ref()
                .is_some_and(|request| request.request_id == request_id)
        } else {
            worker_status
                .pending_tool_request
                .as_ref()
                .is_some_and(|request| request.request_id == request_id)
        };
        let detail = store.apply_worker_status(job_id, worker_status)?;
        if is_terminal_status(&detail.job.status) || !still_waiting {
            return Ok(detail);
        }
        thread::sleep(Duration::from_millis(10));
    }
    Err("Agent Worker did not accept the completed request".into())
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
