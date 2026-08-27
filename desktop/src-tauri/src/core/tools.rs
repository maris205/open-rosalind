use std::{
    collections::HashMap,
    env,
    ffi::OsString,
    fs,
    fs::File,
    io::{Read, Write},
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
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};

use super::storage::{Artifact, AuthorizedProjectDirectory, DesktopStore, NewArtifact, ToolRun};

const MAX_TEXT_CHARACTERS: usize = 500_000;
const MAX_PYTHON_INPUT_BYTES: usize = 64 * 1024;
const MAX_CAPTURE_BYTES: u64 = 128 * 1024;
const MAX_OUTPUT_BYTES: u64 = 20 * 1024 * 1024;
const MAX_OUTPUT_FILES: usize = 100;
const MAX_ARTIFACT_PREVIEW_BYTES: usize = 512 * 1024;
const MAX_PROJECT_FILE_PREVIEW_BYTES: usize = 64 * 1024;
const MAX_PROJECT_FILE_READ_BYTES: usize = 10 * 1024 * 1024;
const MAX_PROJECT_FILE_WRITE_BYTES: usize = 256 * 1024;
const MAX_PROJECT_LIST_FILES: usize = 200;
const MAX_PROJECT_LIST_DEPTH: usize = 4;
const PYTHON_TIMEOUT: Duration = Duration::from_secs(60);
const PROCESS_POLL_INTERVAL: Duration = Duration::from_millis(25);
const OUTPUT_SCAN_INTERVAL: Duration = Duration::from_millis(250);
const CONTAINER_IMAGE: &str = "docker.io/library/python@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134";
const CONTAINER_MEMORY_MB: u32 = 512;
const CONTAINER_CPUS: f32 = 1.0;
const CONTAINER_PIDS: u32 = 64;
const CONTAINER_PULL_TIMEOUT: Duration = Duration::from_secs(300);

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

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ArtifactExport {
    file_name: String,
    size_bytes: u64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ContainerCapability {
    installed: bool,
    available: bool,
    daemon_version: Option<String>,
    image: &'static str,
    image_available: bool,
    reason: Option<String>,
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
            .ok_or_else(|| "ToolRun does not have an active executor process".to_string())?;
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
                "Artifact changed after it was indexed; preview, reveal, and export are blocked"
                    .into(),
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
            .env("PYTHONNOUSERSITE", "1")
            .env("PYTHONSAFEPATH", "1")
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

    fn execute_project_file_write(
        &self,
        tool_run_id: &str,
        project: &AuthorizedProjectDirectory,
        input: &Value,
    ) -> Result<ToolExecution, String> {
        if !project.write {
            return Err("The project directory is not authorized for writes".into());
        }
        let write = project_write_input(input)?;
        let destination = prepare_project_write_destination(project, write.relative)?;
        let existing = match destination.symlink_metadata() {
            Ok(metadata) => {
                if metadata.file_type().is_symlink() || !metadata.is_file() {
                    return Err("Project write destination is not a regular file".into());
                }
                if metadata.len() > MAX_PROJECT_FILE_WRITE_BYTES as u64 {
                    return Err("Existing project file exceeds the 256 KiB rollback limit".into());
                }
                Some((metadata, sha256_file(&destination)?))
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
            Err(error) => {
                return Err(format!(
                    "Unable to inspect project write destination: {error}"
                ))
            }
        };
        match (&existing, write.expected_sha256) {
            (Some((_, actual)), Some(expected)) if actual.eq_ignore_ascii_case(expected) => {}
            (Some(_), None) => {
                return Err("Overwriting an existing file requires its expectedSha256".into())
            }
            (Some((_, actual)), Some(_)) => {
                return Err(format!(
                    "Project file changed after it was reviewed; expected digest does not match {actual}"
                ))
            }
            (None, Some(_)) => {
                return Err("A file expected for replacement no longer exists".into())
            }
            (None, None) => {}
        }

        let output_root = self.inner.runs_root.join(tool_run_id).join("output");
        let written_artifact = Path::new("written").join(write.relative);
        let written_path = output_root.join(&written_artifact);
        fs::create_dir_all(
            written_path
                .parent()
                .ok_or("Invalid written artifact path")?,
        )
        .map_err(|error| format!("Unable to create project-write artifact directory: {error}"))?;
        fs::write(&written_path, write.content)
            .map_err(|error| format!("Unable to stage project-write content: {error}"))?;
        let mut output_files = vec![OutputFile {
            name: written_artifact.to_string_lossy().replace('\\', "/"),
            size: write.content.len() as u64,
        }];
        if existing.is_some() {
            let previous_artifact = Path::new("previous").join(write.relative);
            let previous_path = output_root.join(&previous_artifact);
            fs::create_dir_all(
                previous_path
                    .parent()
                    .ok_or("Invalid rollback artifact path")?,
            )
            .map_err(|error| format!("Unable to create rollback artifact directory: {error}"))?;
            fs::copy(&destination, &previous_path)
                .map_err(|error| format!("Unable to preserve previous project file: {error}"))?;
            if let Some((_, digest)) = &existing {
                if sha256_file(&previous_path)? != *digest {
                    return Err(
                        "Project file changed while its rollback copy was being preserved".into(),
                    );
                }
            }
            output_files.push(OutputFile {
                name: previous_artifact.to_string_lossy().replace('\\', "/"),
                size: existing
                    .as_ref()
                    .map(|(metadata, _)| metadata.len())
                    .unwrap_or(0),
            });
        }
        let (indexed_files, artifacts) = index_output_files(&output_root, &output_files)?;

        let temporary = destination.with_file_name(format!(
            ".openrosalind-write-{}.tmp",
            uuid::Uuid::new_v4().simple()
        ));
        let write_result = (|| -> Result<(), String> {
            let mut file = fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&temporary)
                .map_err(|error| format!("Unable to create atomic project-write file: {error}"))?;
            file.write_all(write.content.as_bytes())
                .map_err(|error| format!("Unable to flush project-write content: {error}"))?;
            if let Some((metadata, _)) = &existing {
                fs::set_permissions(&temporary, metadata.permissions()).map_err(|error| {
                    format!("Unable to preserve project file permissions: {error}")
                })?;
            }
            file.sync_all()
                .map_err(|error| format!("Unable to flush project-write content: {error}"))?;
            drop(file);
            if let Some((_, approved_digest)) = &existing {
                if sha256_file(&destination)? != *approved_digest {
                    return Err(
                        "Project file changed after approval and before atomic replacement".into(),
                    );
                }
                fs::rename(&temporary, &destination).map_err(|error| {
                    format!("Unable to atomically replace project file: {error}")
                })?;
            } else {
                fs::hard_link(&temporary, &destination).map_err(|error| {
                    format!(
                        "Unable to atomically create project file; the destination may now exist: {error}"
                    )
                })?;
                let _ = fs::remove_file(&temporary);
            }
            sync_parent_directory(&destination)?;
            Ok(())
        })();
        if write_result.is_err() {
            let _ = fs::remove_file(&temporary);
        }
        write_result?;
        let new_sha256 = sha256_file(&destination)?;
        Ok(ToolExecution {
            terminal_status: "succeeded",
            output: json!({
                "ok": true,
                "projectId": project.project_id,
                "path": write.relative.to_string_lossy().replace('\\', "/"),
                "created": existing.is_none(),
                "previousSha256": existing.as_ref().map(|(_, digest)| digest),
                "sha256": new_sha256,
                "sizeBytes": write.content.len(),
                "rollbackArtifact": existing.is_some(),
                "files": indexed_files,
            }),
            artifacts,
        })
    }

    fn execute_registered_container_python(
        &self,
        tool_run_id: &str,
        code: &str,
        limits: &ExecutionLimits,
        active_run: &ActiveRun,
    ) -> Result<ToolExecution, String> {
        if code.as_bytes().len() > MAX_PYTHON_INPUT_BYTES {
            return Err("python.container code exceeds the 64 KiB input limit".into());
        }
        let docker = docker_executable().ok_or_else(|| {
            "Docker CLI was not found. Install and start Docker Desktop, then restart OpenRosalind."
                .to_string()
        })?;
        let capability = inspect_container_capability_with(&docker);
        if !capability.available {
            return Err(capability
                .reason
                .unwrap_or_else(|| "Docker Desktop is not available".into()));
        }
        if !capability.image_available {
            return Err("The pinned OpenRosalind container image is not installed. Prepare the Docker sandbox first.".into());
        }

        let run_root = self.inner.runs_root.join(tool_run_id);
        let input_root = run_root.join("input");
        let output_root = run_root.join("output");
        fs::create_dir_all(&input_root)
            .and_then(|_| fs::create_dir_all(&output_root))
            .map_err(|error| format!("Unable to create isolated ToolRun directories: {error}"))?;
        let script_path = input_root.join("main.py");
        fs::write(&script_path, code)
            .map_err(|error| format!("Unable to write the approved container input: {error}"))?;
        let stdout_path = run_root.join("stdout.log");
        let stderr_path = run_root.join("stderr.log");
        let stdout = File::create(&stdout_path)
            .map_err(|error| format!("Unable to create container stdout log: {error}"))?;
        let stderr = File::create(&stderr_path)
            .map_err(|error| format!("Unable to create container stderr log: {error}"))?;
        let container_name = container_name(tool_run_id)?;
        let arguments =
            container_run_arguments(tool_run_id, &container_name, &input_root, &output_root)?;

        let mut command = Command::new(&docker);
        command
            .args(arguments)
            .stdin(Stdio::null())
            .stdout(Stdio::from(stdout))
            .stderr(Stdio::from(stderr));
        let mut child = command
            .group_spawn()
            .map_err(|error| format!("Unable to start Docker Container Executor: {error}"))?;
        let started = Instant::now();
        let mut last_output_scan = started;
        let execution_result = (|| -> Result<(ExitStatus, Option<&'static str>), String> {
            let mut forced_status = None;
            let exit_status = loop {
                if active_run.cancelled.load(Ordering::Acquire) {
                    forced_status = Some("cancelled");
                    let status = stop_process_group(&mut child, "cancelled container")?;
                    remove_container(&docker, &container_name);
                    break status;
                }
                if started.elapsed() >= limits.timeout {
                    forced_status = Some("timed_out");
                    let status = stop_process_group(&mut child, "timed-out container")?;
                    remove_container(&docker, &container_name);
                    break status;
                }
                let capture_size = file_size(&stdout_path).saturating_add(file_size(&stderr_path));
                if capture_size > limits.max_capture_bytes {
                    forced_status = Some("failed");
                    let status = stop_process_group(&mut child, "log-limited container")?;
                    remove_container(&docker, &container_name);
                    break status;
                }
                if last_output_scan.elapsed() >= OUTPUT_SCAN_INTERVAL {
                    let scan = scan_output(
                        &output_root,
                        limits.max_output_bytes,
                        limits.max_output_files,
                    )?;
                    if scan.exceeded {
                        forced_status = Some("failed");
                        let status = stop_process_group(&mut child, "output-limited container")?;
                        remove_container(&docker, &container_name);
                        break status;
                    }
                    last_output_scan = Instant::now();
                }
                match child
                    .try_wait()
                    .map_err(|error| format!("Unable to inspect Docker process group: {error}"))?
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
                remove_container(&docker, &container_name);
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
                    "executor": "desktop-core:docker-container",
                    "image": CONTAINER_IMAGE,
                    "network": "none",
                    "readOnlyRoot": true,
                    "privileged": false,
                    "capabilities": "none",
                    "noNewPrivileges": true,
                    "user": container_user(&output_root),
                    "timeoutSeconds": limits.timeout.as_secs(),
                    "memoryMb": CONTAINER_MEMORY_MB,
                    "cpus": CONTAINER_CPUS,
                    "pids": CONTAINER_PIDS,
                    "maxCaptureBytes": limits.max_capture_bytes,
                    "maxOutputBytes": limits.max_output_bytes,
                    "maxOutputFiles": limits.max_output_files,
                }
            }),
            artifacts,
        })
    }
}

