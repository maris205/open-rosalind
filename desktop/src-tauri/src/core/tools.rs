use serde::Serialize;
use serde_json::{json, Value};
use tauri::State;

use super::storage::{DesktopStore, ToolRun};

const MAX_TEXT_CHARACTERS: usize = 500_000;

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolExecutor {
    kind: &'static str,
    entrypoint: &'static str,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolPermissions {
    risk: &'static str,
    approval: &'static str,
    filesystem: Vec<ToolFilesystemPermission>,
    network: &'static str,
    secrets: Vec<&'static str>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolFilesystemPermission {
    scope: &'static str,
    mode: &'static str,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolResources {
    timeout_seconds: u32,
    max_input_bytes: usize,
    max_output_bytes: usize,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolContract {
    schema_version: u32,
    name: &'static str,
    version: &'static str,
    title: &'static str,
    description: &'static str,
    executor: ToolExecutor,
    permissions: ToolPermissions,
    resources: ToolResources,
}

fn text_statistics_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "text.statistics",
        version: "1.0.0",
        title: "文本统计",
        description: "在 Desktop Core 内统计文本的字符、字节、单词和行数。",
        executor: ToolExecutor {
            kind: "native",
            entrypoint: "desktop-core:text-statistics",
        },
        permissions: ToolPermissions {
            risk: "low",
            approval: "automatic",
            filesystem: vec![],
            network: "none",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 1,
            max_input_bytes: 512 * 1024,
            max_output_bytes: 16 * 1024,
        },
    }
}

fn contracts() -> Vec<ToolContract> {
    vec![text_statistics_contract(), python_run_contract()]
}

fn python_run_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "python.run",
        version: "1.0.0-alpha.1",
        title: "运行 Python",
        description: "在桌面 Python 执行器中运行用户逐次确认的代码。",
        executor: ToolExecutor {
            kind: "native",
            entrypoint: "python-sidecar:execute",
        },
        permissions: ToolPermissions {
            risk: "critical",
            approval: "per-run",
            filesystem: vec![
                ToolFilesystemPermission {
                    scope: "host",
                    mode: "read",
                },
                ToolFilesystemPermission {
                    scope: "host",
                    mode: "write",
                },
            ],
            network: "host",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 60,
            max_input_bytes: 64 * 1024,
            max_output_bytes: 20 * 1024 * 1024,
        },
    }
}

fn contract(name: &str) -> Option<ToolContract> {
    contracts().into_iter().find(|item| item.name == name)
}

fn execute_text_statistics(input: &Value) -> Result<Value, String> {
    let object = input
        .as_object()
        .ok_or_else(|| "text.statistics input must be an object".to_string())?;
    if object.keys().any(|key| key != "text") {
        return Err("text.statistics accepts only the text field".into());
    }
    let text = object
        .get("text")
        .and_then(Value::as_str)
        .ok_or_else(|| "text.statistics requires a text string".to_string())?;
    let characters = text.chars().count();
    if characters > MAX_TEXT_CHARACTERS {
        return Err("text.statistics input exceeds 500000 characters".into());
    }
    Ok(json!({
        "characters": characters,
        "bytes": text.len(),
        "words": text.split_whitespace().count(),
        "lines": text.lines().count(),
        "nonWhitespaceCharacters": text.chars().filter(|character| !character.is_whitespace()).count(),
    }))
}

fn execute_tool(name: &str, input: &Value) -> Result<Value, String> {
    match name {
        "text.statistics" => execute_text_statistics(input),
        _ => Err(format!("Tool {name} is not installed")),
    }
}

fn validate_proposed_input(name: &str, input: &Value) -> Result<(), String> {
    match name {
        "python.run" => {
            let object = input
                .as_object()
                .ok_or_else(|| "python.run input must be an object".to_string())?;
            if object.keys().any(|key| key != "code") {
                return Err("python.run accepts only the code field".into());
            }
            let code = object
                .get("code")
                .and_then(Value::as_str)
                .ok_or_else(|| "python.run requires a code string".to_string())?;
            if code.is_empty() || code.chars().count() > 50_000 || code.contains('\0') {
                return Err(
                    "python.run code must contain 1 to 50000 characters without NUL bytes".into(),
                );
            }
            Ok(())
        }
        _ => Err(format!("Tool {name} does not support approval proposals")),
    }
}

#[tauri::command]
pub fn desktop_list_tool_contracts() -> Vec<ToolContract> {
    contracts()
}

