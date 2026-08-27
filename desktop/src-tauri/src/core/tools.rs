use std::{
    collections::HashMap,
    env, fs,
    fs::File,
    io::Read,
    path::{Path, PathBuf},
    process::{Command, ExitStatus, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant},
};

use command_group::{CommandGroup, GroupChild};
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager as _, State};

use super::storage::{Artifact, DesktopStore, NewArtifact, ToolRun};

const MAX_TEXT_CHARACTERS: usize = 500_000;
const MAX_PYTHON_INPUT_BYTES: usize = 64 * 1024;
const MAX_CAPTURE_BYTES: u64 = 128 * 1024;
const MAX_OUTPUT_BYTES: u64 = 20 * 1024 * 1024;
const MAX_OUTPUT_FILES: usize = 100;
const MAX_ARTIFACT_PREVIEW_BYTES: usize = 512 * 1024;
const PYTHON_TIMEOUT: Duration = Duration::from_secs(60);
const PROCESS_POLL_INTERVAL: Duration = Duration::from_millis(25);
const OUTPUT_SCAN_INTERVAL: Duration = Duration::from_millis(250);

const INHERITED_ENVIRONMENT: &[&str] = &[
    "PATH",
    "SystemRoot",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TMP",
    "TEMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
];

#[derive(Clone)]
pub struct ToolManager {
    inner: Arc<ToolManagerInner>,
}

struct ToolManagerInner {
    python: PathBuf,
    runs_root: PathBuf,
    active: Mutex<HashMap<String, Arc<AtomicBool>>>,
}

struct ActiveRun {
    id: String,
    manager: Arc<ToolManagerInner>,
    cancelled: Arc<AtomicBool>,
}

impl Drop for ActiveRun {
    fn drop(&mut self) {
        if let Ok(mut active) = self.manager.active.lock() {
            active.remove(&self.id);
        }
    }
}

#[derive(Debug)]
struct ExecutionLimits {
    timeout: Duration,
    max_capture_bytes: u64,
    max_output_bytes: u64,
    max_output_files: usize,
}

impl Default for ExecutionLimits {
    fn default() -> Self {
        Self {
            timeout: PYTHON_TIMEOUT,
            max_capture_bytes: MAX_CAPTURE_BYTES,
            max_output_bytes: MAX_OUTPUT_BYTES,
            max_output_files: MAX_OUTPUT_FILES,
        }
    }
}

