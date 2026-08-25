use std::{
    env,
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

const DEFAULT_PORT: u16 = 18_765;

struct BackendProcess(Mutex<Option<Child>>);

impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Ok(child) = self.0.get_mut() {
            if let Some(child) = child.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            child.take();
        }
    }
}

fn repository_root(app: &tauri::App) -> Result<PathBuf, String> {
    if let Ok(value) = env::var("OPENROSALIND_REPO_ROOT") {
        let path = PathBuf::from(value);
        if path.join("web_app/server.py").is_file() {
            return Ok(path);
        }
        return Err("OPENROSALIND_REPO_ROOT does not contain web_app/server.py".into());
    }

    let development_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or("Unable to locate the development repository root")?;
    if development_root.join("web_app/server.py").is_file() {
        return Ok(development_root);
    }

    let bundled_root = app
        .path()
        .resource_dir()
        .map_err(|error| format!("Unable to locate application resources: {error}"))?
        .join("runtime");
    if bundled_root.join("web_app/server.py").is_file() {
        return Ok(bundled_root);
    }
    Err("OpenRosalind Python runtime was not found".into())
}

fn python_executable(root: &Path) -> PathBuf {
    if let Ok(value) = env::var("OPENROSALIND_PYTHON") {
        return PathBuf::from(value);
    }
    let unix_venv = root.join(".venv/bin/python");
    if unix_venv.is_file() {
        return unix_venv;
    }
    let windows_venv = root.join(".venv/Scripts/python.exe");
    if windows_venv.is_file() {
        return windows_venv;
    }
    #[cfg(target_os = "macos")]
    {
        let mut candidates = Vec::new();
        if let Ok(home) = env::var("HOME") {
            let home = PathBuf::from(home);
            candidates.push(home.join(".local/bin/python3.11"));
            candidates.push(home.join(".local/bin/python3"));
        }
        candidates.extend([
            PathBuf::from("/opt/homebrew/bin/python3"),
            PathBuf::from("/usr/local/bin/python3"),
            PathBuf::from("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"),
        ]);
        if let Some(candidate) = candidates.into_iter().find(|path| path.is_file()) {
            return candidate;
        }
    }
    PathBuf::from(if cfg!(windows) { "python" } else { "python3" })
}

fn validate_python(python: &Path) -> Result<(), String> {
    let output = Command::new(python)
        .arg("-c")
        .arg("import platform, sys; print(f'{sys.version_info.major}.{sys.version_info.minor}\\t{platform.machine()}')")
        .stdin(Stdio::null())
        .output()
        .map_err(|error| format!("Unable to inspect {}: {error}", python.display()))?;
    if !output.status.success() {
        return Err(format!(
            "Unable to run {}. OpenRosalind Desktop requires Python 3.10 or newer.",
            python.display()
        ));
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut fields = stdout.trim().split('\t');
    let version = fields.next().unwrap_or_default();
    let machine = fields.next().unwrap_or_default();
    let mut version_parts = version
        .split('.')
        .filter_map(|part| part.parse::<u16>().ok());
    let major = version_parts.next().unwrap_or_default();
    let minor = version_parts.next().unwrap_or_default();
    if major < 3 || (major == 3 && minor < 10) {
        return Err(format!(
            "OpenRosalind Desktop requires Python 3.10 or newer; {} is Python {version}.",
            python.display()
        ));
    }
    #[cfg(target_os = "macos")]
    {
        let python_arch = match machine {
            "arm64" | "aarch64" => "aarch64",
            "x86_64" => "x86_64",
            _ => machine,
        };
        let app_arch = if cfg!(target_arch = "aarch64") {
            "aarch64"
        } else {
            "x86_64"
        };
        if matches!(python_arch, "aarch64" | "x86_64") && python_arch != app_arch {
            return Err(format!(
                "Python architecture {machine} does not match the {app_arch} desktop application. Avoid mixing Rosetta and native runtimes."
            ));
        }
    }
    Ok(())
}

fn desktop_port() -> Result<u16, String> {
    match env::var("OPENROSALIND_DESKTOP_PORT") {
        Ok(value) => value
            .parse::<u16>()
            .map_err(|_| "OPENROSALIND_DESKTOP_PORT must be a valid TCP port".into()),
        Err(_) => Ok(DEFAULT_PORT),
    }
}

fn sqlite_url(path: &Path) -> String {
    format!("sqlite:///{}", path.to_string_lossy().replace('\\', "/"))
}

fn wait_for_backend(child: &mut Child, address: SocketAddr) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(25);
    while Instant::now() < deadline {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("Unable to inspect local service: {error}"))?
        {
            return Err(format!("Local service exited before startup ({status})"));
        }
        if TcpStream::connect_timeout(&address, Duration::from_millis(200)).is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(150));
    }
    Err("Timed out while starting the local OpenRosalind service".into())
}