#[tauri::command]
pub fn desktop_run_low_risk_tool(
    store: State<'_, DesktopStore>,
    agent_job_id: String,
    tool_name: String,
    input: Value,
) -> Result<ToolRun, String> {
    let tool_name = tool_name.trim();
    let contract =
        contract(tool_name).ok_or_else(|| format!("Tool {tool_name} is not installed"))?;
    if contract.permissions.risk != "low" || contract.permissions.approval != "automatic" {
        return Err("This Tool Contract requires an explicit approval flow".into());
    }
    let permission_snapshot = serde_json::to_value(&contract.permissions)
        .map_err(|error| format!("Unable to encode Tool permission snapshot: {error}"))?;
    let tool_run = store.create_tool_run(
        agent_job_id.trim(),
        contract.name,
        contract.executor.kind,
        input.clone(),
        permission_snapshot,
        "running",
    )?;
    let result = execute_tool(contract.name, &input);
    match result {
        Ok(output) => store.finish_tool_run(&tool_run.id, "succeeded", output),
        Err(error) => store.finish_tool_run(&tool_run.id, "failed", json!({"error": error})),
    }
}

#[tauri::command]
pub fn desktop_propose_tool_run(
    store: State<'_, DesktopStore>,
    agent_job_id: String,
    tool_name: String,
    input: Value,
) -> Result<ToolRun, String> {
    let tool_name = tool_name.trim();
    let contract =
        contract(tool_name).ok_or_else(|| format!("Tool {tool_name} is not installed"))?;
    if contract.permissions.approval == "automatic" {
        return Err("Automatic tools must use desktop_run_low_risk_tool".into());
    }
    validate_proposed_input(contract.name, &input)?;
    let permission_snapshot = serde_json::to_value(&contract.permissions)
        .map_err(|error| format!("Unable to encode Tool permission snapshot: {error}"))?;
    store.create_tool_run(
        agent_job_id.trim(),
        contract.name,
        contract.executor.kind,
        input,
        permission_snapshot,
        "awaiting_approval",
    )
}

#[tauri::command]
pub fn desktop_decide_tool_run(
    store: State<'_, DesktopStore>,
    tool_run_id: String,
    approved: bool,
) -> Result<ToolRun, String> {
    store.decide_tool_run(tool_run_id.trim(), approved)
}

#[tauri::command]
pub fn desktop_start_approved_tool_run(
    store: State<'_, DesktopStore>,
    tool_run_id: String,
) -> Result<ToolRun, String> {
    store.start_approved_tool_run(tool_run_id.trim())
}

#[tauri::command]
pub fn desktop_finish_external_tool_run(
    store: State<'_, DesktopStore>,
    tool_run_id: String,
    succeeded: bool,
    output: Value,
) -> Result<ToolRun, String> {
    let tool_run = store.get_tool_run(tool_run_id.trim())?;
    if tool_run.tool_name != "python.run" || tool_run.status != "running" {
        return Err("Only a running python.run ToolRun can accept an external result".into());
    }
    store.finish_tool_run(
        tool_run_id.trim(),
        if succeeded { "succeeded" } else { "failed" },
        output,
    )
}

#[tauri::command]
pub fn desktop_list_tool_runs(
    store: State<'_, DesktopStore>,
    agent_job_id: String,
) -> Result<Vec<ToolRun>, String> {
    store.list_tool_runs(agent_job_id.trim())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_statistics_is_deterministic_and_unicode_aware() {
        let output = execute_text_statistics(&json!({"text": "Rosalind\n你好 world"})).unwrap();

        assert_eq!(output["characters"], 17);
        assert_eq!(output["words"], 3);
        assert_eq!(output["lines"], 2);
        assert_eq!(output["bytes"], 21);
    }

    #[test]
    fn text_statistics_rejects_undeclared_inputs() {
        let error = execute_text_statistics(&json!({"text": "ok", "path": "/tmp"})).unwrap_err();

        assert!(error.contains("only the text field"));
    }

    #[test]
    fn registry_exposes_a_low_risk_contract_without_permissions() {
        let contract = text_statistics_contract();
        let encoded = serde_json::to_value(contract).unwrap();

        assert_eq!(encoded["schemaVersion"], 1);
        assert_eq!(encoded["permissions"]["risk"], "low");
        assert_eq!(encoded["permissions"]["network"], "none");
        assert_eq!(encoded["permissions"]["filesystem"], json!([]));
        assert_eq!(encoded["permissions"]["secrets"], json!([]));
    }

    #[test]
    fn python_contract_requires_per_run_high_risk_approval() {
        let contract = python_run_contract();
        let encoded = serde_json::to_value(contract).unwrap();

        assert_eq!(encoded["permissions"]["risk"], "critical");
        assert_eq!(encoded["permissions"]["approval"], "per-run");
        assert_eq!(encoded["permissions"]["network"], "host");
        assert_eq!(encoded["permissions"]["filesystem"][0]["scope"], "host");
    }

    #[test]
    fn python_contract_rejects_extra_fields_and_oversized_code() {
        assert!(
            validate_proposed_input("python.run", &json!({"code": "print(1)", "cwd": "/"}))
                .is_err()
        );
        assert!(
            validate_proposed_input("python.run", &json!({"code": "x".repeat(50_001)})).is_err()
        );
    }
}