#[derive(Debug)]
struct ToolExecution {
    terminal_status: &'static str,
    output: Value,
    artifacts: Vec<NewArtifact>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct OutputFile {
    name: String,
    size: u64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndexedOutputFile {
    artifact_id: String,
    name: String,
    size: u64,
    sha256: String,
    kind: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ArtifactPreview {
    artifact: Artifact,
    previewable: bool,
    content: Option<String>,
    truncated: bool,
}

#[derive(Debug)]
struct OutputScan {
    files: Vec<OutputFile>,
    total_bytes: u64,
    exceeded: bool,
}

impl ToolManager {
    pub fn new(python: PathBuf, runs_root: PathBuf) -> Result<Self, String> {
        fs::create_dir_all(&runs_root).map_err(|error| {
            format!(
                "Unable to create Tool Manager run directory {}: {error}",
                runs_root.display()
            )
        })?;
        Ok(Self {
            inner: Arc::new(ToolManagerInner {
                python,
                runs_root,
                active: Mutex::new(HashMap::new()),
            }),
        })
    }

    pub fn cancel_all(&self) {
        if let Ok(active) = self.inner.active.lock() {
            for cancellation in active.values() {
                cancellation.store(true, Ordering::Release);
            }
        }
    }

    fn cancel(&self, tool_run_id: &str) -> Result<(), String> {
        let cancellation = self
            .inner
            .active
            .lock()
            .map_err(|_| "Tool Manager active-run lock was poisoned".to_string())?
            .get(tool_run_id)
            .cloned()
            .ok_or_else(|| "ToolRun does not have an active native process".to_string())?;
        cancellation.store(true, Ordering::Release);
        Ok(())
    }

    fn verified_artifact_path(&self, artifact: &Artifact) -> Result<PathBuf, String> {
        let relative = Path::new(&artifact.path);
        if relative.is_absolute()
            || !relative
                .components()
                .all(|component| matches!(component, std::path::Component::Normal(_)))
        {
            return Err("Artifact path is outside its ToolRun output directory".into());
        }
        let output_root = self
            .inner
            .runs_root
            .join(&artifact.tool_run_id)
            .join("output")
            .canonicalize()
            .map_err(|error| format!("Unable to locate Artifact output directory: {error}"))?;
        let path = output_root
            .join(relative)
            .canonicalize()
            .map_err(|error| format!("Unable to locate Artifact file: {error}"))?;
        if !path.starts_with(&output_root) || !path.is_file() {
            return Err("Artifact resolved outside its ToolRun output directory".into());
        }
        let size = file_size(&path);
        if size != artifact.size_bytes.max(0) as u64 || sha256_file(&path)? != artifact.sha256 {
            return Err(
                "Artifact changed after it was indexed; preview and reveal are blocked".into(),
            );
        }
        Ok(path)
    }

    fn register(&self, tool_run_id: &str) -> Result<ActiveRun, String> {
        let cancelled = Arc::new(AtomicBool::new(false));
        let mut active = self
            .inner
            .active
            .lock()
            .map_err(|_| "Tool Manager active-run lock was poisoned".to_string())?;
        if active.contains_key(tool_run_id) {
            return Err("ToolRun is already executing".into());
        }
        active.insert(tool_run_id.to_string(), Arc::clone(&cancelled));
        Ok(ActiveRun {
            id: tool_run_id.to_string(),
            manager: Arc::clone(&self.inner),
            cancelled,
        })
    }

    #[cfg(test)]
    fn execute_python(&self, tool_run_id: &str, code: &str) -> Result<ToolExecution, String> {
        self.execute_python_with_limits(tool_run_id, code, &ExecutionLimits::default())
    }

    #[cfg(test)]
    fn execute_python_with_limits(
        &self,
        tool_run_id: &str,
        code: &str,
        limits: &ExecutionLimits,
    ) -> Result<ToolExecution, String> {
        let active_run = self.register(tool_run_id)?;
        self.execute_registered_python(tool_run_id, code, limits, &active_run)
    }

    fn execute_registered_python(
        &self,
        tool_run_id: &str,
        code: &str,
        limits: &ExecutionLimits,
        active_run: &ActiveRun,
    ) -> Result<ToolExecution, String> {
        if code.as_bytes().len() > MAX_PYTHON_INPUT_BYTES {
            return Err("python.run code exceeds the 64 KiB input limit".into());
        }
        let run_root = self.inner.runs_root.join(tool_run_id);
        let input_root = run_root.join("input");
        let output_root = run_root.join("output");
        fs::create_dir_all(&input_root)
            .and_then(|_| fs::create_dir_all(&output_root))
            .map_err(|error| format!("Unable to create isolated ToolRun directories: {error}"))?;
        let script_path = input_root.join("main.py");
        fs::write(&script_path, code)
            .map_err(|error| format!("Unable to write the approved Python input: {error}"))?;
        let stdout_path = run_root.join("stdout.log");
        let stderr_path = run_root.join("stderr.log");
        let stdout = File::create(&stdout_path)
            .map_err(|error| format!("Unable to create Python stdout log: {error}"))?;
        let stderr = File::create(&stderr_path)
            .map_err(|error| format!("Unable to create Python stderr log: {error}"))?;

        let mut command = Command::new(&self.inner.python);
        command
            .arg("-I")
            .arg("-B")
            .arg(&script_path)
            .current_dir(&output_root)
            .env_clear()
            .env("PYTHONIOENCODING", "utf-8")
            .env("PYTHONUNBUFFERED", "1")
            .env("OPENROSALIND_TOOL_RUN_ID", tool_run_id)
            .env("OPENROSALIND_OUTPUT_DIR", &output_root)
            .stdin(Stdio::null())
            .stdout(Stdio::from(stdout))
            .stderr(Stdio::from(stderr));
        for key in INHERITED_ENVIRONMENT {
            if let Some(value) = env::var_os(key) {
                command.env(key, value);
            }
        }

        let mut child = command.group_spawn().map_err(|error| {
            format!(
                "Unable to start native Python executor {}: {error}",
                self.inner.python.display()
            )
        })?;
        let started = Instant::now();
        let mut last_output_scan = started;
        let execution_result = (|| -> Result<(ExitStatus, Option<&'static str>), String> {
            let mut forced_status = None;
            let exit_status: ExitStatus = loop {
                if active_run.cancelled.load(Ordering::Acquire) {
                    forced_status = Some("cancelled");
                    break stop_process_group(&mut child, "cancelled")?;
                }
                if started.elapsed() >= limits.timeout {
                    forced_status = Some("timed_out");
                    break stop_process_group(&mut child, "timed-out")?;
                }
                let capture_size = file_size(&stdout_path).saturating_add(file_size(&stderr_path));
                if capture_size > limits.max_capture_bytes {
                    forced_status = Some("failed");
                    break stop_process_group(&mut child, "log-limited")?;
                }
                if last_output_scan.elapsed() >= OUTPUT_SCAN_INTERVAL {
                    let scan = scan_output(
                        &output_root,
                        limits.max_output_bytes,
                        limits.max_output_files,
                    )?;
                    if scan.exceeded {
                        forced_status = Some("failed");
                        break stop_process_group(&mut child, "output-limited")?;
                    }
                    last_output_scan = Instant::now();
                }
                match child
                    .try_wait()
                    .map_err(|error| format!("Unable to inspect Python process group: {error}"))?
                {
                    Some(status) => break status,
                    None => thread::sleep(PROCESS_POLL_INTERVAL),
                }
            };
            Ok((exit_status, forced_status))
        })();
        let (exit_status, forced_status) = match execution_result {
            Ok(result) => result,
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(error);
            }
        };

        let (stdout, stdout_truncated) =
            read_bounded(&stdout_path, limits.max_capture_bytes as usize)?;
        let (stderr, stderr_truncated) =
            read_bounded(&stderr_path, limits.max_capture_bytes as usize)?;
        let output_scan = scan_output(
            &output_root,
            limits.max_output_bytes,
            limits.max_output_files,
        )?;
        let output_limit_exceeded = output_scan.exceeded
            || file_size(&stdout_path).saturating_add(file_size(&stderr_path))
                > limits.max_capture_bytes;
        let terminal_status = forced_status.unwrap_or_else(|| {
            if exit_status.success() && !output_limit_exceeded {
                "succeeded"
            } else {
                "failed"
            }
        });
        let status = match terminal_status {
            "succeeded" => "completed",
            "timed_out" => "timed_out",
            "cancelled" => "cancelled",
            _ if output_limit_exceeded => "output_limit_exceeded",
            _ => "failed",
        };
        let (indexed_files, artifacts) = if output_scan.exceeded {
            (Vec::new(), Vec::new())
        } else {
            index_output_files(&output_root, &output_scan.files)?
        };
        Ok(ToolExecution {
            terminal_status,
            output: json!({
                "ok": terminal_status == "succeeded",
                "status": status,
                "jobId": tool_run_id,
                "exitCode": exit_status.code(),
                "stdout": stdout,
                "stderr": stderr,
                "stdoutTruncated": stdout_truncated,
                "stderrTruncated": stderr_truncated,
                "files": indexed_files,
                "outputBytes": output_scan.total_bytes,
                "audit": {
                    "executor": "desktop-core:native-python",
                    "processGroup": true,
                    "environment": "allowlist",
                    "workingDirectory": "tool-run-output",
                    "timeoutSeconds": limits.timeout.as_secs(),
                    "maxCaptureBytes": limits.max_capture_bytes,
                    "maxOutputBytes": limits.max_output_bytes,
                    "maxOutputFiles": limits.max_output_files,
                }
            }),
            artifacts,
        })
    }
}

fn stop_process_group(child: &mut GroupChild, reason: &str) -> Result<ExitStatus, String> {
    if let Err(error) = child.kill() {
        if error.kind() != std::io::ErrorKind::InvalidInput {
            return Err(format!(
                "Unable to stop {reason} Python process group: {error}"
            ));
        }
    }
    child
        .wait()
        .map_err(|error| format!("Unable to reap {reason} Python process group: {error}"))
}

fn file_size(path: &Path) -> u64 {
    fs::metadata(path)
        .map(|metadata| metadata.len())
        .unwrap_or(0)
}

fn read_bounded(path: &Path, max_bytes: usize) -> Result<(String, bool), String> {
    let file = File::open(path)
        .map_err(|error| format!("Unable to read ToolRun log {}: {error}", path.display()))?;
    let mut bytes = Vec::new();
    file.take(max_bytes as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("Unable to read ToolRun log {}: {error}", path.display()))?;
    let truncated = bytes.len() > max_bytes;
    bytes.truncate(max_bytes);
    Ok((String::from_utf8_lossy(&bytes).into_owned(), truncated))
}

fn index_output_files(
    output_root: &Path,
    files: &[OutputFile],
) -> Result<(Vec<IndexedOutputFile>, Vec<NewArtifact>), String> {
    let mut indexed = Vec::with_capacity(files.len());
    let mut artifacts = Vec::with_capacity(files.len());
    for file in files {
        let path = output_root.join(&file.name);
        let sha256 = sha256_file(&path)?;
        let artifact_id = uuid::Uuid::new_v4().to_string();
        let kind = artifact_kind(&file.name).to_string();
        indexed.push(IndexedOutputFile {
            artifact_id: artifact_id.clone(),
            name: file.name.clone(),
            size: file.size,
            sha256: sha256.clone(),
            kind: kind.clone(),
        });
        artifacts.push(NewArtifact {
            id: artifact_id,
            kind,
            path: file.name.clone(),
            sha256,
            size_bytes: file.size as i64,
        });
    }
    Ok((indexed, artifacts))
}

fn artifact_kind(name: &str) -> &'static str {
    match Path::new(name)
        .extension()
        .and_then(|extension| extension.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some(
            "txt" | "md" | "markdown" | "csv" | "tsv" | "json" | "jsonl" | "yaml" | "yml" | "xml"
            | "html" | "css" | "js" | "ts" | "py" | "r" | "sql" | "log" | "fasta" | "fa" | "fastq"
            | "fq",
        ) => "text",
        _ => "file",
    }
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file = File::open(path)
        .map_err(|error| format!("Unable to hash Artifact {}: {error}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| format!("Unable to hash Artifact {}: {error}", path.display()))?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn scan_output(root: &Path, max_bytes: u64, max_files: usize) -> Result<OutputScan, String> {
    let mut scan = OutputScan {
        files: Vec::new(),
        total_bytes: 0,
        exceeded: false,
    };
    let mut directories = vec![root.to_path_buf()];
    while let Some(directory) = directories.pop() {
        for entry in fs::read_dir(directory)
            .map_err(|error| format!("Unable to inspect ToolRun output: {error}"))?
        {
            let entry =
                entry.map_err(|error| format!("Unable to inspect ToolRun output: {error}"))?;
            let metadata = entry
                .path()
                .symlink_metadata()
                .map_err(|error| format!("Unable to inspect ToolRun output entry: {error}"))?;
            if metadata.file_type().is_symlink() {
                continue;
            }
            if metadata.is_dir() {
                directories.push(entry.path());
            } else if metadata.is_file() {
                scan.total_bytes = scan.total_bytes.saturating_add(metadata.len());
                if scan.files.len() >= max_files {
                    scan.exceeded = true;
                    break;
                }
                let path = entry.path();
                let name = path
                    .strip_prefix(root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .replace('\\', "/");
                scan.files.push(OutputFile {
                    name,
                    size: metadata.len(),
                });
                if scan.total_bytes > max_bytes {
                    scan.exceeded = true;
                    break;
                }
            }
        }
        if scan.exceeded {
            break;
        }
    }
    scan.files.sort_by(|left, right| left.name.cmp(&right.name));
    Ok(scan)
}

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
            entrypoint: "desktop-core:native-python",
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
            if code.is_empty()
                || code.chars().count() > 50_000
                || code.len() > MAX_PYTHON_INPUT_BYTES
                || code.contains('\0')
            {
                return Err(
                    "python.run code must contain 1 to 50000 characters, fit within 64 KiB, and contain no NUL bytes".into(),
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
pub async fn desktop_execute_approved_python_tool(
    app: AppHandle,
    tool_run_id: String,
) -> Result<ToolRun, String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let tool_run_id = tool_run_id.trim().to_string();
    tauri::async_runtime::spawn_blocking(move || {
        execute_approved_python_tool(&manager, &store, &tool_run_id)
    })
    .await
    .map_err(|error| format!("Native Python executor task failed: {error}"))?
}

fn execute_approved_python_tool(
    manager: &ToolManager,
    store: &DesktopStore,
    tool_run_id: &str,
) -> Result<ToolRun, String> {
    let tool_run = store.get_tool_run(tool_run_id)?;
    if tool_run.tool_name != "python.run" || tool_run.status != "approved" {
        return Err("Only an approved python.run ToolRun can enter the native executor".into());
    }
    let code = tool_run
        .input()
        .get("code")
        .and_then(Value::as_str)
        .ok_or_else(|| "Approved python.run input is missing its code field".to_string())?
        .to_string();
    let active_run = manager.register(tool_run_id)?;
    store.start_approved_tool_run(tool_run_id)?;
    let execution = manager.execute_registered_python(
        tool_run_id,
        &code,
        &ExecutionLimits::default(),
        &active_run,
    );
    let finished = match execution {
        Ok(execution) => {
            match store.replace_tool_run_artifacts(tool_run_id, &execution.artifacts) {
                Ok(_) => {
                    store.finish_tool_run(tool_run_id, execution.terminal_status, execution.output)
                }
                Err(error) => {
                    let mut output = execution.output;
                    if let Some(object) = output.as_object_mut() {
                        object.insert("ok".into(), Value::Bool(false));
                        object.insert(
                            "status".into(),
                            Value::String("artifact_index_error".into()),
                        );
                        object.insert("error".into(), Value::String(error));
                        object.insert("files".into(), Value::Array(Vec::new()));
                    }
                    store.finish_tool_run(tool_run_id, "failed", output)
                }
            }
        }
        Err(error) => store.finish_tool_run(
            tool_run_id,
            "failed",
            json!({
                "ok": false,
                "status": "executor_error",
                "jobId": tool_run_id,
                "error": error,
                "files": [],
            }),
        ),
    };
    drop(active_run);
    finished
}

#[tauri::command]
pub fn desktop_cancel_tool_run(
    manager: State<'_, ToolManager>,
    store: State<'_, DesktopStore>,
    tool_run_id: String,
) -> Result<ToolRun, String> {
    let tool_run_id = tool_run_id.trim();
    manager.cancel(tool_run_id)?;
    match store.request_tool_run_cancellation(tool_run_id) {
        Ok(tool_run) => Ok(tool_run),
        Err(error) => {
            let current = store.get_tool_run(tool_run_id)?;
            if matches!(
                current.status.as_str(),
                "succeeded" | "failed" | "cancelled" | "timed_out"
            ) {
                Ok(current)
            } else {
                Err(error)
            }
        }
    }
}

#[tauri::command]
pub fn desktop_list_tool_runs(
    store: State<'_, DesktopStore>,
    agent_job_id: String,
) -> Result<Vec<ToolRun>, String> {
    store.list_tool_runs(agent_job_id.trim())
}

#[tauri::command]
pub fn desktop_list_tool_artifacts(
    store: State<'_, DesktopStore>,
    tool_run_id: String,
) -> Result<Vec<Artifact>, String> {
    store.list_tool_run_artifacts(tool_run_id.trim())
}

#[tauri::command]
pub async fn desktop_read_tool_artifact(
    app: AppHandle,
    artifact_id: String,
) -> Result<ArtifactPreview, String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let artifact_id = artifact_id.trim().to_string();
    tauri::async_runtime::spawn_blocking(move || read_tool_artifact(&manager, &store, &artifact_id))
        .await
        .map_err(|error| format!("Artifact preview task failed: {error}"))?
}

fn read_tool_artifact(
    manager: &ToolManager,
    store: &DesktopStore,
    artifact_id: &str,
) -> Result<ArtifactPreview, String> {
    let artifact = store.get_artifact(artifact_id)?;
    let path = manager.verified_artifact_path(&artifact)?;
    if artifact.kind != "text" {
        return Ok(ArtifactPreview {
            artifact,
            previewable: false,
            content: None,
            truncated: false,
        });
    }
    let file =
        File::open(&path).map_err(|error| format!("Unable to read Artifact preview: {error}"))?;
    let mut bytes = Vec::new();
    file.take(MAX_ARTIFACT_PREVIEW_BYTES as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("Unable to read Artifact preview: {error}"))?;
    let truncated = bytes.len() > MAX_ARTIFACT_PREVIEW_BYTES;
    bytes.truncate(MAX_ARTIFACT_PREVIEW_BYTES);
    match String::from_utf8(bytes) {
        Ok(content) => Ok(ArtifactPreview {
            artifact,
            previewable: true,
            content: Some(content),
            truncated,
        }),
        Err(_) => Ok(ArtifactPreview {
            artifact,
            previewable: false,
            content: None,
            truncated: false,
        }),
    }
}

#[tauri::command]
pub async fn desktop_reveal_tool_artifact(
    app: AppHandle,
    artifact_id: String,
) -> Result<(), String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let artifact_id = artifact_id.trim().to_string();
    tauri::async_runtime::spawn_blocking(move || {
        reveal_tool_artifact(&manager, &store, &artifact_id)
    })
    .await
    .map_err(|error| format!("Artifact reveal task failed: {error}"))?
}

fn reveal_tool_artifact(
    manager: &ToolManager,
    store: &DesktopStore,
    artifact_id: &str,
) -> Result<(), String> {
    let artifact = store.get_artifact(artifact_id)?;
    let path = manager.verified_artifact_path(&artifact)?;
    reveal_artifact(&path)
}

fn reveal_artifact(path: &Path) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg("-R").arg(path);
        command
    };
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("explorer.exe");
        command.arg("/select,").arg(path);
        command
    };
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(path.parent().unwrap_or(path));
        command
    };
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("Unable to reveal Artifact in the file manager: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_tool_manager() -> (ToolManager, PathBuf) {
        let root = env::temp_dir().join(format!(
            "open-rosalind-tool-manager-test-{}",
            uuid::Uuid::new_v4()
        ));
        let python = env::var_os("OPENROSALIND_PYTHON")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "python" } else { "python3" }));
        let manager = ToolManager::new(python, root.clone()).unwrap();
        (manager, root)
    }

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
        assert!(validate_proposed_input(
            "python.run",
            &json!({"code": "界".repeat(MAX_PYTHON_INPUT_BYTES / 3 + 1)})
        )
        .is_err());
    }

    #[test]
    fn native_python_executor_captures_logs_and_output_files() {
        let (manager, root) = test_tool_manager();
        let execution = manager
            .execute_python(
                "successful-run",
                "from pathlib import Path\nprint('hello from tool manager')\nPath('result.txt').write_text('done', encoding='utf-8')",
            )
            .unwrap();

        assert_eq!(execution.terminal_status, "succeeded");
        assert_eq!(execution.output["status"], "completed");
        assert!(execution.output["stdout"]
            .as_str()
            .unwrap()
            .contains("hello from tool manager"));
        assert_eq!(execution.output["files"][0]["name"], "result.txt");
        assert_eq!(
            execution.output["files"][0]["sha256"],
            sha256_file(&root.join("successful-run/output/result.txt")).unwrap()
        );
        assert!(!execution.output["files"][0]["artifactId"]
            .as_str()
            .unwrap()
            .is_empty());
        let indexed = &execution.artifacts[0];
        let artifact = Artifact {
            id: indexed.id.clone(),
            agent_job_id: "test-job".into(),
            tool_run_id: "successful-run".into(),
            kind: indexed.kind.clone(),
            path: indexed.path.clone(),
            sha256: indexed.sha256.clone(),
            size_bytes: indexed.size_bytes,
            created_at: 0,
        };
        assert!(manager.verified_artifact_path(&artifact).is_ok());
        fs::write(root.join("successful-run/output/result.txt"), "changed").unwrap();
        assert!(manager.verified_artifact_path(&artifact).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn native_python_executor_times_out_the_process_group() {
        let (manager, root) = test_tool_manager();
        let execution = manager
            .execute_python_with_limits(
                "timed-out-run",
                "import time\ntime.sleep(5)",
                &ExecutionLimits {
                    timeout: Duration::from_millis(150),
                    ..ExecutionLimits::default()
                },
            )
            .unwrap();

        assert_eq!(execution.terminal_status, "timed_out");
        assert_eq!(execution.output["status"], "timed_out");
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn native_python_executor_accepts_cross_thread_cancellation() {
        let (manager, root) = test_tool_manager();
        let executor = manager.clone();
        let handle = thread::spawn(move || {
            executor.execute_python("cancelled-run", "import time\ntime.sleep(5)")
        });
        for _ in 0..100 {
            if manager
                .inner
                .active
                .lock()
                .unwrap()
                .contains_key("cancelled-run")
            {
                break;
            }
            thread::sleep(Duration::from_millis(5));
        }
        manager.cancel("cancelled-run").unwrap();
        let execution = handle.join().unwrap().unwrap();

        assert_eq!(execution.terminal_status, "cancelled");
        assert_eq!(execution.output["status"], "cancelled");
        fs::remove_dir_all(root).unwrap();
    }
}