fn start_backend(app: &tauri::App) -> Result<(Child, u16), String> {
    let root = repository_root(app)?;
    let python = python_executable(&root);
    validate_python(&python)?;
    let port = desktop_port()?;
    let data_root = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Unable to locate application data directory: {error}"))?;
    let workspace_root = data_root.join("agent-workspaces");
    let runs_root = data_root.join("agent-runs");
    let jobs_root = data_root.join("jobs");
    for path in [&data_root, &workspace_root, &runs_root, &jobs_root] {
        std::fs::create_dir_all(path)
            .map_err(|error| format!("Unable to create {}: {error}", path.display()))?;
    }
    let development_packages = root.join("desktop/python-packages");
    let bundled_packages = root.join("python-packages");
    let python_packages = if development_packages.is_dir() {
        development_packages
    } else {
        bundled_packages
    };
    let python_path = env::join_paths([root.as_path(), python_packages.as_path()])
        .map_err(|error| format!("Unable to configure the Python module path: {error}"))?;

    let mut child = Command::new(&python)
        .arg("-m")
        .arg("web_app.server")
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg(port.to_string())
        .current_dir(&root)
        .env("PYTHONPATH", python_path)
        .env("ROSALIND_DESKTOP_MODE", "1")
        .env("ROSALIND_COOKIE_SECURE", "0")
        .env(
            "ROSALIND_AGENT_RUNTIME",
            env::var("OPENROSALIND_DESKTOP_AGENT_RUNTIME").unwrap_or_else(|_| "legacy".into()),
        )
        .env("DATABASE_URL", sqlite_url(&data_root.join("rosalind.db")))
        .env("ROSALIND_JOBS_DIR", &jobs_root)
        .env("OPENHANDS_HOST_PROJECTS_ROOT", &workspace_root)
        .env("OPENHANDS_HOST_RUNS_ROOT", &runs_root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("Unable to start {}: {error}", python.display()))?;

    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port);
    if let Err(error) = wait_for_backend(&mut child, address) {
        let _ = child.kill();
        return Err(error);
    }
    Ok((child, port))
}

fn stop_backend(app_handle: &tauri::AppHandle) {
    if let Some(backend) = app_handle.try_state::<BackendProcess>() {
        if let Ok(mut guard) = backend.0.lock() {
            if let Some(child) = guard.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            guard.take();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let (child, port) = start_backend(app)?;
            app.manage(BackendProcess(Mutex::new(Some(child))));
            let url = format!("http://127.0.0.1:{port}/app")
                .parse()
                .map_err(|error| format!("Invalid local application URL: {error}"))?;
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title("OpenRosalind")
                .inner_size(1320.0, 840.0)
                .min_inner_size(960.0, 640.0)
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building OpenRosalind desktop");

    app.run(|app_handle, event| {
        let main_window_closed = matches!(
            &event,
            tauri::RunEvent::WindowEvent {
                label,
                event: tauri::WindowEvent::Destroyed,
                ..
            } if label == "main"
        );
        if main_window_closed
            || matches!(
                event,
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. }
            )
        {
            stop_backend(app_handle);
        }
        if main_window_closed {
            app_handle.exit(0);
        }
    });
}