fn docker_executable() -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Some(configured) = env::var_os("OPENROSALIND_DOCKER") {
        candidates.push(PathBuf::from(configured));
    }
    candidates.push(PathBuf::from(if cfg!(windows) {
        "docker.exe"
    } else {
        "docker"
    }));
    #[cfg(target_os = "macos")]
    candidates.extend([
        PathBuf::from("/usr/local/bin/docker"),
        PathBuf::from("/opt/homebrew/bin/docker"),
        PathBuf::from("/Applications/Docker.app/Contents/Resources/bin/docker"),
    ]);
    #[cfg(target_os = "windows")]
    if let Some(program_files) = env::var_os("ProgramFiles") {
        candidates
            .push(PathBuf::from(program_files).join("Docker/Docker/resources/bin/docker.exe"));
    }
    candidates.into_iter().find(|candidate| {
        Command::new(candidate)
            .arg("--version")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|status| status.success())
            .unwrap_or(false)
    })
}

fn inspect_container_capability() -> ContainerCapability {
    match docker_executable() {
        Some(docker) => inspect_container_capability_with(&docker),
        None => ContainerCapability {
            installed: false,
            available: false,
            daemon_version: None,
            image: CONTAINER_IMAGE,
            image_available: false,
            reason: Some(
                "Docker CLI was not found. Install Docker Desktop and restart OpenRosalind.".into(),
            ),
        },
    }
}

fn inspect_container_capability_with(docker: &Path) -> ContainerCapability {
    let version = Command::new(docker)
        .args(["version", "--format", "{{.Server.Version}}"])
        .stdin(Stdio::null())
        .output();
    let Ok(version) = version else {
        return ContainerCapability {
            installed: true,
            available: false,
            daemon_version: None,
            image: CONTAINER_IMAGE,
            image_available: false,
            reason: Some("Docker Desktop could not be started or contacted.".into()),
        };
    };
    if !version.status.success() {
        return ContainerCapability {
            installed: true,
            available: false,
            daemon_version: None,
            image: CONTAINER_IMAGE,
            image_available: false,
            reason: Some("Docker Desktop is installed but its daemon is not running.".into()),
        };
    }
    let daemon_version = String::from_utf8_lossy(&version.stdout).trim().to_string();
    let image_available = Command::new(docker)
        .args(["image", "inspect", CONTAINER_IMAGE])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false);
    ContainerCapability {
        installed: true,
        available: true,
        daemon_version: (!daemon_version.is_empty()).then_some(daemon_version),
        image: CONTAINER_IMAGE,
        image_available,
        reason: (!image_available).then(|| {
            "The pinned Python image must be downloaded before the first sandbox run.".into()
        }),
    }
}

fn container_name(tool_run_id: &str) -> Result<String, String> {
    if tool_run_id.is_empty()
        || tool_run_id.len() > 64
        || !tool_run_id
            .chars()
            .all(|character| character.is_ascii_hexdigit() || character == '-')
    {
        return Err("ToolRun ID is not safe for a Docker container name".into());
    }
    Ok(format!(
        "openrosalind-{}",
        tool_run_id.replace('-', "").to_ascii_lowercase()
    ))
}

#[cfg(unix)]
fn container_user(output_root: &Path) -> String {
    use std::os::unix::fs::MetadataExt;

    fs::metadata(output_root)
        .ok()
        .filter(|metadata| metadata.uid() != 0)
        .map(|metadata| format!("{}:{}", metadata.uid(), metadata.gid()))
        .unwrap_or_else(|| "65532:65532".into())
}

#[cfg(not(unix))]
fn container_user(_output_root: &Path) -> String {
    "65532:65532".into()
}

fn container_run_arguments(
    tool_run_id: &str,
    container_name: &str,
    input_root: &Path,
    output_root: &Path,
) -> Result<Vec<OsString>, String> {
    if container_name != self::container_name(tool_run_id)? {
        return Err("Container name does not match its ToolRun ID".into());
    }
    let input_source = input_root
        .to_str()
        .ok_or_else(|| "Container input path is not valid Unicode".to_string())?;
    let output_source = output_root
        .to_str()
        .ok_or_else(|| "Container output path is not valid Unicode".to_string())?;
    if [input_source, output_source].iter().any(|path| {
        path.chars()
            .any(|character| matches!(character, ',' | '\n' | '\r'))
    }) {
        return Err("Container mount paths cannot contain commas or newlines".into());
    }
    let input_mount = format!("type=bind,source={input_source},target=/workspace/input,readonly");
    let output_mount = format!("type=bind,source={output_source},target=/workspace/output");
    Ok([
        "run".into(),
        "--rm".into(),
        "--pull=never".into(),
        "--name".into(),
        container_name.into(),
        "--network=none".into(),
        "--read-only".into(),
        "--cap-drop=ALL".into(),
        "--security-opt=no-new-privileges=true".into(),
        "--pids-limit=64".into(),
        "--memory=512m".into(),
        "--cpus=1".into(),
        "--ipc=none".into(),
        "--ulimit=nofile=256:256".into(),
        "--stop-timeout=2".into(),
        "--user".into(),
        container_user(output_root).into(),
        "--workdir=/workspace/output".into(),
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m".into(),
        "--mount".into(),
        input_mount.into(),
        "--mount".into(),
        output_mount.into(),
        "--env=HOME=/tmp".into(),
        "--env=PYTHONDONTWRITEBYTECODE=1".into(),
        "--env=PYTHONUNBUFFERED=1".into(),
        "--env=OPENROSALIND_OUTPUT_DIR=/workspace/output".into(),
        "--label".into(),
        format!("com.openrosalind.tool-run={tool_run_id}").into(),
        CONTAINER_IMAGE.into(),
        "python".into(),
        "-I".into(),
        "-B".into(),
        "/workspace/input/main.py".into(),
    ]
    .into_iter()
    .collect())
}

fn remove_container(docker: &Path, container_name: &str) {
    let _ = Command::new(docker)
        .args(["container", "rm", "--force", container_name])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status();
}

fn prepare_container_image() -> Result<ContainerCapability, String> {
    let docker = docker_executable().ok_or_else(|| {
        "Docker CLI was not found. Install and start Docker Desktop, then restart OpenRosalind."
            .to_string()
    })?;
    let capability = inspect_container_capability_with(&docker);
    if !capability.available {
        return Err(capability
            .reason
            .unwrap_or_else(|| "Docker Desktop is not available".into()));
    }
    if capability.image_available {
        return Ok(capability);
    }
    let mut command = Command::new(&docker);
    command
        .args(["image", "pull", "--quiet", CONTAINER_IMAGE])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    let mut child = command
        .group_spawn()
        .map_err(|error| format!("Unable to download the pinned container image: {error}"))?;
    let started = Instant::now();
    let status = loop {
        if started.elapsed() >= CONTAINER_PULL_TIMEOUT {
            let _ = stop_process_group(&mut child, "timed-out image download");
            return Err("Downloading the pinned container image timed out after 5 minutes".into());
        }
        match child
            .try_wait()
            .map_err(|error| format!("Unable to inspect Docker image download: {error}"))?
        {
            Some(status) => break status,
            None => thread::sleep(Duration::from_millis(100)),
        }
    };
    if !status.success() {
        return Err("Docker could not download the pinned OpenRosalind container image".into());
    }
    let capability = inspect_container_capability_with(&docker);
    if !capability.image_available {
        return Err("Docker reported success but the pinned image is still unavailable".into());
    }
    Ok(capability)
}

fn stop_process_group(child: &mut GroupChild, reason: &str) -> Result<ExitStatus, String> {
    if let Err(error) = child.kill() {
        if error.kind() != std::io::ErrorKind::InvalidInput {
            return Err(format!("Unable to stop {reason} process group: {error}"));
        }
    }
    child
        .wait()
        .map_err(|error| format!("Unable to reap {reason} process group: {error}"))
}

fn file_size(path: &Path) -> u64 {
    fs::metadata(path)
        .map(|metadata| metadata.len())
        .unwrap_or(0)
}

fn sync_parent_directory(path: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        let parent = path
            .parent()
            .ok_or_else(|| "Project file does not have a parent directory".to_string())?;
        File::open(parent)
            .and_then(|directory| directory.sync_all())
            .map_err(|error| format!("Unable to flush project directory: {error}"))?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
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
    #[serde(skip_serializing_if = "Option::is_none")]
    image: Option<&'static str>,
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
    #[serde(skip_serializing_if = "Option::is_none")]
    memory_mb: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cpu: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pids: Option<u32>,
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
            image: None,
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
            memory_mb: None,
            cpu: None,
            pids: None,
        },
    }
}

fn project_files_list_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "project.files.list",
        version: "1.0.0",
        title: "列出项目文件",
        description: "列出当前 AgentJob 所属科研项目已授权目录中的非敏感文件。",
        executor: ToolExecutor {
            kind: "native",
            entrypoint: "desktop-core:project-files-list",
            image: None,
        },
        permissions: ToolPermissions {
            risk: "low",
            approval: "automatic",
            filesystem: vec![ToolFilesystemPermission {
                scope: "project-root",
                mode: "read",
            }],
            network: "none",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 2,
            max_input_bytes: 1024,
            max_output_bytes: 512 * 1024,
            memory_mb: None,
            cpu: None,
            pids: None,
        },
    }
}

fn project_file_read_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "project.file.read",
        version: "1.0.0",
        title: "读取项目文本",
        description: "读取当前科研项目授权目录内一个受限 UTF-8 文本文件的预览。",
        executor: ToolExecutor {
            kind: "native",
            entrypoint: "desktop-core:project-file-read",
            image: None,
        },
        permissions: ToolPermissions {
            risk: "low",
            approval: "automatic",
            filesystem: vec![ToolFilesystemPermission {
                scope: "project-root",
                mode: "read",
            }],
            network: "none",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 2,
            max_input_bytes: 2048,
            max_output_bytes: MAX_PROJECT_FILE_PREVIEW_BYTES,
            memory_mb: None,
            cpu: None,
            pids: None,
        },
    }
}

fn project_file_write_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "project.file.write",
        version: "1.0.0-alpha.1",
        title: "写入项目文本",
        description: "经用户逐次批准后，原子写入授权项目内一个非敏感文本文件。",
        executor: ToolExecutor {
            kind: "native",
            entrypoint: "desktop-core:project-file-write",
            image: None,
        },
        permissions: ToolPermissions {
            risk: "medium",
            approval: "per-run",
            filesystem: vec![ToolFilesystemPermission {
                scope: "project-root",
                mode: "write",
            }],
            network: "none",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 2,
            max_input_bytes: MAX_PROJECT_FILE_WRITE_BYTES + 4096,
            max_output_bytes: MAX_PROJECT_FILE_WRITE_BYTES * 2,
            memory_mb: None,
            cpu: None,
            pids: None,
        },
    }
}

fn contracts() -> Vec<ToolContract> {
    vec![
        text_statistics_contract(),
        project_files_list_contract(),
        project_file_read_contract(),
        project_file_write_contract(),
        python_run_contract(),
        python_container_contract(),
    ]
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
            image: None,
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
            memory_mb: None,
            cpu: None,
            pids: None,
        },
    }
}

fn python_container_contract() -> ToolContract {
    ToolContract {
        schema_version: 1,
        name: "python.container",
        version: "1.0.0-alpha.1",
        title: "在 Docker 沙箱运行 Python",
        description: "在固定镜像、默认断网和最小权限的临时容器中运行用户逐次确认的代码。",
        executor: ToolExecutor {
            kind: "container",
            entrypoint: "python -I -B /workspace/input/main.py",
            image: Some(CONTAINER_IMAGE),
        },
        permissions: ToolPermissions {
            risk: "high",
            approval: "per-run",
            filesystem: vec![
                ToolFilesystemPermission {
                    scope: "job-input",
                    mode: "read",
                },
                ToolFilesystemPermission {
                    scope: "job-output",
                    mode: "write",
                },
            ],
            network: "none",
            secrets: vec![],
        },
        resources: ToolResources {
            timeout_seconds: 60,
            max_input_bytes: 64 * 1024,
            max_output_bytes: 20 * 1024 * 1024,
            memory_mb: Some(CONTAINER_MEMORY_MB),
            cpu: Some(CONTAINER_CPUS),
            pids: Some(CONTAINER_PIDS),
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

fn execute_project_files_list(
    project: &AuthorizedProjectDirectory,
    input: &Value,
) -> Result<Value, String> {
    let object = input
        .as_object()
        .ok_or_else(|| "project.files.list input must be an object".to_string())?;
    if !object.is_empty() {
        return Err("project.files.list does not accept input fields".into());
    }
    let mut files = Vec::new();
    let mut directories = vec![(project.root.clone(), 0_usize)];
    let mut truncated = false;
    while let Some((directory, depth)) = directories.pop() {
        let mut entries = fs::read_dir(&directory)
            .map_err(|error| format!("Unable to list authorized project directory: {error}"))?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to list authorized project directory: {error}"))?;
        entries.sort_by_key(|entry| entry.file_name());
        for entry in entries {
            let Some(name) = entry.file_name().to_str().map(str::to_string) else {
                continue;
            };
            if should_skip_project_entry(&name) {
                continue;
            }
            let metadata = entry
                .path()
                .symlink_metadata()
                .map_err(|error| format!("Unable to inspect authorized project entry: {error}"))?;
            if metadata.file_type().is_symlink() {
                continue;
            }
            if metadata.is_dir() {
                if depth < MAX_PROJECT_LIST_DEPTH {
                    directories.push((entry.path(), depth + 1));
                }
                continue;
            }
            if !metadata.is_file() {
                continue;
            }
            let relative = entry
                .path()
                .strip_prefix(&project.root)
                .map_err(|_| "Project file escaped the authorized directory".to_string())?
                .to_path_buf();
            if is_sensitive_project_path(&relative) {
                continue;
            }
            if files.len() >= MAX_PROJECT_LIST_FILES {
                truncated = true;
                break;
            }
            let Some(path) = relative.to_str() else {
                continue;
            };
            if path.chars().count() > 1024 || path.chars().any(char::is_control) {
                continue;
            }
            files.push(json!({
                "path": path.replace('\\', "/"),
                "sizeBytes": metadata.len(),
                "kind": if is_project_text_file(&relative) { "text" } else { "file" },
                "readable": is_project_text_file(&relative),
            }));
        }
        if truncated {
            break;
        }
    }
    files.sort_by(|left, right| {
        left["path"]
            .as_str()
            .unwrap_or_default()
            .cmp(right["path"].as_str().unwrap_or_default())
    });
    Ok(json!({
        "projectId": project.project_id,
        "files": files,
        "truncated": truncated,
        "maxDepth": MAX_PROJECT_LIST_DEPTH,
    }))
}

fn execute_project_file_read(
    project: &AuthorizedProjectDirectory,
    input: &Value,
) -> Result<Value, String> {
    let object = input
        .as_object()
        .ok_or_else(|| "project.file.read input must be an object".to_string())?;
    if object.keys().any(|key| key != "path") {
        return Err("project.file.read accepts only the path field".into());
    }
    let relative = object
        .get("path")
        .and_then(Value::as_str)
        .ok_or_else(|| "project.file.read requires a relative path string".to_string())?;
    if relative.is_empty()
        || relative.chars().count() > 1024
        || relative.chars().any(char::is_control)
        || relative.contains('\\')
    {
        return Err("Project file path must contain 1 to 1024 printable characters".into());
    }
    let relative = Path::new(relative);
    if relative.is_absolute()
        || !relative
            .components()
            .all(|component| matches!(component, std::path::Component::Normal(_)))
        || relative
            .components()
            .any(|component| component.as_os_str().to_string_lossy().starts_with('.'))
    {
        return Err("Project file path must stay within the authorized directory".into());
    }
    if is_sensitive_project_path(relative) {
        return Err("Sensitive credential files cannot be read by this Tool Contract".into());
    }
    if !is_project_text_file(relative) {
        return Err("This Tool Contract reads only allowlisted UTF-8 text formats".into());
    }

    let mut candidate = project.root.clone();
    for component in relative.components() {
        candidate.push(component.as_os_str());
        let metadata = candidate
            .symlink_metadata()
            .map_err(|_| "The requested project file does not exist".to_string())?;
        if metadata.file_type().is_symlink() {
            return Err("Symbolic links are not readable through the project Tool Contract".into());
        }
    }
    let canonical = candidate
        .canonicalize()
        .map_err(|_| "The requested project file is unavailable".to_string())?;
    if !canonical.starts_with(&project.root) || !canonical.is_file() {
        return Err("Project file resolved outside the authorized directory".into());
    }
    let size_bytes = fs::metadata(&canonical)
        .map_err(|error| format!("Unable to inspect project file: {error}"))?
        .len();
    if size_bytes > MAX_PROJECT_FILE_READ_BYTES as u64 {
        return Err("Project file exceeds the 10 MiB safe preview limit".into());
    }
    let bytes =
        fs::read(&canonical).map_err(|error| format!("Unable to read project file: {error}"))?;
    if bytes.len() as u64 != size_bytes {
        return Err("Project file changed while its preview was being read".into());
    }
    let complete_content = std::str::from_utf8(&bytes)
        .map_err(|_| "Project file is not valid UTF-8 text".to_string())?;
    let truncated = bytes.len() > MAX_PROJECT_FILE_PREVIEW_BYTES;
    let mut preview_end = bytes.len().min(MAX_PROJECT_FILE_PREVIEW_BYTES);
    while !complete_content.is_char_boundary(preview_end) {
        preview_end -= 1;
    }
    let content = &complete_content[..preview_end];
    let sha256 = format!("{:x}", Sha256::digest(&bytes));
    Ok(json!({
        "projectId": project.project_id,
        "path": relative.to_string_lossy().replace('\\', "/"),
        "content": content,
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "truncated": truncated,
    }))
}

struct ProjectWriteInput<'a> {
    relative: &'a Path,
    content: &'a str,
    expected_sha256: Option<&'a str>,
}

fn project_write_input(input: &Value) -> Result<ProjectWriteInput<'_>, String> {
    let object = input
        .as_object()
        .ok_or_else(|| "project.file.write input must be an object".to_string())?;
    if object
        .keys()
        .any(|key| !matches!(key.as_str(), "path" | "content" | "expectedSha256"))
    {
        return Err("project.file.write accepts only path, content, and expectedSha256".into());
    }
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .ok_or_else(|| "project.file.write requires a relative path string".to_string())?;
    let relative = Path::new(path);
    if path.is_empty()
        || path.chars().count() > 1024
        || path.chars().any(char::is_control)
        || path.contains('\\')
        || relative.is_absolute()
        || !relative
            .components()
            .all(|component| matches!(component, std::path::Component::Normal(_)))
        || relative
            .components()
            .any(|component| component.as_os_str().to_string_lossy().starts_with('.'))
    {
        return Err(
            "Project file path must stay within the authorized non-hidden directory".into(),
        );
    }
    if is_sensitive_project_path(relative) || !is_project_text_file(relative) {
        return Err("Only allowlisted, non-sensitive project text files can be written".into());
    }
    let content = object
        .get("content")
        .and_then(Value::as_str)
        .ok_or_else(|| "project.file.write requires UTF-8 text content".to_string())?;
    if content.len() > MAX_PROJECT_FILE_WRITE_BYTES || content.contains('\0') {
        return Err("Project file content exceeds 256 KiB or contains a NUL byte".into());
    }
    let expected_sha256 = match object.get("expectedSha256") {
        None => None,
        Some(Value::String(digest)) => Some(digest.as_str()),
        Some(_) => return Err("expectedSha256 must be a hexadecimal string".into()),
    };
    if expected_sha256.is_some_and(|digest| {
        digest.len() != 64
            || !digest
                .chars()
                .all(|character| character.is_ascii_hexdigit())
    }) {
        return Err("expectedSha256 must be a 64-character hexadecimal digest".into());
    }
    Ok(ProjectWriteInput {
        relative,
        content,
        expected_sha256,
    })
}

fn prepare_project_write_destination(
    project: &AuthorizedProjectDirectory,
    relative: &Path,
) -> Result<PathBuf, String> {
    let parent = relative
        .parent()
        .ok_or_else(|| "Project write path does not have a parent".to_string())?;
    let mut directory = project.root.clone();
    for component in parent.components() {
        directory.push(component.as_os_str());
        match directory.symlink_metadata() {
            Ok(metadata) => {
                if metadata.file_type().is_symlink() || !metadata.is_dir() {
                    return Err(
                        "Project write parent contains a symbolic link or non-directory".into(),
                    );
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                fs::create_dir(&directory)
                    .map_err(|error| format!("Unable to create project subdirectory: {error}"))?;
            }
            Err(error) => return Err(format!("Unable to inspect project subdirectory: {error}")),
        }
    }
    let canonical_parent = directory
        .canonicalize()
        .map_err(|error| format!("Unable to resolve project-write parent: {error}"))?;
    if !canonical_parent.starts_with(&project.root) {
        return Err("Project write parent escaped the authorized directory".into());
    }
    Ok(canonical_parent.join(
        relative
            .file_name()
            .ok_or_else(|| "Project write file name is missing".to_string())?,
    ))
}

fn should_skip_project_entry(name: &str) -> bool {
    if name.starts_with('.') {
        return true;
    }
    matches!(
        name.to_ascii_lowercase().as_str(),
        "node_modules" | "target" | "__pycache__" | "venv" | "python-packages"
    )
}

fn is_sensitive_project_path(path: &Path) -> bool {
    let name = path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    let extension = path
        .extension()
        .and_then(|extension| extension.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    matches!(
        name.as_str(),
        ".env"
            | ".npmrc"
            | ".pypirc"
            | "credentials"
            | "credentials.json"
            | "id_rsa"
            | "id_ed25519"
            | "netrc"
            | "dockerconfigjson"
    ) || matches!(extension.as_str(), "pem" | "key" | "p12" | "pfx" | "kdbx")
}

fn is_project_text_file(path: &Path) -> bool {
    let name = path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if matches!(name.as_str(), "readme" | "license" | "authors" | "notice") {
        return true;
    }
    matches!(
        path.extension()
            .and_then(|extension| extension.to_str())
            .map(str::to_ascii_lowercase)
            .as_deref(),
        Some(
            "txt"
                | "md"
                | "markdown"
                | "csv"
                | "tsv"
                | "json"
                | "jsonl"
                | "yaml"
                | "yml"
                | "toml"
                | "xml"
                | "html"
                | "css"
                | "js"
                | "ts"
                | "py"
                | "r"
                | "sql"
                | "log"
                | "fasta"
                | "fa"
                | "fastq"
                | "fq"
                | "bib"
                | "tex"
        )
    )
}

fn execute_tool(
    name: &str,
    input: &Value,
    project: Option<&AuthorizedProjectDirectory>,
) -> Result<Value, String> {
    match name {
        "text.statistics" => execute_text_statistics(input),
        "project.files.list" => execute_project_files_list(
            project.ok_or_else(|| "Project directory authorization is required".to_string())?,
            input,
        ),
        "project.file.read" => execute_project_file_read(
            project.ok_or_else(|| "Project directory authorization is required".to_string())?,
            input,
        ),
        _ => Err(format!("Tool {name} is not installed")),
    }
}

fn validate_proposed_input(name: &str, input: &Value) -> Result<(), String> {
    match name {
        "python.run" | "python.container" => {
            let object = input
                .as_object()
                .ok_or_else(|| format!("{name} input must be an object"))?;
            if object.keys().any(|key| key != "code") {
                return Err(format!("{name} accepts only the code field"));
            }
            let code = object
                .get("code")
                .and_then(Value::as_str)
                .ok_or_else(|| format!("{name} requires a code string"))?;
            if code.is_empty()
                || code.chars().count() > 50_000
                || code.len() > MAX_PYTHON_INPUT_BYTES
                || code.contains('\0')
            {
                return Err(
                    format!("{name} code must contain 1 to 50000 characters, fit within 64 KiB, and contain no NUL bytes"),
                );
            }
            Ok(())
        }
        "project.file.write" => project_write_input(input).map(|_| ()),
        _ => Err(format!("Tool {name} does not support approval proposals")),
    }
}

#[tauri::command]
pub fn desktop_list_tool_contracts() -> Vec<ToolContract> {
    contracts()
}

#[tauri::command]
pub async fn desktop_container_capability() -> Result<ContainerCapability, String> {
    tauri::async_runtime::spawn_blocking(inspect_container_capability)
        .await
        .map_err(|error| format!("Container capability task failed: {error}"))
}

#[tauri::command]
pub async fn desktop_prepare_container_image(
    app: AppHandle,
) -> Result<ContainerCapability, String> {
    let confirmed = app
        .dialog()
        .message(format!(
            "OpenRosalind 将通过 Docker Desktop 下载固定摘要的官方 Python 镜像。\n\n{CONTAINER_IMAGE}\n\n镜像下载需要网络；工具容器运行时仍保持断网。"
        ))
        .title("准备 Docker 沙箱")
        .buttons(MessageDialogButtons::OkCancelCustom(
            "下载镜像".into(),
            "取消".into(),
        ))
        .blocking_show();
    if !confirmed {
        return Ok(inspect_container_capability());
    }
    tauri::async_runtime::spawn_blocking(prepare_container_image)
        .await
        .map_err(|error| format!("Container image task failed: {error}"))?
}

#[tauri::command]
pub fn desktop_run_low_risk_tool(
    store: State<'_, DesktopStore>,
    agent_job_id: String,
    tool_name: String,
    input: Value,
) -> Result<ToolRun, String> {
    run_low_risk_tool(&store, agent_job_id.trim(), tool_name.trim(), input)
}

pub(crate) fn run_low_risk_tool(
    store: &DesktopStore,
    agent_job_id: &str,
    tool_name: &str,
    input: Value,
) -> Result<ToolRun, String> {
    let tool_name = tool_name.trim();
    let contract =
        contract(tool_name).ok_or_else(|| format!("Tool {tool_name} is not installed"))?;
    if contract.permissions.risk != "low" || contract.permissions.approval != "automatic" {
        return Err("This Tool Contract requires an explicit approval flow".into());
    }
    let project_directory = match contract.name {
        "project.files.list" | "project.file.read" => {
            Some(store.authorized_project_directory_for_agent_job(agent_job_id)?)
        }
        _ => None,
    };
    let mut permission_snapshot = serde_json::to_value(&contract.permissions)
        .map_err(|error| format!("Unable to encode Tool permission snapshot: {error}"))?;
    if let Some(project) = &project_directory {
        permission_snapshot
            .as_object_mut()
            .ok_or_else(|| "Tool permission snapshot must be an object".to_string())?
            .insert(
                "projectAuthorization".into(),
                json!({
                    "projectId": project.project_id,
                    "authorizationUpdatedAt": project.authorization_updated_at,
                    "authorizationMode": if project.write { "read-write" } else { "read" },
                    "effectiveAccess": "read",
                }),
            );
    }
    let tool_run = store.create_tool_run(
        agent_job_id,
        contract.name,
        contract.executor.kind,
        input.clone(),
        permission_snapshot,
        "running",
    )?;
    let result = execute_tool(contract.name, &input, project_directory.as_ref());
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
    propose_tool_run(&store, agent_job_id.trim(), tool_name.trim(), input, None)
}

pub(crate) fn propose_tool_run(
    store: &DesktopStore,
    agent_job_id: &str,
    tool_name: &str,
    input: Value,
    worker_request_id: Option<&str>,
) -> Result<ToolRun, String> {
    let tool_name = tool_name.trim();
    let contract =
        contract(tool_name).ok_or_else(|| format!("Tool {tool_name} is not installed"))?;
    if contract.permissions.approval == "automatic" {
        return Err("Automatic tools must use desktop_run_low_risk_tool".into());
    }
    validate_proposed_input(contract.name, &input)?;
    let mut permission_snapshot = serde_json::to_value(&contract.permissions)
        .map_err(|error| format!("Unable to encode Tool permission snapshot: {error}"))?;
    if contract.name == "project.file.write" {
        let project = store.authorized_project_directory_for_agent_job(agent_job_id.trim())?;
        if !project.write {
            return Err("The project directory requires read-write authorization".into());
        }
        let write = project_write_input(&input)?;
        if let Some(expected_digest) = write.expected_sha256 {
            let path = write.relative.to_string_lossy().replace('\\', "/");
            let reviewed = store.list_tool_runs(agent_job_id)?.into_iter().any(|run| {
                let output = run.output.as_ref();
                run.tool_name == "project.file.read"
                    && run.status == "succeeded"
                    && run.input().get("path").and_then(Value::as_str) == Some(path.as_str())
                    && output
                        .and_then(|value| value.get("path"))
                        .and_then(Value::as_str)
                        == Some(path.as_str())
                    && output
                        .and_then(|value| value.get("sha256"))
                        .and_then(Value::as_str)
                        .is_some_and(|digest| digest.eq_ignore_ascii_case(expected_digest))
                    && output
                        .and_then(|value| value.get("truncated"))
                        .and_then(Value::as_bool)
                        == Some(false)
                    && run
                        .permission_snapshot()
                        .get("projectAuthorization")
                        .and_then(|value| value.get("projectId"))
                        .and_then(Value::as_str)
                        == Some(project.project_id.as_str())
                    && run
                        .permission_snapshot()
                        .get("projectAuthorization")
                        .and_then(|value| value.get("authorizationUpdatedAt"))
                        .and_then(Value::as_i64)
                        == Some(project.authorization_updated_at)
            });
            if !reviewed {
                return Err(
                    "Overwriting a project file requires a successful, complete project.file.read in the same AgentJob and authorization version"
                        .into(),
                );
            }
        }
        permission_snapshot
            .as_object_mut()
            .ok_or_else(|| "Tool permission snapshot must be an object".to_string())?
            .insert(
                "projectAuthorization".into(),
                json!({
                    "projectId": project.project_id,
                    "authorizationUpdatedAt": project.authorization_updated_at,
                    "authorizationMode": "read-write",
                    "effectiveAccess": "write",
                }),
            );
    }
    if let Some(request_id) = worker_request_id {
        permission_snapshot
            .as_object_mut()
            .ok_or_else(|| "Tool permission snapshot must be an object".to_string())?
            .insert(
                "workerRequestId".into(),
                Value::String(request_id.to_string()),
            );
    }
    store.create_tool_run(
        agent_job_id,
        contract.name,
        contract.executor.kind,
        input,
        permission_snapshot,
        "awaiting_approval",
    )
}

#[tauri::command]
pub async fn desktop_execute_approved_project_write(
    app: AppHandle,
    tool_run_id: String,
) -> Result<ToolRun, String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let tool_run_id = tool_run_id.trim().to_string();
    tauri::async_runtime::spawn_blocking(move || {
        execute_approved_project_write(&manager, &store, &tool_run_id)
    })
    .await
    .map_err(|error| format!("Project write executor task failed: {error}"))?
}

fn execute_approved_project_write(
    manager: &ToolManager,
    store: &DesktopStore,
    tool_run_id: &str,
) -> Result<ToolRun, String> {
    let tool_run = store.get_tool_run(tool_run_id)?;
    if tool_run.tool_name != "project.file.write" || tool_run.status != "approved" {
        return Err("Only an approved project.file.write ToolRun can enter this executor".into());
    }
    store.start_approved_tool_run(tool_run_id)?;
    let execution = (|| {
        let project = store.authorized_project_directory_for_agent_job(&tool_run.agent_job_id)?;
        let authorization = tool_run
            .permission_snapshot()
            .get("projectAuthorization")
            .ok_or_else(|| "Project write permission snapshot is missing".to_string())?;
        if authorization.get("projectId").and_then(Value::as_str) != Some(&project.project_id)
            || authorization
                .get("authorizationUpdatedAt")
                .and_then(Value::as_i64)
                != Some(project.authorization_updated_at)
            || authorization.get("effectiveAccess").and_then(Value::as_str) != Some("write")
            || !project.write
        {
            return Err("Project authorization changed after approval; write was blocked".into());
        }
        manager.execute_project_file_write(tool_run_id, &project, tool_run.input())
    })();
    finish_tool_execution(store, tool_run_id, execution)
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
    let finished = finish_tool_execution(store, tool_run_id, execution);
    drop(active_run);
    finished
}

#[tauri::command]
pub async fn desktop_execute_approved_container_tool(
    app: AppHandle,
    tool_run_id: String,
) -> Result<ToolRun, String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let tool_run_id = tool_run_id.trim().to_string();
    tauri::async_runtime::spawn_blocking(move || {
        execute_approved_container_tool(&manager, &store, &tool_run_id)
    })
    .await
    .map_err(|error| format!("Container executor task failed: {error}"))?
}

fn execute_approved_container_tool(
    manager: &ToolManager,
    store: &DesktopStore,
    tool_run_id: &str,
) -> Result<ToolRun, String> {
    let tool_run = store.get_tool_run(tool_run_id)?;
    if tool_run.tool_name != "python.container" || tool_run.status != "approved" {
        return Err(
            "Only an approved python.container ToolRun can enter the Container Executor".into(),
        );
    }
    let code = tool_run
        .input()
        .get("code")
        .and_then(Value::as_str)
        .ok_or_else(|| "Approved python.container input is missing its code field".to_string())?
        .to_string();
    let active_run = manager.register(tool_run_id)?;
    store.start_approved_tool_run(tool_run_id)?;
    let execution = manager.execute_registered_container_python(
        tool_run_id,
        &code,
        &ExecutionLimits::default(),
        &active_run,
    );
    let finished = finish_tool_execution(store, tool_run_id, execution);
    drop(active_run);
    finished
}

fn finish_tool_execution(
    store: &DesktopStore,
    tool_run_id: &str,
    execution: Result<ToolExecution, String>,
) -> Result<ToolRun, String> {
    match execution {
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
    }
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

#[tauri::command]
pub async fn desktop_export_tool_artifact(
    app: AppHandle,
    artifact_id: String,
) -> Result<Option<ArtifactExport>, String> {
    let manager = app.state::<ToolManager>().inner().clone();
    let store = app.state::<DesktopStore>().inner().clone();
    let artifact_id = artifact_id.trim().to_string();
    let artifact = store.get_artifact(&artifact_id)?;
    manager.verified_artifact_path(&artifact)?;
    let file_name = Path::new(&artifact.path)
        .file_name()
        .and_then(|name| name.to_str())
        .filter(|name| !name.is_empty())
        .unwrap_or("artifact")
        .to_string();

    let Some(destination) = app
        .dialog()
        .file()
        .set_title("导出 OpenRosalind 产物")
        .set_file_name(&file_name)
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let destination = destination
        .into_path()
        .map_err(|_| "Artifact export requires a local filesystem path".to_string())?;

    tauri::async_runtime::spawn_blocking(move || {
        let artifact = store.get_artifact(&artifact_id)?;
        export_artifact_to(&manager, &artifact, &destination).map(Some)
    })
    .await
    .map_err(|error| format!("Artifact export task failed: {error}"))?
}

fn export_artifact_to(
    manager: &ToolManager,
    artifact: &Artifact,
    destination: &Path,
) -> Result<ArtifactExport, String> {
    let source = manager.verified_artifact_path(artifact)?;
    if destination == source {
        return Err("Artifact is already stored at the selected location".into());
    }
    if destination.is_dir() {
        return Err("Artifact export destination must be a file".into());
    }
    let copied = fs::copy(&source, destination)
        .map_err(|error| format!("Unable to export Artifact: {error}"))?;
    if copied != artifact.size_bytes.max(0) as u64 || sha256_file(destination)? != artifact.sha256 {
        return Err("Exported Artifact did not pass its integrity check".into());
    }
    let file_name = destination
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("artifact")
        .to_string();
    Ok(ArtifactExport {
        file_name,
        size_bytes: copied,
    })
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
    fn automatic_agent_tools_exclude_python_and_container_executors() {
        let automatic = contracts()
            .into_iter()
            .filter(|contract| contract.permissions.approval == "automatic")
            .map(|contract| contract.name)
            .collect::<Vec<_>>();

        assert_eq!(
            automatic,
            vec!["text.statistics", "project.files.list", "project.file.read"]
        );
        assert!(!automatic.contains(&"python.run"));
        assert!(!automatic.contains(&"python.container"));
        assert!(!automatic.contains(&"project.file.write"));
    }

    #[test]
    fn project_write_contract_requires_per_run_project_only_approval() {
        let encoded = serde_json::to_value(project_file_write_contract()).unwrap();
        assert_eq!(encoded["permissions"]["risk"], "medium");
        assert_eq!(encoded["permissions"]["approval"], "per-run");
        assert_eq!(encoded["permissions"]["network"], "none");
        assert_eq!(
            encoded["permissions"]["filesystem"][0]["scope"],
            "project-root"
        );
        assert_eq!(encoded["permissions"]["filesystem"][0]["mode"], "write");
    }

    #[test]
    fn project_write_is_atomic_and_preserves_rollback_artifact() {
        let (manager, runs_root) = test_tool_manager();
        let project_root = env::temp_dir().join(format!(
            "open-rosalind-project-write-test-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&project_root).unwrap();
        let project = AuthorizedProjectDirectory {
            project_id: "project-write".into(),
            root: project_root.canonicalize().unwrap(),
            write: true,
            authorization_updated_at: 10,
        };
        let target = project.root.join("notes/result.md");
        let created = manager
            .execute_project_file_write(
                "write-new",
                &project,
                &json!({"path":"notes/result.md","content":"first"}),
            )
            .unwrap();
        assert_eq!(fs::read_to_string(&target).unwrap(), "first");
        assert_eq!(created.output["created"], true);

        let digest = sha256_file(&target).unwrap();
        let replaced = manager
            .execute_project_file_write(
                "write-replace",
                &project,
                &json!({"path":"notes/result.md","content":"second","expectedSha256":digest}),
            )
            .unwrap();
        assert_eq!(fs::read_to_string(&target).unwrap(), "second");
        assert_eq!(replaced.output["rollbackArtifact"], true);
        assert_eq!(
            fs::read_to_string(runs_root.join("write-replace/output/previous/notes/result.md"))
                .unwrap(),
            "first"
        );
        assert_eq!(replaced.artifacts.len(), 2);

        fs::remove_dir_all(project_root).unwrap();
        fs::remove_dir_all(runs_root).unwrap();
    }

    #[test]
    fn project_write_rejects_stale_sensitive_and_read_only_changes() {
        let (manager, runs_root) = test_tool_manager();
        let project_root = env::temp_dir().join(format!(
            "open-rosalind-project-write-reject-test-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&project_root).unwrap();
        fs::write(project_root.join("result.txt"), "current").unwrap();
        let mut project = AuthorizedProjectDirectory {
            project_id: "project-write".into(),
            root: project_root.canonicalize().unwrap(),
            write: true,
            authorization_updated_at: 10,
        };
        assert!(manager
            .execute_project_file_write(
                "stale",
                &project,
                &json!({"path":"result.txt","content":"changed","expectedSha256":"0".repeat(64)}),
            )
            .unwrap_err()
            .contains("changed after it was reviewed"));
        assert!(manager
            .execute_project_file_write(
                "missing-digest",
                &project,
                &json!({"path":"result.txt","content":"changed"}),
            )
            .unwrap_err()
            .contains("requires its expectedSha256"));
        assert!(project_write_input(&json!({"path":".env","content":"secret"})).is_err());
        assert!(project_write_input(
            &json!({"path":"new.txt","content":"blocked","expectedSha256":null})
        )
        .is_err());
        project.write = false;
        assert!(manager
            .execute_project_file_write(
                "read-only",
                &project,
                &json!({"path":"new.txt","content":"blocked"}),
            )
            .unwrap_err()
            .contains("not authorized for writes"));

        fs::remove_dir_all(project_root).unwrap();
        fs::remove_dir_all(runs_root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn project_write_rejects_symbolic_link_parents() {
        use std::os::unix::fs::symlink;

        let (manager, runs_root) = test_tool_manager();
        let project_root = env::temp_dir().join(format!(
            "open-rosalind-project-write-symlink-test-{}",
            uuid::Uuid::new_v4()
        ));
        let outside = env::temp_dir().join(format!(
            "open-rosalind-project-write-outside-test-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(&project_root).unwrap();
        fs::create_dir_all(&outside).unwrap();
        symlink(&outside, project_root.join("linked")).unwrap();
        let project = AuthorizedProjectDirectory {
            project_id: "project-write".into(),
            root: project_root.canonicalize().unwrap(),
            write: true,
            authorization_updated_at: 10,
        };

        assert!(manager
            .execute_project_file_write(
                "symlink-parent",
                &project,
                &json!({"path":"linked/result.txt","content":"blocked"}),
            )
            .unwrap_err()
            .contains("symbolic link"));
        assert!(!outside.join("result.txt").exists());

        fs::remove_dir_all(project_root).unwrap();
        fs::remove_dir_all(outside).unwrap();
        fs::remove_dir_all(runs_root).unwrap();
    }

    #[test]
    fn project_read_tools_stay_inside_authorized_non_sensitive_text() {
        let root = env::temp_dir().join(format!(
            "open-rosalind-project-read-test-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir_all(root.join("data")).unwrap();
        fs::write(root.join("README.md"), "# Study\nTP53 cohort").unwrap();
        fs::write(root.join("data/variants.csv"), "gene,variant\nTP53,R175H\n").unwrap();
        fs::write(root.join("data/archive.zip"), [0_u8, 1, 2, 3]).unwrap();
        let mut late_binary = vec![b'a'; MAX_PROJECT_FILE_PREVIEW_BYTES + 1];
        late_binary.push(0xff);
        fs::write(root.join("data/late-binary.txt"), late_binary).unwrap();
        fs::write(root.join(".env"), "API_KEY=must-not-be-read").unwrap();
        fs::write(root.join("private.pem"), "must-not-be-read").unwrap();
        let project = AuthorizedProjectDirectory {
            project_id: "project-1".into(),
            root: root.canonicalize().unwrap(),
            write: true,
            authorization_updated_at: 1,
        };

        let listed = execute_project_files_list(&project, &json!({})).unwrap();
        let paths = listed["files"]
            .as_array()
            .unwrap()
            .iter()
            .map(|file| file["path"].as_str().unwrap())
            .collect::<Vec<_>>();
        assert_eq!(
            paths,
            vec![
                "README.md",
                "data/archive.zip",
                "data/late-binary.txt",
                "data/variants.csv"
            ]
        );
        assert_eq!(listed["files"][0]["readable"], true);
        assert_eq!(listed["files"][1]["readable"], false);

        let read =
            execute_project_file_read(&project, &json!({"path": "data/variants.csv"})).unwrap();
        assert_eq!(read["content"], "gene,variant\nTP53,R175H\n");
        assert!(execute_project_file_read(&project, &json!({"path": "../outside.txt"})).is_err());
        assert!(execute_project_file_read(&project, &json!({"path": ".env"})).is_err());
        assert!(execute_project_file_read(&project, &json!({"path": "private.pem"})).is_err());
        assert!(execute_project_file_read(&project, &json!({"path": "data/archive.zip"})).is_err());
        assert!(
            execute_project_file_read(&project, &json!({"path": "data/late-binary.txt"})).is_err()
        );

        fs::remove_dir_all(root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn project_read_tool_rejects_symbolic_links() {
        use std::os::unix::fs::symlink;

        let root = env::temp_dir().join(format!(
            "open-rosalind-project-link-test-{}",
            uuid::Uuid::new_v4()
        ));
        let outside = env::temp_dir().join(format!(
            "open-rosalind-project-outside-{}",
            uuid::Uuid::new_v4()
        ));
        fs::create_dir(&root).unwrap();
        fs::write(&outside, "outside").unwrap();
        symlink(&outside, root.join("linked.txt")).unwrap();
        let project = AuthorizedProjectDirectory {
            project_id: "project-1".into(),
            root: root.canonicalize().unwrap(),
            write: false,
            authorization_updated_at: 1,
        };

        assert!(execute_project_file_read(&project, &json!({"path": "linked.txt"})).is_err());
        let listed = execute_project_files_list(&project, &json!({})).unwrap();
        assert!(listed["files"].as_array().unwrap().is_empty());

        fs::remove_dir_all(root).unwrap();
        fs::remove_file(outside).unwrap();
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
    fn container_contract_pins_the_image_and_freezes_resource_limits() {
        let encoded = serde_json::to_value(python_container_contract()).unwrap();

        assert_eq!(encoded["executor"]["kind"], "container");
        assert_eq!(encoded["executor"]["image"], CONTAINER_IMAGE);
        assert!(CONTAINER_IMAGE.contains("@sha256:"));
        assert_eq!(encoded["permissions"]["risk"], "high");
        assert_eq!(encoded["permissions"]["approval"], "per-run");
        assert_eq!(encoded["permissions"]["network"], "none");
        assert_eq!(encoded["resources"]["memoryMb"], CONTAINER_MEMORY_MB);
        assert_eq!(encoded["resources"]["cpu"], CONTAINER_CPUS);
        assert_eq!(encoded["resources"]["pids"], CONTAINER_PIDS);
    }

    #[test]
    fn container_command_applies_fail_closed_sandbox_flags() {
        let root = env::temp_dir().join(format!(
            "open-rosalind-container-args-{}",
            uuid::Uuid::new_v4()
        ));
        let input = root.join("input");
        let output = root.join("output");
        fs::create_dir_all(&input).unwrap();
        fs::create_dir_all(&output).unwrap();
        let tool_run_id = "12345678-1234-4123-8123-123456789abc";
        let name = container_name(tool_run_id).unwrap();
        let arguments = container_run_arguments(tool_run_id, &name, &input, &output).unwrap();
        let arguments = arguments
            .iter()
            .map(|value| value.to_string_lossy().into_owned())
            .collect::<Vec<_>>();

        for required in [
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges=true",
            "--pids-limit=64",
            "--memory=512m",
            "--cpus=1",
            "--ipc=none",
            CONTAINER_IMAGE,
        ] {
            assert!(arguments.iter().any(|argument| argument == required));
        }
        assert!(!arguments.iter().any(|argument| argument == "--privileged"));
        assert!(arguments
            .iter()
            .any(|argument| argument.contains("target=/workspace/input,readonly")));
        assert!(arguments
            .iter()
            .any(|argument| argument.contains("target=/workspace/output")));
        assert!(container_name("../../docker-socket").is_err());
        fs::remove_dir_all(root).unwrap();
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
        assert!(validate_proposed_input(
            "python.container",
            &json!({"code": "print(1)", "image": "attacker/image:latest"})
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
        let export_path = root.join("exported-result.txt");
        let exported = export_artifact_to(&manager, &artifact, &export_path).unwrap();
        assert_eq!(exported.file_name, "exported-result.txt");
        assert_eq!(exported.size_bytes, 4);
        assert_eq!(fs::read_to_string(&export_path).unwrap(), "done");
        fs::write(root.join("successful-run/output/result.txt"), "changed").unwrap();
        assert!(manager.verified_artifact_path(&artifact).is_err());
        assert!(export_artifact_to(&manager, &artifact, &root.join("blocked.txt")).is_err());
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
