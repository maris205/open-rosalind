use std::{
    collections::HashSet,
    env, fs,
    path::{Component, Path, PathBuf},
    process::{Command, Stdio},
    sync::{Arc, Mutex},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

#[cfg(target_os = "macos")]
use std::collections::HashMap;

use rusqlite::{
    params, Connection, OpenFlags, OptionalExtension, Row, TransactionBehavior, MAIN_DB,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use uuid::Uuid;

use super::agent::WorkerJobStatus;

const SCHEMA_VERSION: i64 = 5;
const MAX_DATABASE_BACKUPS: usize = 5;
const DATABASE_BACKUP_INTERVAL: Duration = Duration::from_secs(6 * 60 * 60);
const MAX_AGENT_JOB_REQUEST_BYTES: usize = 512 * 1024;
const MAX_UI_CHATS: usize = 100;
const MAX_UI_MESSAGES: usize = 10_000;
const MAX_UI_MESSAGE_BYTES: usize = 2 * 1024 * 1024;
const MAX_UI_CHAT_STATE_BYTES: usize = 50 * 1024 * 1024;
const TERMINAL_STATUSES: &[&str] = &["completed", "cancelled", "failed", "interrupted"];
pub(crate) const DEFAULT_PROVIDER_ID: &str = "default-qwen-openai-compatible";
const DEFAULT_PROVIDER_BASE_URL: &str =
    "https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1";
const DEFAULT_PROVIDER_MODEL: &str = "qwen3.7-max";

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Conversation {
    id: String,
    project_id: Option<String>,
    title: String,
    created_at: i64,
    updated_at: i64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UiChatSnapshot {
    id: String,
    function_id: String,
    title: String,
    messages: Vec<Value>,
    created_at: String,
    updated_at: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UiChatState {
    active_chat_id: String,
    chats: Vec<UiChatSnapshot>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentJob {
    pub(crate) id: String,
    conversation_id: String,
    pub(crate) status: String,
    pub(crate) request: Value,
    result: Option<Value>,
    cancellation_requested: bool,
    created_at: i64,
    started_at: Option<i64>,
    ended_at: Option<i64>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentJobEvent {
    id: i64,
    agent_job_id: String,
    sequence: i64,
    kind: String,
    payload: Value,
    created_at: i64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentJobDetail {
    pub(crate) job: AgentJob,
    events: Vec<AgentJobEvent>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderProfile {
    pub(crate) id: String,
    pub(crate) name: String,
    pub(crate) provider_type: String,
    pub(crate) base_url: String,
    pub(crate) model: String,
    pub(crate) credential_ref: String,
    pub(crate) is_default: bool,
    pub(crate) created_at: i64,
    pub(crate) updated_at: i64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectDirectoryAuthorization {
    project_id: String,
    display_name: String,
    display_path: String,
    read: bool,
    write: bool,
    available: bool,
    persistence: String,
    authorized_at: i64,
    updated_at: i64,
}

#[derive(Clone, Debug)]
pub(crate) struct AuthorizedProjectDirectory {
    pub(crate) project_id: String,
    pub(crate) root: PathBuf,
    pub(crate) write: bool,
    pub(crate) authorization_updated_at: i64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolRun {
    pub(crate) id: String,
    pub(crate) agent_job_id: String,
    pub(crate) tool_name: String,
    executor: String,
    pub(crate) status: String,
    input: Value,
    pub(crate) output: Option<Value>,
    permission_snapshot: Value,
    created_at: i64,
    started_at: Option<i64>,
    ended_at: Option<i64>,
}

impl ToolRun {
    pub(crate) fn input(&self) -> &Value {
        &self.input
    }

    pub(crate) fn permission_snapshot(&self) -> &Value {
        &self.permission_snapshot
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Artifact {
    pub(crate) id: String,
    pub(crate) agent_job_id: String,
    pub(crate) tool_run_id: String,
    pub(crate) kind: String,
    pub(crate) path: String,
    pub(crate) sha256: String,
    pub(crate) size_bytes: i64,
    pub(crate) created_at: i64,
}

#[derive(Debug)]
pub(crate) struct NewArtifact {
    pub(crate) id: String,
    pub(crate) kind: String,
    pub(crate) path: String,
    pub(crate) sha256: String,
    pub(crate) size_bytes: i64,
}

#[derive(Clone)]
pub struct DesktopStore {
    connection: Arc<Mutex<Connection>>,
    database_path: Option<PathBuf>,
    backup_directory: Option<PathBuf>,
    backup_baseline_changes: Arc<Mutex<u64>>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopBackupInfo {
    file_name: String,
    created_at: i64,
    size_bytes: u64,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopBackupStatus {
    available: bool,
    backup_directory: Option<String>,
    backups: Vec<DesktopBackupInfo>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRestoreResult {
    restored_backup: String,
    safety_backup: DesktopBackupInfo,
}

impl DesktopStore {
    pub fn open(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|error| {
                format!("Unable to create Desktop Core data directory: {error}")
            })?;
            secure_directory_permissions(parent)?;
        }
        let backup_directory = path
            .parent()
            .map(|parent| parent.join("backups"))
            .ok_or_else(|| {
                "Desktop Core database path does not have a parent directory".to_string()
            })?;
        let database_existed = path
            .metadata()
            .map(|metadata| metadata.len() > 0)
            .unwrap_or(false);
        let connection = Connection::open(path)
            .map_err(|error| format!("Unable to open Desktop Core database: {error}"))?;
        if database_existed {
            verify_database_integrity(&connection, "quick_check").map_err(|error| {
                format!(
                    "Desktop Core database failed its startup integrity check: {error}. The original database was preserved. Verified backups, when available, are in {}",
                    backup_directory.display()
                )
            })?;
        }
        let mut store = Self::from_connection(connection)?;
        store.database_path = Some(path.to_path_buf());
        store.backup_directory = Some(backup_directory);
        secure_file_permissions(path)?;
        {
            let connection = store.lock_connection()?;
            verify_database_integrity(&connection, "integrity_check")?;
        }
        if let Err(error) = store.create_backup_if_due() {
            eprintln!("OpenRosalind startup backup was skipped: {error}");
        }
        Ok(store)
    }

    fn from_connection(mut connection: Connection) -> Result<Self, String> {
        connection
            .execute_batch(
                r#"
                PRAGMA foreign_keys = ON;
                PRAGMA journal_mode = WAL;
                PRAGMA busy_timeout = 5000;
                "#,
            )
            .map_err(|error| format!("Unable to configure Desktop Core database: {error}"))?;
        let current_version = connection
            .pragma_query_value(None, "user_version", |row| row.get::<_, i64>(0))
            .map_err(|error| format!("Unable to inspect Desktop Core schema version: {error}"))?;
        if current_version > SCHEMA_VERSION {
            return Err(format!(
                "Desktop Core database schema {current_version} is newer than supported version {SCHEMA_VERSION}"
            ));
        }
        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(|error| format!("Unable to begin Desktop Core migration: {error}"))?;
        transaction
            .execute_batch(
                r#"
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ui_chat_states (
                    owner_id TEXT PRIMARY KEY,
                    active_chat_id TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ui_chats (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    function_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(owner_id, position)
                );

                CREATE TABLE IF NOT EXISTS ui_chat_messages (
                    chat_id TEXT NOT NULL REFERENCES ui_chats(id) ON DELETE CASCADE,
                    id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    message_json TEXT NOT NULL,
                    PRIMARY KEY(chat_id, id),
                    UNIQUE(chat_id, position)
                );

                CREATE TABLE IF NOT EXISTS agent_jobs (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    cancellation_requested INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    started_at INTEGER,
                    ended_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS agent_job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_job_id TEXT NOT NULL REFERENCES agent_jobs(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(agent_job_id, sequence)
                );

                CREATE TABLE IF NOT EXISTS provider_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider_type TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    model TEXT NOT NULL,
                    credential_ref TEXT NOT NULL UNIQUE,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_directory_authorizations (
                    project_id TEXT PRIMARY KEY,
                    root_path TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    access_mode TEXT NOT NULL CHECK(access_mode IN ('read', 'read-write')),
                    persistence TEXT NOT NULL,
                    authorized_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_runs (
                    id TEXT PRIMARY KEY,
                    agent_job_id TEXT NOT NULL REFERENCES agent_jobs(id) ON DELETE CASCADE,
                    tool_name TEXT NOT NULL,
                    executor TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT,
                    permission_snapshot_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    started_at INTEGER,
                    ended_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    agent_job_id TEXT REFERENCES agent_jobs(id) ON DELETE CASCADE,
                    tool_run_id TEXT REFERENCES tool_runs(id) ON DELETE SET NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    sha256 TEXT,
                    size_bytes INTEGER,
                    created_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS conversations_updated_at
                    ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS ui_chats_owner_position
                    ON ui_chats(owner_id, position);
                CREATE INDEX IF NOT EXISTS ui_chat_messages_chat_position
                    ON ui_chat_messages(chat_id, position);
                CREATE INDEX IF NOT EXISTS agent_jobs_conversation_created
                    ON agent_jobs(conversation_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS agent_job_events_job_sequence
                    ON agent_job_events(agent_job_id, sequence);
                CREATE INDEX IF NOT EXISTS provider_profiles_default_updated
                    ON provider_profiles(is_default DESC, updated_at DESC);
                CREATE INDEX IF NOT EXISTS project_directory_authorizations_updated
                    ON project_directory_authorizations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS tool_runs_job_created
                    ON tool_runs(agent_job_id, created_at);
                CREATE INDEX IF NOT EXISTS artifacts_job_created
                    ON artifacts(agent_job_id, created_at);
                "#,
            )
            .map_err(|error| format!("Unable to migrate Desktop Core database: {error}"))?;

        let provider_created_at = unix_millis();
        transaction
            .execute(
                r#"
                INSERT OR IGNORE INTO provider_profiles
                    (id, name, provider_type, base_url, model, credential_ref, is_default, created_at, updated_at)
                VALUES (?1, '通义千问', 'openai_compatible', ?2, ?3, ?1, 1, ?4, ?4)
                "#,
                params![
                    DEFAULT_PROVIDER_ID,
                    DEFAULT_PROVIDER_BASE_URL,
                    DEFAULT_PROVIDER_MODEL,
                    provider_created_at,
                ],
            )
            .map_err(|error| format!("Unable to create default Provider profile: {error}"))?;

        let recovered_at = unix_millis();
        transaction
            .execute(
                r#"
                INSERT INTO agent_job_events (agent_job_id, sequence, kind, payload_json, created_at)
                SELECT jobs.id,
                       COALESCE((SELECT MAX(events.sequence) FROM agent_job_events events WHERE events.agent_job_id = jobs.id), 0) + 1,
                       'interrupted',
                       '{"reason":"desktop-core-restarted"}',
                       ?1
                  FROM agent_jobs jobs
                 WHERE jobs.status IN ('queued', 'running', 'cancelling')
                "#,
                [recovered_at],
            )
            .map_err(|error| format!("Unable to record interrupted Agent jobs: {error}"))?;
        transaction
            .execute(
                "UPDATE agent_jobs SET status = 'interrupted', ended_at = ?1 WHERE status IN ('queued', 'running', 'cancelling')",
                [recovered_at],
            )
            .map_err(|error| format!("Unable to recover interrupted Agent jobs: {error}"))?;
        transaction
            .pragma_update(None, "user_version", SCHEMA_VERSION)
            .map_err(|error| format!("Unable to record Desktop Core schema version: {error}"))?;
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit Desktop Core migration: {error}"))?;
        let baseline_changes = connection.total_changes();
        Ok(Self {
            connection: Arc::new(Mutex::new(connection)),
            database_path: None,
            backup_directory: None,
            backup_baseline_changes: Arc::new(Mutex::new(baseline_changes)),
        })
    }

    fn create_conversation(
        &self,
        title: String,
        project_id: Option<String>,
    ) -> Result<Conversation, String> {
        let title = title.trim();
        if title.is_empty() || title.chars().count() > 200 {
            return Err("Conversation title must contain 1 to 200 characters".into());
        }
        let now = unix_millis();
        let conversation = Conversation {
            id: Uuid::new_v4().to_string(),
            project_id: project_id.filter(|value| !value.trim().is_empty()),
            title: title.into(),
            created_at: now,
            updated_at: now,
        };
        let connection = self.lock_connection()?;
        connection
            .execute(
                "INSERT INTO conversations (id, project_id, title, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    conversation.id,
                    conversation.project_id,
                    conversation.title,
                    conversation.created_at,
                    conversation.updated_at,
                ],
            )
            .map_err(|error| format!("Unable to create conversation: {error}"))?;
        Ok(conversation)
    }

    fn list_conversations(&self) -> Result<Vec<Conversation>, String> {
        let connection = self.lock_connection()?;
        let mut statement = connection
            .prepare(
                "SELECT id, project_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC, id",
            )
            .map_err(|error| format!("Unable to list conversations: {error}"))?;
        let rows = statement
            .query_map([], |row| {
                Ok(Conversation {
                    id: row.get(0)?,
                    project_id: row.get(1)?,
                    title: row.get(2)?,
                    created_at: row.get(3)?,
                    updated_at: row.get(4)?,
                })
            })
            .map_err(|error| format!("Unable to read conversations: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode conversation: {error}"))
    }

    fn load_ui_chat_state(&self, owner_id: String) -> Result<UiChatState, String> {
        let owner_id = validate_text("Chat owner id", owner_id, 320)?;
        let connection = self.lock_connection()?;
        let active_chat_id = connection
            .query_row(
                "SELECT active_chat_id FROM ui_chat_states WHERE owner_id = ?1",
                [&owner_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(|error| format!("Unable to load desktop chat state: {error}"))?
            .unwrap_or_default();

        let chat_rows = {
            let mut statement = connection
                .prepare(
                    "SELECT id, function_id, title, created_at, updated_at FROM ui_chats WHERE owner_id = ?1 ORDER BY position",
                )
                .map_err(|error| format!("Unable to load desktop chats: {error}"))?;
            let rows = statement
                .query_map([&owner_id], |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                    ))
                })
                .map_err(|error| format!("Unable to read desktop chats: {error}"))?;
            rows.collect::<Result<Vec<_>, _>>()
                .map_err(|error| format!("Unable to decode desktop chats: {error}"))?
        };

        let mut chats = Vec::with_capacity(chat_rows.len());
        let mut message_statement = connection
            .prepare(
                "SELECT message_json FROM ui_chat_messages WHERE chat_id = ?1 ORDER BY position",
            )
            .map_err(|error| format!("Unable to load desktop chat messages: {error}"))?;
        for (id, function_id, title, created_at, updated_at) in chat_rows {
            let rows = message_statement
                .query_map([&id], |row| row.get::<_, String>(0))
                .map_err(|error| format!("Unable to read desktop chat messages: {error}"))?;
            let mut messages = Vec::new();
            for row in rows {
                let encoded =
                    row.map_err(|error| format!("Unable to decode desktop chat message: {error}"))?;
                messages.push(serde_json::from_str(&encoded).map_err(|error| {
                    format!("Desktop chat message contains invalid JSON: {error}")
                })?);
            }
            chats.push(UiChatSnapshot {
                id,
                function_id,
                title,
                messages,
                created_at,
                updated_at,
            });
        }

        Ok(UiChatState {
            active_chat_id,
            chats,
        })
    }

    fn replace_ui_chat_state(
        &self,
        owner_id: String,
        active_chat_id: String,
        chats: Vec<UiChatSnapshot>,
    ) -> Result<UiChatState, String> {
        let owner_id = validate_text("Chat owner id", owner_id, 320)?;
        let (active_chat_id, chats, encoded_messages) =
            validate_ui_chat_state(active_chat_id, chats)?;
        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin desktop chat transaction: {error}"))?;
        transaction
            .execute("DELETE FROM ui_chats WHERE owner_id = ?1", [&owner_id])
            .map_err(|error| format!("Unable to replace desktop chats: {error}"))?;

        let mut encoded_index = 0usize;
        for (chat_position, chat) in chats.iter().enumerate() {
            transaction
                .execute(
                    "INSERT INTO ui_chats (id, owner_id, position, function_id, title, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                    params![
                        chat.id,
                        owner_id,
                        chat_position as i64,
                        chat.function_id,
                        chat.title,
                        chat.created_at,
                        chat.updated_at,
                    ],
                )
                .map_err(|error| format!("Unable to save desktop chat: {error}"))?;
            for (message_position, message) in chat.messages.iter().enumerate() {
                let message_id = message
                    .get("id")
                    .and_then(Value::as_str)
                    .expect("validated chat messages always have ids");
                transaction
                    .execute(
                        "INSERT INTO ui_chat_messages (chat_id, id, position, message_json) VALUES (?1, ?2, ?3, ?4)",
                        params![
                            chat.id,
                            message_id,
                            message_position as i64,
                            encoded_messages[encoded_index],
                        ],
                    )
                    .map_err(|error| format!("Unable to save desktop chat message: {error}"))?;
                encoded_index += 1;
            }
        }
        transaction
            .execute(
                r#"
                INSERT INTO ui_chat_states (owner_id, active_chat_id, updated_at)
                VALUES (?1, ?2, ?3)
                ON CONFLICT(owner_id) DO UPDATE SET
                    active_chat_id = excluded.active_chat_id,
                    updated_at = excluded.updated_at
                "#,
                params![owner_id, active_chat_id, unix_millis()],
            )
            .map_err(|error| format!("Unable to save desktop chat state: {error}"))?;
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit desktop chat state: {error}"))?;

        Ok(UiChatState {
            active_chat_id,
            chats,
        })
    }

    #[cfg(target_os = "macos")]
    pub(crate) fn import_legacy_macos_webkit_chats(&self) -> Result<usize, String> {
        let home_directory = env::var_os("HOME")
            .map(PathBuf::from)
            .ok_or_else(|| "Unable to locate the macOS home directory".to_string())?;
        let webkit_root =
            home_directory.join("Library/WebKit/bio.openrosalind.desktop/WebsiteData/Default");
        if !webkit_root.is_dir() {
            return Ok(0);
        }
        let mut database_paths = Vec::new();
        collect_legacy_local_storage_databases(&webkit_root, 0, &mut database_paths)?;
        let mut states_by_owner: HashMap<String, Vec<UiChatState>> = HashMap::new();
        for database_path in database_paths.into_iter().take(512) {
            let Ok(connection) = Connection::open_with_flags(
                database_path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
            ) else {
                continue;
            };
            let Ok(mut statement) = connection
                .prepare("SELECT key, value FROM ItemTable WHERE key LIKE 'rosalind.chats.%'")
            else {
                continue;
            };
            let Ok(rows) = statement.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, Vec<u8>>(1)?))
            }) else {
                continue;
            };
            for row in rows.flatten() {
                let Some(owner_id) = row.0.strip_prefix("rosalind.chats.") else {
                    continue;
                };
                let Ok(owner_id) = percent_decode(owner_id) else {
                    continue;
                };
                let Ok(encoded) = decode_utf16le(&row.1) else {
                    continue;
                };
                let Ok(mut state) = serde_json::from_str::<UiChatState>(&encoded) else {
                    continue;
                };
                if state.active_chat_id.is_empty() {
                    state.active_chat_id = state
                        .chats
                        .first()
                        .map(|chat| chat.id.clone())
                        .unwrap_or_default();
                }
                if validate_ui_chat_state(state.active_chat_id.clone(), state.chats.clone()).is_ok()
                {
                    states_by_owner.entry(owner_id).or_default().push(state);
                }
            }
        }

        let mut imported = 0usize;
        for (owner_id, states) in states_by_owner {
            let already_migrated = {
                let connection = self.lock_connection()?;
                connection
                    .query_row(
                        "SELECT 1 FROM ui_chat_states WHERE owner_id = ?1",
                        [&owner_id],
                        |_| Ok(()),
                    )
                    .optional()
                    .map_err(|error| format!("Unable to inspect desktop chat migration: {error}"))?
                    .is_some()
            };
            if already_migrated {
                continue;
            }
            let merged = merge_legacy_ui_chat_states(states);
            if merged.chats.is_empty() {
                continue;
            }
            self.replace_ui_chat_state(owner_id, merged.active_chat_id, merged.chats)?;
            imported += 1;
        }
        Ok(imported)
    }

    fn create_agent_job(
        &self,
        conversation_id: String,
        request: Value,
    ) -> Result<AgentJob, String> {
        let conversation_id = conversation_id.trim();
        if conversation_id.is_empty() {
            return Err("Conversation id is required".into());
        }
        if !request.is_object() {
            return Err("Agent job request must be a JSON object".into());
        }
        if contains_secret_field(&request) {
            return Err(
                "Agent job requests must reference credentials, not contain secrets".into(),
            );
        }
        let now = unix_millis();
        let job = AgentJob {
            id: Uuid::new_v4().to_string(),
            conversation_id: conversation_id.into(),
            status: "queued".into(),
            request,
            result: None,
            cancellation_requested: false,
            created_at: now,
            started_at: None,
            ended_at: None,
        };
        let request_json = serde_json::to_string(&job.request)
            .map_err(|error| format!("Unable to encode Agent job request: {error}"))?;
        if request_json.len() > MAX_AGENT_JOB_REQUEST_BYTES {
            return Err("Agent job request exceeds the 512 KiB protocol limit".into());
        }
        let connection = self.lock_connection()?;
        connection
            .execute(
                "INSERT INTO agent_jobs (id, conversation_id, status, request_json, cancellation_requested, created_at) VALUES (?1, ?2, ?3, ?4, 0, ?5)",
                params![job.id, job.conversation_id, job.status, request_json, job.created_at],
            )
            .map_err(|error| format!("Unable to create Agent job: {error}"))?;
        Ok(job)
    }

    fn list_agent_jobs(&self, conversation_id: String) -> Result<Vec<AgentJob>, String> {
        let connection = self.lock_connection()?;
        let mut statement = connection
            .prepare(
                "SELECT id, conversation_id, status, request_json, result_json, cancellation_requested, created_at, started_at, ended_at FROM agent_jobs WHERE conversation_id = ?1 ORDER BY created_at DESC, id",
            )
            .map_err(|error| format!("Unable to list Agent jobs: {error}"))?;
        let rows = statement
            .query_map([conversation_id], decode_agent_job)
            .map_err(|error| format!("Unable to read Agent jobs: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode Agent job: {error}"))
    }

    pub(crate) fn get_agent_job(&self, job_id: &str) -> Result<AgentJob, String> {
        let connection = self.lock_connection()?;
        connection
            .query_row(
                "SELECT id, conversation_id, status, request_json, result_json, cancellation_requested, created_at, started_at, ended_at FROM agent_jobs WHERE id = ?1",
                [job_id],
                decode_agent_job,
            )
            .map_err(|error| format!("Unable to find Agent job {job_id}: {error}"))
    }

    pub(crate) fn get_agent_job_detail(&self, job_id: &str) -> Result<AgentJobDetail, String> {
        let connection = self.lock_connection()?;
        let job = connection
            .query_row(
                "SELECT id, conversation_id, status, request_json, result_json, cancellation_requested, created_at, started_at, ended_at FROM agent_jobs WHERE id = ?1",
                [job_id],
                decode_agent_job,
            )
            .map_err(|error| format!("Unable to find Agent job {job_id}: {error}"))?;
        let mut statement = connection
            .prepare(
                "SELECT id, agent_job_id, sequence, kind, payload_json, created_at FROM agent_job_events WHERE agent_job_id = ?1 ORDER BY sequence",
            )
            .map_err(|error| format!("Unable to list Agent job events: {error}"))?;
        let rows = statement
            .query_map([job_id], |row| {
                let payload_json: String = row.get(4)?;
                Ok(AgentJobEvent {
                    id: row.get(0)?,
                    agent_job_id: row.get(1)?,
                    sequence: row.get(2)?,
                    kind: row.get(3)?,
                    payload: serde_json::from_str(&payload_json).unwrap_or(Value::Null),
                    created_at: row.get(5)?,
                })
            })
            .map_err(|error| format!("Unable to read Agent job events: {error}"))?;
        let events = rows
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode Agent job event: {error}"))?;
        Ok(AgentJobDetail { job, events })
    }

    pub(crate) fn apply_worker_status(
        &self,
        expected_job_id: &str,
        worker: WorkerJobStatus,
    ) -> Result<AgentJobDetail, String> {
        if worker.job_id != expected_job_id {
            return Err("Agent Worker returned status for a different AgentJob".into());
        }
        if !is_known_status(&worker.status) {
            return Err(format!(
                "Agent Worker returned unknown status {}",
                worker.status
            ));
        }

        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin Agent job update: {error}"))?;
        let current_status: String = transaction
            .query_row(
                "SELECT status FROM agent_jobs WHERE id = ?1",
                [expected_job_id],
                |row| row.get(0),
            )
            .map_err(|error| format!("Unable to inspect Agent job {expected_job_id}: {error}"))?;
        if !valid_transition(&current_status, &worker.status) {
            return Err(format!(
                "Invalid AgentJob transition from {current_status} to {}",
                worker.status
            ));
        }

        let result = worker
            .result
            .clone()
            .or_else(|| worker.error.as_ref().map(|error| json!({"error": error})));
        let result_json = result
            .as_ref()
            .map(serde_json::to_string)
            .transpose()
            .map_err(|error| format!("Unable to encode Agent job result: {error}"))?;
        transaction
            .execute(
                r#"
                UPDATE agent_jobs
                   SET status = ?2,
                       result_json = COALESCE(?3, result_json),
                       cancellation_requested = CASE WHEN ?4 THEN 1 ELSE cancellation_requested END,
                       started_at = COALESCE(started_at, ?5),
                       ended_at = COALESCE(?6, ended_at)
                 WHERE id = ?1
                "#,
                params![
                    expected_job_id,
                    worker.status,
                    result_json,
                    worker.cancellation_requested,
                    worker.started_at,
                    worker.ended_at,
                ],
            )
            .map_err(|error| format!("Unable to update Agent job: {error}"))?;

        for event in &worker.progress {
            let payload_json = serde_json::to_string(&event.payload)
                .map_err(|error| format!("Unable to encode Agent job progress: {error}"))?;
            transaction
                .execute(
                    "INSERT OR IGNORE INTO agent_job_events (agent_job_id, sequence, kind, payload_json, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                    params![expected_job_id, event.sequence, event.kind, payload_json, event.created_at],
                )
                .map_err(|error| format!("Unable to persist Agent job progress: {error}"))?;
        }
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit Agent job update: {error}"))?;
        drop(connection);
        self.get_agent_job_detail(expected_job_id)
    }

    pub(crate) fn request_cancellation(&self, job_id: &str) -> Result<AgentJobDetail, String> {
        let now = unix_millis();
        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin Agent job cancellation: {error}"))?;
        let current_status: String = transaction
            .query_row(
                "SELECT status FROM agent_jobs WHERE id = ?1",
                [job_id],
                |row| row.get(0),
            )
            .map_err(|error| format!("Unable to inspect Agent job {job_id}: {error}"))?;
        match current_status.as_str() {
            "queued" => {
                transaction
                    .execute(
                        "UPDATE agent_jobs SET status = 'cancelled', cancellation_requested = 1, ended_at = ?2 WHERE id = ?1",
                        params![job_id, now],
                    )
                    .map_err(|error| format!("Unable to cancel queued Agent job: {error}"))?;
                append_database_event(
                    &transaction,
                    job_id,
                    "cancelled",
                    &json!({"reason": "cancelled-before-start"}),
                    now,
                )?;
            }
            "running" => {
                transaction
                    .execute(
                        "UPDATE agent_jobs SET status = 'cancelling', cancellation_requested = 1 WHERE id = ?1",
                        [job_id],
                    )
                    .map_err(|error| format!("Unable to request Agent job cancellation: {error}"))?;
            }
            "cancelling" => {}
            status if is_terminal_status(status) => {}
            status => {
                return Err(format!(
                    "Agent job cannot be cancelled from status {status}"
                ))
            }
        }
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit Agent job cancellation: {error}"))?;
        drop(connection);
        self.get_agent_job_detail(job_id)
    }

    pub(crate) fn create_tool_run(
        &self,
        agent_job_id: &str,
        tool_name: &str,
        executor: &str,
        input: Value,
        permission_snapshot: Value,
        initial_status: &str,
    ) -> Result<ToolRun, String> {
        if !input.is_object() {
            return Err("Tool input must be a JSON object".into());
        }
        if contains_secret_field(&input) {
            return Err("Tool input must reference credentials, not contain secrets".into());
        }
        if !permission_snapshot.is_object() {
            return Err("Tool permission snapshot must be a JSON object".into());
        }
        if !matches!(initial_status, "running" | "awaiting_approval") {
            return Err("ToolRun initial status is invalid".into());
        }
        self.get_agent_job(agent_job_id)?;
        let tool_name = validate_text("Tool name", tool_name.to_string(), 200)?;
        let executor = validate_text("Tool executor", executor.to_string(), 100)?;
        let input_json = serde_json::to_string(&input)
            .map_err(|error| format!("Unable to encode Tool input: {error}"))?;
        if input_json.len() > MAX_AGENT_JOB_REQUEST_BYTES {
            return Err("Tool input exceeds the 512 KiB protocol limit".into());
        }
        let permission_snapshot_json = serde_json::to_string(&permission_snapshot)
            .map_err(|error| format!("Unable to encode Tool permission snapshot: {error}"))?;
        if permission_snapshot_json.len() > 32 * 1024 {
            return Err("Tool permission snapshot exceeds the 32 KiB limit".into());
        }
        let now = unix_millis();
        let tool_run = ToolRun {
            id: Uuid::new_v4().to_string(),
            agent_job_id: agent_job_id.into(),
            tool_name,
            executor,
            status: initial_status.into(),
            input,
            output: None,
            permission_snapshot,
            created_at: now,
            started_at: (initial_status == "running").then_some(now),
            ended_at: None,
        };
        let connection = self.lock_connection()?;
        connection
            .execute(
                "INSERT INTO tool_runs (id, agent_job_id, tool_name, executor, status, input_json, permission_snapshot_json, created_at, started_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
                params![
                    tool_run.id,
                    tool_run.agent_job_id,
                    tool_run.tool_name,
                    tool_run.executor,
                    tool_run.status,
                    input_json,
                    permission_snapshot_json,
                    tool_run.created_at,
                    tool_run.started_at,
                ],
            )
            .map_err(|error| format!("Unable to create ToolRun: {error}"))?;
        Ok(tool_run)
    }

    pub(crate) fn decide_tool_run(
        &self,
        tool_run_id: &str,
        approved: bool,
    ) -> Result<ToolRun, String> {
        let status = if approved { "approved" } else { "denied" };
        let ended_at = (!approved).then_some(unix_millis());
        let output_json = (!approved).then_some(r#"{"decision":"denied"}"#);
        let connection = self.lock_connection()?;
        let updated = connection
            .execute(
                "UPDATE tool_runs SET status = ?2, output_json = ?3, ended_at = ?4 WHERE id = ?1 AND status = 'awaiting_approval'",
                params![tool_run_id, status, output_json, ended_at],
            )
            .map_err(|error| format!("Unable to record ToolRun approval: {error}"))?;
        if updated != 1 {
            return Err("ToolRun is not waiting for approval".into());
        }
        drop(connection);
        self.get_tool_run(tool_run_id)
    }

    pub(crate) fn start_approved_tool_run(&self, tool_run_id: &str) -> Result<ToolRun, String> {
        let connection = self.lock_connection()?;
        let updated = connection
            .execute(
                "UPDATE tool_runs SET status = 'running', started_at = ?2 WHERE id = ?1 AND status = 'approved'",
                params![tool_run_id, unix_millis()],
            )
            .map_err(|error| format!("Unable to start approved ToolRun: {error}"))?;
        if updated != 1 {
            return Err("ToolRun is not approved".into());
        }
        drop(connection);
        self.get_tool_run(tool_run_id)
    }

    pub(crate) fn finish_tool_run(
        &self,
        tool_run_id: &str,
        status: &str,
        output: Value,
    ) -> Result<ToolRun, String> {
        if !matches!(status, "succeeded" | "failed" | "cancelled" | "timed_out") {
            return Err(
                "ToolRun can finish only as succeeded, failed, cancelled, or timed_out".into(),
            );
        }
        let output_json = serde_json::to_string(&output)
            .map_err(|error| format!("Unable to encode Tool output: {error}"))?;
        if output_json.len() > MAX_AGENT_JOB_REQUEST_BYTES {
            return Err("Tool output exceeds the 512 KiB protocol limit".into());
        }
        let connection = self.lock_connection()?;
        let updated = connection
            .execute(
                "UPDATE tool_runs SET status = ?2, output_json = ?3, ended_at = ?4 WHERE id = ?1 AND status IN ('running', 'cancelling')",
                params![tool_run_id, status, output_json, unix_millis()],
            )
            .map_err(|error| format!("Unable to finish ToolRun: {error}"))?;
        if updated != 1 {
            return Err("ToolRun was not found or is already terminal".into());
        }
        drop(connection);
        self.get_tool_run(tool_run_id)
    }

    pub(crate) fn request_tool_run_cancellation(
        &self,
        tool_run_id: &str,
    ) -> Result<ToolRun, String> {
        let connection = self.lock_connection()?;
        let updated = connection
            .execute(
                "UPDATE tool_runs SET status = 'cancelling' WHERE id = ?1 AND status = 'running'",
                [tool_run_id],
            )
            .map_err(|error| format!("Unable to request ToolRun cancellation: {error}"))?;
        if updated != 1 {
            return Err("Only a running ToolRun can be cancelled".into());
        }
        drop(connection);
        self.get_tool_run(tool_run_id)
    }

    pub(crate) fn list_tool_runs(&self, agent_job_id: &str) -> Result<Vec<ToolRun>, String> {
        let connection = self.lock_connection()?;
        let mut statement = connection
            .prepare(
                "SELECT id, agent_job_id, tool_name, executor, status, input_json, output_json, permission_snapshot_json, created_at, started_at, ended_at FROM tool_runs WHERE agent_job_id = ?1 ORDER BY created_at, id",
            )
            .map_err(|error| format!("Unable to list ToolRuns: {error}"))?;
        let rows = statement
            .query_map([agent_job_id], decode_tool_run)
            .map_err(|error| format!("Unable to read ToolRuns: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode ToolRun: {error}"))
    }

    pub(crate) fn get_tool_run(&self, tool_run_id: &str) -> Result<ToolRun, String> {
        let connection = self.lock_connection()?;
        connection
            .query_row(
                "SELECT id, agent_job_id, tool_name, executor, status, input_json, output_json, permission_snapshot_json, created_at, started_at, ended_at FROM tool_runs WHERE id = ?1",
                [tool_run_id],
                decode_tool_run,
            )
            .map_err(|error| format!("Unable to find ToolRun {tool_run_id}: {error}"))
    }

    pub(crate) fn replace_tool_run_artifacts(
        &self,
        tool_run_id: &str,
        artifacts: &[NewArtifact],
    ) -> Result<Vec<Artifact>, String> {
        if artifacts.len() > 100 {
            return Err("A ToolRun can index at most 100 artifacts".into());
        }
        let tool_run = self.get_tool_run(tool_run_id)?;
        for artifact in artifacts {
            let path = Path::new(&artifact.path);
            if artifact.id.trim().is_empty()
                || !matches!(artifact.kind.as_str(), "text" | "file")
                || artifact.path.is_empty()
                || path.is_absolute()
                || !path
                    .components()
                    .all(|component| matches!(component, Component::Normal(_)))
                || artifact.sha256.len() != 64
                || !artifact
                    .sha256
                    .chars()
                    .all(|character| character.is_ascii_hexdigit())
            {
                return Err("Artifact metadata is invalid".into());
            }
        }
        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin Artifact transaction: {error}"))?;
        transaction
            .execute(
                "DELETE FROM artifacts WHERE tool_run_id = ?1",
                [tool_run_id],
            )
            .map_err(|error| format!("Unable to replace ToolRun artifacts: {error}"))?;
        let created_at = unix_millis();
        for artifact in artifacts {
            transaction
                .execute(
                    "INSERT INTO artifacts (id, agent_job_id, tool_run_id, kind, path, sha256, size_bytes, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                    params![
                        artifact.id,
                        tool_run.agent_job_id,
                        tool_run_id,
                        artifact.kind,
                        artifact.path,
                        artifact.sha256,
                        artifact.size_bytes,
                        created_at,
                    ],
                )
                .map_err(|error| format!("Unable to index ToolRun artifact: {error}"))?;
        }
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit Artifact transaction: {error}"))?;
        drop(connection);
        self.list_tool_run_artifacts(tool_run_id)
    }

    pub(crate) fn list_tool_run_artifacts(
        &self,
        tool_run_id: &str,
    ) -> Result<Vec<Artifact>, String> {
        let connection = self.lock_connection()?;
        let mut statement = connection
            .prepare(
                "SELECT id, agent_job_id, tool_run_id, kind, path, sha256, size_bytes, created_at FROM artifacts WHERE tool_run_id = ?1 ORDER BY path, id",
            )
            .map_err(|error| format!("Unable to list ToolRun artifacts: {error}"))?;
        let rows = statement
            .query_map([tool_run_id], decode_artifact)
            .map_err(|error| format!("Unable to read ToolRun artifacts: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode ToolRun artifact: {error}"))
    }

    pub(crate) fn get_artifact(&self, artifact_id: &str) -> Result<Artifact, String> {
        let connection = self.lock_connection()?;
        connection
            .query_row(
                "SELECT id, agent_job_id, tool_run_id, kind, path, sha256, size_bytes, created_at FROM artifacts WHERE id = ?1",
                [artifact_id],
                decode_artifact,
            )
            .map_err(|error| format!("Unable to find Artifact {artifact_id}: {error}"))
    }

    pub(crate) fn list_provider_profiles(&self) -> Result<Vec<ProviderProfile>, String> {
        let connection = self.lock_connection()?;
        let mut statement = connection
            .prepare(
                "SELECT id, name, provider_type, base_url, model, credential_ref, is_default, created_at, updated_at FROM provider_profiles ORDER BY is_default DESC, updated_at DESC, id",
            )
            .map_err(|error| format!("Unable to list Provider profiles: {error}"))?;
        let rows = statement
            .query_map([], decode_provider_profile)
            .map_err(|error| format!("Unable to read Provider profiles: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode Provider profile: {error}"))
    }

    pub(crate) fn get_provider_profile(&self, profile_id: &str) -> Result<ProviderProfile, String> {
        let connection = self.lock_connection()?;
        connection
            .query_row(
                "SELECT id, name, provider_type, base_url, model, credential_ref, is_default, created_at, updated_at FROM provider_profiles WHERE id = ?1",
                [profile_id],
                decode_provider_profile,
            )
            .map_err(|error| format!("Unable to find Provider profile {profile_id}: {error}"))
    }

    pub(crate) fn save_provider_profile(
        &self,
        profile_id: Option<String>,
        name: String,
        provider_type: String,
        base_url: String,
        model: String,
        set_default: bool,
    ) -> Result<ProviderProfile, String> {
        let name = validate_text("Provider name", name, 100)?;
        let provider_type = provider_type.trim();
        if provider_type != "openai_compatible" {
            return Err(
                "Only openai_compatible Provider profiles are supported in this version".into(),
            );
        }
        let base_url = validate_provider_base_url(base_url)?;
        let model = validate_text("Provider model", model, 200)?;
        let now = unix_millis();
        let profile_id = profile_id
            .map(|value| value.trim().to_string())
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| Uuid::new_v4().to_string());
        if profile_id.len() > 128 {
            return Err("Provider profile id is too long".into());
        }

        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin Provider profile update: {error}"))?;
        if set_default {
            transaction
                .execute("UPDATE provider_profiles SET is_default = 0", [])
                .map_err(|error| format!("Unable to update default Provider profile: {error}"))?;
        }
        transaction
            .execute(
                r#"
                INSERT INTO provider_profiles
                    (id, name, provider_type, base_url, model, credential_ref, is_default, created_at, updated_at)
                VALUES (?1, ?2, ?3, ?4, ?5, ?1, ?6, ?7, ?7)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    provider_type = excluded.provider_type,
                    base_url = excluded.base_url,
                    model = excluded.model,
                    is_default = CASE WHEN excluded.is_default = 1 THEN 1 ELSE provider_profiles.is_default END,
                    updated_at = excluded.updated_at
                "#,
                params![
                    profile_id,
                    name,
                    provider_type,
                    base_url,
                    model,
                    set_default,
                    now,
                ],
            )
            .map_err(|error| format!("Unable to save Provider profile: {error}"))?;
        transaction
            .commit()
            .map_err(|error| format!("Unable to commit Provider profile: {error}"))?;
        drop(connection);
        self.get_provider_profile(&profile_id)
    }

    fn get_project_directory_authorization(
        &self,
        project_id: &str,
    ) -> Result<Option<ProjectDirectoryAuthorization>, String> {
        let project_id = validate_text("Project id", project_id.to_string(), 128)?;
        let connection = self.lock_connection()?;
        let record = connection
            .query_row(
                "SELECT project_id, root_path, display_name, access_mode, persistence, authorized_at, updated_at FROM project_directory_authorizations WHERE project_id = ?1",
                [project_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, i64>(5)?,
                        row.get::<_, i64>(6)?,
                    ))
                },
            )
            .optional()
            .map_err(|error| format!("Unable to read project directory authorization: {error}"))?;
        Ok(record.map(
            |(
                project_id,
                root_path,
                display_name,
                access_mode,
                persistence,
                authorized_at,
                updated_at,
            )| {
                project_authorization_view(
                    project_id,
                    root_path,
                    display_name,
                    access_mode,
                    persistence,
                    authorized_at,
                    updated_at,
                )
            },
        ))
    }

    fn authorize_project_directory(
        &self,
        project_id: &str,
        selected_path: &Path,
    ) -> Result<ProjectDirectoryAuthorization, String> {
        let project_id = validate_text("Project id", project_id.to_string(), 128)?;
        let root = validate_project_root(selected_path)?;
        let root_path = root
            .to_str()
            .ok_or_else(|| "Project directory path is not valid Unicode".to_string())?
            .to_string();
        let display_name = root
            .file_name()
            .and_then(|name| name.to_str())
            .filter(|name| !name.is_empty())
            .unwrap_or(&root_path)
            .to_string();
        let now = unix_millis();
        let persistence = if cfg!(target_os = "macos") {
            "macos-path-policy"
        } else if cfg!(target_os = "windows") {
            "windows-path-policy"
        } else {
            "path-policy"
        };

        let mut connection = self.lock_connection()?;
        let transaction = connection
            .transaction()
            .map_err(|error| format!("Unable to begin project authorization update: {error}"))?;
        let assigned_project = transaction
            .query_row(
                "SELECT project_id FROM project_directory_authorizations WHERE root_path = ?1 AND project_id <> ?2",
                params![root_path, project_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(|error| format!("Unable to inspect project directory authorization: {error}"))?;
        if assigned_project.is_some() {
            return Err(
                "This directory is already authorized for another OpenRosalind project".into(),
            );
        }
        transaction
            .execute(
                r#"
                INSERT INTO project_directory_authorizations
                    (project_id, root_path, display_name, access_mode, persistence, authorized_at, updated_at)
                VALUES (?1, ?2, ?3, 'read-write', ?4, ?5, ?5)
                ON CONFLICT(project_id) DO UPDATE SET
                    root_path = excluded.root_path,
                    display_name = excluded.display_name,
                    access_mode = excluded.access_mode,
                    persistence = excluded.persistence,
                    updated_at = excluded.updated_at
                "#,
                params![project_id, root_path, display_name, persistence, now],
            )
            .map_err(|error| format!("Unable to save project directory authorization: {error}"))?;
        transaction.commit().map_err(|error| {
            format!("Unable to commit project directory authorization: {error}")
        })?;
        drop(connection);
        self.get_project_directory_authorization(&project_id)?
            .ok_or_else(|| "Project directory authorization was not saved".to_string())
    }

    fn revoke_project_directory(&self, project_id: &str) -> Result<bool, String> {
        let project_id = validate_text("Project id", project_id.to_string(), 128)?;
        let connection = self.lock_connection()?;
        connection
            .execute(
                "DELETE FROM project_directory_authorizations WHERE project_id = ?1",
                [project_id],
            )
            .map(|changed| changed == 1)
            .map_err(|error| format!("Unable to revoke project directory authorization: {error}"))
    }

    pub(crate) fn authorized_project_directory_for_agent_job(
        &self,
        agent_job_id: &str,
    ) -> Result<AuthorizedProjectDirectory, String> {
        let agent_job_id = validate_text("Agent job id", agent_job_id.to_string(), 128)?;
        let connection = self.lock_connection()?;
        let context = connection
            .query_row(
                r#"
                SELECT conversations.project_id,
                       authorizations.root_path,
                       authorizations.access_mode,
                       authorizations.updated_at
                  FROM agent_jobs jobs
                  JOIN conversations ON conversations.id = jobs.conversation_id
             LEFT JOIN project_directory_authorizations authorizations
                    ON authorizations.project_id = conversations.project_id
                 WHERE jobs.id = ?1
                "#,
                [agent_job_id],
                |row| {
                    Ok((
                        row.get::<_, Option<String>>(0)?,
                        row.get::<_, Option<String>>(1)?,
                        row.get::<_, Option<String>>(2)?,
                        row.get::<_, Option<i64>>(3)?,
                    ))
                },
            )
            .optional()
            .map_err(|error| format!("Unable to resolve AgentJob project directory: {error}"))?
            .ok_or_else(|| "AgentJob was not found".to_string())?;
        let project_id = context
            .0
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| "AgentJob is not associated with a research project".to_string())?;
        let root_path = context.1.ok_or_else(|| {
            "The research project does not have an authorized local directory".to_string()
        })?;
        let root = PathBuf::from(&root_path);
        let canonical = root
            .canonicalize()
            .map_err(|_| "The authorized project directory is no longer available".to_string())?;
        if canonical != root || !canonical.is_dir() {
            return Err("The authorized project directory is no longer available".into());
        }
        Ok(AuthorizedProjectDirectory {
            project_id,
            root: canonical,
            write: context.2.as_deref() == Some("read-write"),
            authorization_updated_at: context.3.unwrap_or_default(),
        })
    }

    fn lock_connection(&self) -> Result<std::sync::MutexGuard<'_, Connection>, String> {
        self.connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())
    }

    pub fn backup_status(&self) -> Result<DesktopBackupStatus, String> {
        let Some(directory) = self.backup_directory.as_ref() else {
            return Ok(DesktopBackupStatus {
                available: false,
                backup_directory: None,
                backups: Vec::new(),
            });
        };
        Ok(DesktopBackupStatus {
            available: true,
            backup_directory: Some(directory.to_string_lossy().into_owned()),
            backups: list_database_backups(directory)?,
        })
    }

    pub fn create_backup(&self) -> Result<DesktopBackupInfo, String> {
        if self.database_path.is_none() {
            return Err("Database backups are unavailable for an in-memory store".into());
        }
        let directory = self
            .backup_directory
            .as_ref()
            .ok_or_else(|| "Database backup directory is unavailable".to_string())?;
        fs::create_dir_all(directory)
            .map_err(|error| format!("Unable to create database backup directory: {error}"))?;
        secure_directory_permissions(directory)?;

        let created_at = unix_millis();
        let suffix = &Uuid::new_v4().simple().to_string()[..8];
        let file_name = format!("desktop-core-{created_at}-{suffix}.db");
        let final_path = directory.join(&file_name);
        let temporary_path = directory.join(format!(".{file_name}.partial"));
        let backup_result: Result<DesktopBackupInfo, String> = (|| {
            let connection = self.lock_connection()?;
            verify_database_integrity(&connection, "quick_check")?;
            connection
                .backup(MAIN_DB, &temporary_path, None)
                .map_err(|error| format!("Unable to create an online database backup: {error}"))?;
            drop(connection);
            secure_file_permissions(&temporary_path)?;
            let backup_connection = Connection::open_with_flags(
                &temporary_path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
            )
            .map_err(|error| format!("Unable to open the new database backup: {error}"))?;
            verify_database_integrity(&backup_connection, "integrity_check")?;
            drop(backup_connection);
            fs::rename(&temporary_path, &final_path)
                .map_err(|error| format!("Unable to finalize database backup: {error}"))?;
            secure_file_permissions(&final_path)?;
            let size_bytes = final_path
                .metadata()
                .map_err(|error| format!("Unable to inspect database backup: {error}"))?
                .len();
            Ok(DesktopBackupInfo {
                file_name,
                created_at,
                size_bytes,
            })
        })();
        if backup_result.is_err() {
            let _ = fs::remove_file(&temporary_path);
        }
        let info = backup_result?;
        self.rotate_database_backups()?;
        let changes = self.lock_connection()?.total_changes();
        *self
            .backup_baseline_changes
            .lock()
            .map_err(|_| "Database backup state lock was poisoned".to_string())? = changes;
        Ok(info)
    }

    pub fn create_backup_if_changed(&self) -> Result<Option<DesktopBackupInfo>, String> {
        if self.database_path.is_none() {
            return Ok(None);
        }
        let changes = self.lock_connection()?.total_changes();
        let baseline = *self
            .backup_baseline_changes
            .lock()
            .map_err(|_| "Database backup state lock was poisoned".to_string())?;
        if changes == baseline {
            return Ok(None);
        }
        self.create_backup().map(Some)
    }

    pub fn restore_backup(&self, file_name: &str) -> Result<DesktopRestoreResult, String> {
        if parse_database_backup_name(file_name).is_none()
            || Path::new(file_name).components().count() != 1
        {
            return Err("The selected database backup name is invalid".into());
        }
        let directory = self
            .backup_directory
            .as_ref()
            .ok_or_else(|| "Database backup directory is unavailable".to_string())?;
        let source_path = directory.join(file_name);
        let source_metadata = fs::symlink_metadata(&source_path)
            .map_err(|error| format!("Unable to inspect the selected database backup: {error}"))?;
        if !source_metadata.file_type().is_file() || source_metadata.file_type().is_symlink() {
            return Err("The selected database backup is not a regular app-managed file".into());
        }

        let staging_path =
            directory.join(format!(".restore-source-{}.db", Uuid::new_v4().simple()));
        fs::copy(&source_path, &staging_path)
            .map_err(|error| format!("Unable to stage the selected database backup: {error}"))?;
        let restore_result: Result<DesktopRestoreResult, String> = (|| {
            secure_file_permissions(&staging_path)?;
            let source = Connection::open_with_flags(
                &staging_path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
            )
            .map_err(|error| format!("Unable to open the selected database backup: {error}"))?;
            verify_database_integrity(&source, "integrity_check")?;
            let source_version = source
                .pragma_query_value(None, "user_version", |row| row.get::<_, i64>(0))
                .map_err(|error| format!("Unable to inspect backup schema version: {error}"))?;
            if source_version > SCHEMA_VERSION {
                return Err(format!(
                    "Database backup schema {source_version} is newer than supported version {SCHEMA_VERSION}"
                ));
            }
            drop(source);

            let safety_backup = self.create_backup()?;
            let mut connection = self.lock_connection()?;
            connection
                .restore(
                    MAIN_DB,
                    &staging_path,
                    None::<fn(rusqlite::backup::Progress)>,
                )
                .map_err(|error| {
                    format!("Unable to restore the selected database backup: {error}")
                })?;
            verify_database_integrity(&connection, "integrity_check")?;
            let changes = connection.total_changes();
            drop(connection);
            *self
                .backup_baseline_changes
                .lock()
                .map_err(|_| "Database backup state lock was poisoned".to_string())? = changes;
            Ok(DesktopRestoreResult {
                restored_backup: file_name.to_string(),
                safety_backup,
            })
        })();
        let _ = fs::remove_file(&staging_path);
        restore_result
    }

    fn create_backup_if_due(&self) -> Result<Option<DesktopBackupInfo>, String> {
        let Some(directory) = self.backup_directory.as_ref() else {
            return Ok(None);
        };
        let latest = list_database_backups(directory)?
            .into_iter()
            .map(|backup| backup.created_at)
            .max();
        let due_before = unix_millis().saturating_sub(DATABASE_BACKUP_INTERVAL.as_millis() as i64);
        if latest.is_some_and(|created_at| created_at > due_before) {
            let changes = self.lock_connection()?.total_changes();
            *self
                .backup_baseline_changes
                .lock()
                .map_err(|_| "Database backup state lock was poisoned".to_string())? = changes;
            return Ok(None);
        }
        self.create_backup().map(Some)
    }

    fn rotate_database_backups(&self) -> Result<(), String> {
        let Some(directory) = self.backup_directory.as_ref() else {
            return Ok(());
        };
        let backups = list_database_backups(directory)?;
        for backup in backups.into_iter().skip(MAX_DATABASE_BACKUPS) {
            let path = directory.join(backup.file_name);
            let metadata = fs::symlink_metadata(&path)
                .map_err(|error| format!("Unable to inspect old database backup: {error}"))?;
            if metadata.file_type().is_file() && !metadata.file_type().is_symlink() {
                fs::remove_file(&path)
                    .map_err(|error| format!("Unable to rotate old database backup: {error}"))?;
            }
        }
        Ok(())
    }
}

fn verify_database_integrity(connection: &Connection, pragma: &str) -> Result<(), String> {
    let statement = match pragma {
        "quick_check" => "PRAGMA quick_check",
        "integrity_check" => "PRAGMA integrity_check",
        _ => return Err("Unsupported database integrity check".into()),
    };
    let result = connection
        .query_row(statement, [], |row| row.get::<_, String>(0))
        .map_err(|error| format!("Unable to run SQLite {pragma}: {error}"))?;
    if result.eq_ignore_ascii_case("ok") {
        Ok(())
    } else {
        Err(format!("SQLite {pragma} reported: {result}"))
    }
}

fn parse_database_backup_name(file_name: &str) -> Option<i64> {
    let value = file_name
        .strip_prefix("desktop-core-")?
        .strip_suffix(".db")?;
    let (timestamp, suffix) = value.split_once('-')?;
    if suffix.len() != 8
        || !suffix
            .chars()
            .all(|character| character.is_ascii_hexdigit())
    {
        return None;
    }
    timestamp.parse::<i64>().ok().filter(|value| *value > 0)
}

fn list_database_backups(directory: &Path) -> Result<Vec<DesktopBackupInfo>, String> {
    if !directory.exists() {
        return Ok(Vec::new());
    }
    let mut backups = Vec::new();
    let entries = fs::read_dir(directory)
        .map_err(|error| format!("Unable to list database backups: {error}"))?;
    for entry in entries {
        let entry = entry.map_err(|error| format!("Unable to inspect database backup: {error}"))?;
        let metadata = entry
            .file_type()
            .map_err(|error| format!("Unable to inspect database backup type: {error}"))?;
        if !metadata.is_file() || metadata.is_symlink() {
            continue;
        }
        let file_name = entry.file_name().to_string_lossy().into_owned();
        let Some(created_at) = parse_database_backup_name(&file_name) else {
            continue;
        };
        let size_bytes = entry
            .metadata()
            .map_err(|error| format!("Unable to inspect database backup size: {error}"))?
            .len();
        backups.push(DesktopBackupInfo {
            file_name,
            created_at,
            size_bytes,
        });
    }
    backups.sort_by(|left, right| right.created_at.cmp(&left.created_at));
    Ok(backups)
}

#[cfg(unix)]
fn secure_directory_permissions(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))
        .map_err(|error| format!("Unable to secure data directory permissions: {error}"))
}

#[cfg(not(unix))]
fn secure_directory_permissions(_path: &Path) -> Result<(), String> {
    Ok(())
}

#[cfg(unix)]
fn secure_file_permissions(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))
        .map_err(|error| format!("Unable to secure database file permissions: {error}"))
}

#[cfg(not(unix))]
fn secure_file_permissions(_path: &Path) -> Result<(), String> {
    Ok(())
}

fn decode_agent_job(row: &Row<'_>) -> rusqlite::Result<AgentJob> {
    let request_json: String = row.get(3)?;
    let result_json: Option<String> = row.get(4)?;
    Ok(AgentJob {
        id: row.get(0)?,
        conversation_id: row.get(1)?,
        status: row.get(2)?,
        request: serde_json::from_str(&request_json).unwrap_or(Value::Null),
        result: result_json
            .as_deref()
            .and_then(|value| serde_json::from_str(value).ok()),
        cancellation_requested: row.get::<_, i64>(5)? != 0,
        created_at: row.get(6)?,
        started_at: row.get(7)?,
        ended_at: row.get(8)?,
    })
}

fn decode_provider_profile(row: &Row<'_>) -> rusqlite::Result<ProviderProfile> {
    Ok(ProviderProfile {
        id: row.get(0)?,
        name: row.get(1)?,
        provider_type: row.get(2)?,
        base_url: row.get(3)?,
        model: row.get(4)?,
        credential_ref: row.get(5)?,
        is_default: row.get::<_, i64>(6)? != 0,
        created_at: row.get(7)?,
        updated_at: row.get(8)?,
    })
}

fn decode_tool_run(row: &Row<'_>) -> rusqlite::Result<ToolRun> {
    let input_json: String = row.get(5)?;
    let output_json: Option<String> = row.get(6)?;
    let permission_snapshot_json: String = row.get(7)?;
    Ok(ToolRun {
        id: row.get(0)?,
        agent_job_id: row.get(1)?,
        tool_name: row.get(2)?,
        executor: row.get(3)?,
        status: row.get(4)?,
        input: serde_json::from_str(&input_json).unwrap_or(Value::Null),
        output: output_json.and_then(|value| serde_json::from_str(&value).ok()),
        permission_snapshot: serde_json::from_str(&permission_snapshot_json).unwrap_or(Value::Null),
        created_at: row.get(8)?,
        started_at: row.get(9)?,
        ended_at: row.get(10)?,
    })
}

fn decode_artifact(row: &Row<'_>) -> rusqlite::Result<Artifact> {
    Ok(Artifact {
        id: row.get(0)?,
        agent_job_id: row.get(1)?,
        tool_run_id: row.get(2)?,
        kind: row.get(3)?,
        path: row.get(4)?,
        sha256: row.get::<_, Option<String>>(5)?.unwrap_or_default(),
        size_bytes: row.get::<_, Option<i64>>(6)?.unwrap_or_default(),
        created_at: row.get(7)?,
    })
}

fn project_authorization_view(
    project_id: String,
    root_path: String,
    display_name: String,
    access_mode: String,
    persistence: String,
    authorized_at: i64,
    updated_at: i64,
) -> ProjectDirectoryAuthorization {
    let root = Path::new(&root_path);
    let available = root.is_dir()
        && root
            .canonicalize()
            .map(|canonical| canonical == root)
            .unwrap_or(false);
    ProjectDirectoryAuthorization {
        project_id,
        display_name,
        display_path: root_path,
        read: true,
        write: access_mode == "read-write",
        available,
        persistence,
        authorized_at,
        updated_at,
    }
}

fn validate_project_root(selected_path: &Path) -> Result<PathBuf, String> {
    let root = selected_path
        .canonicalize()
        .map_err(|error| format!("Unable to resolve selected project directory: {error}"))?;
    if !root.is_dir() {
        return Err("The selected project path is not a directory".into());
    }
    if root.parent().is_none() {
        return Err("A filesystem root cannot be authorized as an OpenRosalind project".into());
    }
    let home = env::var_os(if cfg!(target_os = "windows") {
        "USERPROFILE"
    } else {
        "HOME"
    })
    .map(PathBuf::from)
    .and_then(|path| path.canonicalize().ok());
    if home.as_ref() == Some(&root) {
        return Err("Your entire home directory cannot be authorized as one project".into());
    }
    Ok(root)
}

fn reveal_directory(path: &Path) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(path);
        command
    };
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("explorer.exe");
        command.arg(path);
        command
    };
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(path);
        command
    };
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("Unable to open project directory in the file manager: {error}"))
}

fn validate_text(label: &str, value: String, max_characters: usize) -> Result<String, String> {
    let value = value.trim();
    if value.is_empty()
        || value.chars().count() > max_characters
        || value.chars().any(char::is_control)
    {
        return Err(format!(
            "{label} must contain 1 to {max_characters} printable characters"
        ));
    }
    Ok(value.to_string())
}

fn validate_ui_chat_state(
    active_chat_id: String,
    mut chats: Vec<UiChatSnapshot>,
) -> Result<(String, Vec<UiChatSnapshot>, Vec<String>), String> {
    if chats.len() > MAX_UI_CHATS {
        return Err(format!(
            "Desktop chat state exceeds the {MAX_UI_CHATS} chat limit"
        ));
    }
    let active_chat_id = active_chat_id.trim().to_string();
    if !active_chat_id.is_empty() {
        validate_text("Active chat id", active_chat_id.clone(), 128)?;
    }

    let mut chat_ids = HashSet::new();
    let mut message_count = 0usize;
    let mut encoded_bytes = 0usize;
    let mut encoded_messages = Vec::new();
    for chat in &mut chats {
        chat.id = validate_text("Chat id", std::mem::take(&mut chat.id), 128)?;
        if !chat_ids.insert(chat.id.clone()) {
            return Err("Desktop chat state contains duplicate chat ids".into());
        }
        chat.function_id = validate_text(
            "Chat function id",
            std::mem::take(&mut chat.function_id),
            100,
        )?;
        chat.title = validate_text("Chat title", std::mem::take(&mut chat.title), 200)?;
        chat.created_at = validate_text(
            "Chat created timestamp",
            std::mem::take(&mut chat.created_at),
            64,
        )?;
        chat.updated_at = validate_text(
            "Chat updated timestamp",
            std::mem::take(&mut chat.updated_at),
            64,
        )?;

        message_count = message_count
            .checked_add(chat.messages.len())
            .ok_or_else(|| "Desktop chat message count overflowed".to_string())?;
        if message_count > MAX_UI_MESSAGES {
            return Err(format!(
                "Desktop chat state exceeds the {MAX_UI_MESSAGES} message limit"
            ));
        }
        let mut message_ids = HashSet::new();
        for message in &chat.messages {
            let object = message
                .as_object()
                .ok_or_else(|| "Desktop chat messages must be JSON objects".to_string())?;
            let message_id = object
                .get("id")
                .and_then(Value::as_str)
                .ok_or_else(|| "Desktop chat message id is required".to_string())?;
            validate_text("Chat message id", message_id.to_string(), 128)?;
            if !message_ids.insert(message_id.to_string()) {
                return Err("Desktop chat contains duplicate message ids".into());
            }
            let role = object
                .get("role")
                .and_then(Value::as_str)
                .ok_or_else(|| "Desktop chat message role is required".to_string())?;
            if !matches!(role, "user" | "assistant") {
                return Err("Desktop chat message role must be user or assistant".into());
            }
            if !object.get("content").is_some_and(Value::is_string) {
                return Err("Desktop chat message content must be text".into());
            }
            let encoded = serde_json::to_string(message)
                .map_err(|error| format!("Unable to encode desktop chat message: {error}"))?;
            if encoded.len() > MAX_UI_MESSAGE_BYTES {
                return Err("Desktop chat message exceeds the 2 MiB limit".into());
            }
            encoded_bytes = encoded_bytes
                .checked_add(encoded.len())
                .ok_or_else(|| "Desktop chat state size overflowed".to_string())?;
            if encoded_bytes > MAX_UI_CHAT_STATE_BYTES {
                return Err("Desktop chat state exceeds the 50 MiB limit".into());
            }
            encoded_messages.push(encoded);
        }
    }
    if chats.is_empty() {
        if !active_chat_id.is_empty() {
            return Err("Active chat id must be empty when there are no chats".into());
        }
    } else if !chat_ids.contains(&active_chat_id) {
        return Err("Active chat id does not belong to the desktop chat state".into());
    }
    Ok((active_chat_id, chats, encoded_messages))
}

#[cfg(target_os = "macos")]
fn collect_legacy_local_storage_databases(
    directory: &Path,
    depth: usize,
    results: &mut Vec<PathBuf>,
) -> Result<(), String> {
    if depth > 6 || results.len() >= 512 {
        return Ok(());
    }
    let entries = std::fs::read_dir(directory)
        .map_err(|error| format!("Unable to inspect legacy WebKit chat storage: {error}"))?;
    for entry in entries.flatten() {
        let path = entry.path();
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if file_type.is_symlink() {
            continue;
        }
        if file_type.is_dir() {
            collect_legacy_local_storage_databases(&path, depth + 1, results)?;
        } else if file_type.is_file()
            && path.file_name().and_then(|value| value.to_str()) == Some("localstorage.sqlite3")
        {
            results.push(path);
        }
        if results.len() >= 512 {
            break;
        }
    }
    Ok(())
}

#[cfg(target_os = "macos")]
fn decode_utf16le(bytes: &[u8]) -> Result<String, String> {
    if bytes.len() % 2 != 0 {
        return Err("Legacy WebKit chat value has invalid UTF-16 length".into());
    }
    let values = bytes
        .chunks_exact(2)
        .map(|chunk| u16::from_le_bytes([chunk[0], chunk[1]]))
        .collect::<Vec<_>>();
    String::from_utf16(&values)
        .map_err(|_| "Legacy WebKit chat value contains invalid UTF-16".to_string())
}

#[cfg(target_os = "macos")]
fn percent_decode(value: &str) -> Result<String, String> {
    let bytes = value.as_bytes();
    let mut decoded = Vec::with_capacity(bytes.len());
    let mut index = 0usize;
    while index < bytes.len() {
        if bytes[index] == b'%' {
            if index + 2 >= bytes.len() {
                return Err("Legacy chat owner id contains invalid percent encoding".into());
            }
            let high = (bytes[index + 1] as char).to_digit(16).ok_or_else(|| {
                "Legacy chat owner id contains invalid percent encoding".to_string()
            })?;
            let low = (bytes[index + 2] as char).to_digit(16).ok_or_else(|| {
                "Legacy chat owner id contains invalid percent encoding".to_string()
            })?;
            decoded.push(((high << 4) | low) as u8);
            index += 3;
        } else {
            decoded.push(bytes[index]);
            index += 1;
        }
    }
    String::from_utf8(decoded).map_err(|_| "Legacy chat owner id is not valid UTF-8".to_string())
}

#[cfg(target_os = "macos")]
fn merge_legacy_ui_chat_states(states: Vec<UiChatState>) -> UiChatState {
    let mut chats_by_id: HashMap<String, UiChatSnapshot> = HashMap::new();
    let mut active_candidate: Option<(String, String)> = None;
    for state in states {
        if let Some(active_chat) = state
            .chats
            .iter()
            .find(|chat| chat.id == state.active_chat_id)
        {
            let candidate = (active_chat.updated_at.clone(), active_chat.id.clone());
            if active_candidate
                .as_ref()
                .map_or(true, |current| candidate.0 > current.0)
            {
                active_candidate = Some(candidate);
            }
        }
        for chat in state.chats {
            let replace = chats_by_id.get(&chat.id).map_or(true, |existing| {
                chat.updated_at > existing.updated_at
                    || (chat.updated_at == existing.updated_at
                        && chat.messages.len() > existing.messages.len())
            });
            if replace {
                chats_by_id.insert(chat.id.clone(), chat);
            }
        }
    }
    let mut chats = chats_by_id.into_values().collect::<Vec<_>>();
    chats.sort_by(|left, right| {
        right
            .updated_at
            .cmp(&left.updated_at)
            .then_with(|| left.id.cmp(&right.id))
    });
    let active_chat_id = active_candidate
        .map(|candidate| candidate.1)
        .filter(|id| chats.iter().any(|chat| &chat.id == id))
        .or_else(|| chats.first().map(|chat| chat.id.clone()))
        .unwrap_or_default();
    UiChatState {
        active_chat_id,
        chats,
    }
}

fn validate_provider_base_url(value: String) -> Result<String, String> {
    let value = value.trim().trim_end_matches('/');
    let url = tauri::Url::parse(value).map_err(|_| "Provider Base URL is invalid".to_string())?;
    if url.username() != ""
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return Err("Provider Base URL cannot contain credentials, query, or fragment".into());
    }
    let secure = url.scheme() == "https";
    let loopback_http = cfg!(debug_assertions)
        && url.scheme() == "http"
        && matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "::1"));
    if !secure && !loopback_http {
        return Err(
            "Provider Base URL must use HTTPS (debug builds also allow loopback HTTP)".into(),
        );
    }
    if url.host_str().is_none() {
        return Err("Provider Base URL must include a host".into());
    }
    Ok(value.to_string())
}

fn append_database_event(
    transaction: &rusqlite::Transaction<'_>,
    job_id: &str,
    kind: &str,
    payload: &Value,
    created_at: i64,
) -> Result<(), String> {
    let payload_json = serde_json::to_string(payload)
        .map_err(|error| format!("Unable to encode Agent job event: {error}"))?;
    transaction
        .execute(
            r#"
            INSERT INTO agent_job_events (agent_job_id, sequence, kind, payload_json, created_at)
            VALUES (
                ?1,
                COALESCE((SELECT MAX(sequence) FROM agent_job_events WHERE agent_job_id = ?1), 0) + 1,
                ?2,
                ?3,
                ?4
            )
            "#,
            params![job_id, kind, payload_json, created_at],
        )
        .map_err(|error| format!("Unable to persist Agent job event: {error}"))?;
    Ok(())
}

pub(crate) fn is_terminal_status(status: &str) -> bool {
    TERMINAL_STATUSES.contains(&status)
}

fn is_known_status(status: &str) -> bool {
    matches!(
        status,
        "queued" | "running" | "cancelling" | "completed" | "cancelled" | "failed"
    )
}

fn valid_transition(from: &str, to: &str) -> bool {
    if from == to {
        return true;
    }
    match from {
        "queued" => matches!(
            to,
            "running" | "cancelling" | "completed" | "cancelled" | "failed"
        ),
        "running" => matches!(to, "cancelling" | "completed" | "cancelled" | "failed"),
        "cancelling" => matches!(to, "completed" | "cancelled" | "failed"),
        _ => false,
    }
}

fn unix_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as i64)
        .unwrap_or_default()
}

fn contains_secret_field(value: &Value) -> bool {
    match value {
        Value::Object(values) => values.iter().any(|(key, value)| {
            let normalized = key
                .chars()
                .filter(|character| character.is_ascii_alphanumeric())
                .flat_map(char::to_lowercase)
                .collect::<String>();
            matches!(
                normalized.as_str(),
                "apikey"
                    | "authorization"
                    | "credential"
                    | "credentials"
                    | "password"
                    | "secret"
                    | "token"
            ) || contains_secret_field(value)
        }),
        Value::Array(values) => values.iter().any(contains_secret_field),
        _ => false,
    }
}

#[tauri::command]
pub fn desktop_create_conversation(
    state: State<'_, DesktopStore>,
    title: String,
    project_id: Option<String>,
) -> Result<Conversation, String> {
    state.create_conversation(title, project_id)
}

#[tauri::command]
pub fn desktop_list_conversations(
    state: State<'_, DesktopStore>,
) -> Result<Vec<Conversation>, String> {
    state.list_conversations()
}

#[tauri::command]
pub fn desktop_load_ui_chat_state(
    state: State<'_, DesktopStore>,
    owner_id: String,
) -> Result<UiChatState, String> {
    state.load_ui_chat_state(owner_id)
}

#[tauri::command]
pub fn desktop_replace_ui_chat_state(
    state: State<'_, DesktopStore>,
    owner_id: String,
    active_chat_id: String,
    chats: Vec<UiChatSnapshot>,
) -> Result<UiChatState, String> {
    state.replace_ui_chat_state(owner_id, active_chat_id, chats)
}

#[tauri::command]
pub fn desktop_create_agent_job(
    state: State<'_, DesktopStore>,
    conversation_id: String,
    request: Value,
) -> Result<AgentJob, String> {
    state.create_agent_job(conversation_id, request)
}

#[tauri::command]
pub fn desktop_list_agent_jobs(
    state: State<'_, DesktopStore>,
    conversation_id: String,
) -> Result<Vec<AgentJob>, String> {
    state.list_agent_jobs(conversation_id)
}

#[tauri::command]
pub fn desktop_get_project_directory_authorization(
    state: State<'_, DesktopStore>,
    project_id: String,
) -> Result<Option<ProjectDirectoryAuthorization>, String> {
    state.get_project_directory_authorization(project_id.trim())
}

#[tauri::command]
pub async fn desktop_authorize_project_directory(
    app: AppHandle,
    state: State<'_, DesktopStore>,
    project_id: String,
) -> Result<Option<ProjectDirectoryAuthorization>, String> {
    let Some(selection) = app
        .dialog()
        .file()
        .set_title("选择 OpenRosalind 项目目录")
        .blocking_pick_folder()
    else {
        return Ok(None);
    };
    let path = selection
        .into_path()
        .map_err(|_| "Project authorization requires a local filesystem directory".to_string())?;
    state
        .authorize_project_directory(project_id.trim(), &path)
        .map(Some)
}

#[tauri::command]
pub fn desktop_reveal_project_directory(
    state: State<'_, DesktopStore>,
    project_id: String,
) -> Result<(), String> {
    let authorization = state
        .get_project_directory_authorization(project_id.trim())?
        .ok_or_else(|| "This project does not have an authorized local directory".to_string())?;
    if !authorization.available {
        return Err("The authorized project directory is no longer available".into());
    }
    reveal_directory(Path::new(&authorization.display_path))
}

#[tauri::command]
pub fn desktop_revoke_project_directory(
    state: State<'_, DesktopStore>,
    project_id: String,
) -> Result<bool, String> {
    state.revoke_project_directory(project_id.trim())
}

#[tauri::command]
pub fn desktop_data_backup_status(
    state: State<'_, DesktopStore>,
) -> Result<DesktopBackupStatus, String> {
    state.backup_status()
}

#[tauri::command]
pub fn desktop_create_data_backup(
    state: State<'_, DesktopStore>,
) -> Result<DesktopBackupInfo, String> {
    state.create_backup()
}

#[tauri::command]
pub fn desktop_reveal_data_backups(state: State<'_, DesktopStore>) -> Result<(), String> {
    let directory = state
        .backup_directory
        .as_ref()
        .ok_or_else(|| "Database backup directory is unavailable".to_string())?;
    fs::create_dir_all(directory)
        .map_err(|error| format!("Unable to create database backup directory: {error}"))?;
    secure_directory_permissions(directory)?;
    reveal_directory(directory)
}

#[tauri::command]
pub fn desktop_restore_data_backup(
    app: AppHandle,
    state: State<'_, DesktopStore>,
    file_name: String,
) -> Result<DesktopRestoreResult, String> {
    let result = state.restore_backup(file_name.trim())?;
    app.request_restart();
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::agent::{WorkerJobProgress, WorkerJobStatus};
    use crate::core::tools::{propose_tool_run, run_low_risk_tool};

    fn store() -> DesktopStore {
        DesktopStore::from_connection(Connection::open_in_memory().unwrap()).unwrap()
    }

    fn conversation_and_job(store: &DesktopStore) -> (Conversation, AgentJob) {
        let conversation = store
            .create_conversation("Research plan".into(), Some("project-1".into()))
            .unwrap();
        let job = store
            .create_agent_job(
                conversation.id.clone(),
                json!({"input": "Summarize the dataset"}),
            )
            .unwrap();
        (conversation, job)
    }

    #[test]
    fn migrates_all_local_agent_tables() {
        let store = store();
        let connection = store.connection.lock().unwrap();
        let mut statement = connection
            .prepare(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('conversations', 'ui_chat_states', 'ui_chats', 'ui_chat_messages', 'agent_jobs', 'agent_job_events', 'project_directory_authorizations', 'tool_runs', 'artifacts') ORDER BY name",
            )
            .unwrap();
        let tables = statement
            .query_map([], |row| row.get::<_, String>(0))
            .unwrap()
            .collect::<Result<Vec<_>, _>>()
            .unwrap();

        assert_eq!(
            tables,
            vec![
                "agent_job_events",
                "agent_jobs",
                "artifacts",
                "conversations",
                "project_directory_authorizations",
                "tool_runs",
                "ui_chat_messages",
                "ui_chat_states",
                "ui_chats"
            ]
        );
        assert_eq!(
            connection
                .pragma_query_value(None, "user_version", |row| row.get::<_, i64>(0))
                .unwrap(),
            SCHEMA_VERSION
        );
    }

    #[test]
    fn refuses_to_downgrade_a_newer_schema() {
        let connection = Connection::open_in_memory().unwrap();
        connection
            .pragma_update(None, "user_version", SCHEMA_VERSION + 1)
            .unwrap();

        let error = match DesktopStore::from_connection(connection) {
            Ok(_) => panic!("newer schemas must be rejected"),
            Err(error) => error,
        };

        assert!(error.contains("newer than supported"));
    }

    #[test]
    fn file_store_creates_verified_online_backups() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-backup-test-{}",
            Uuid::new_v4().simple()
        ));
        let database_path = root.join("desktop-core.db");
        let store = DesktopStore::open(&database_path).unwrap();
        store
            .create_conversation("Backup test".into(), Some("project-backup".into()))
            .unwrap();
        let backup = store.create_backup().unwrap();
        let backup_path = root.join("backups").join(&backup.file_name);

        let backup_connection = Connection::open_with_flags(
            &backup_path,
            OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )
        .unwrap();
        verify_database_integrity(&backup_connection, "integrity_check").unwrap();
        let conversation_count: i64 = backup_connection
            .query_row("SELECT COUNT(*) FROM conversations", [], |row| row.get(0))
            .unwrap();
        assert_eq!(conversation_count, 1);
        assert_eq!(store.backup_status().unwrap().backups.len(), 2);

        drop(backup_connection);
        drop(store);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn backup_rotation_only_removes_managed_database_snapshots() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-backup-rotation-test-{}",
            Uuid::new_v4().simple()
        ));
        let store = DesktopStore::open(&root.join("desktop-core.db")).unwrap();
        let backup_directory = root.join("backups");
        fs::write(backup_directory.join("keep-me.db"), b"not managed").unwrap();
        for _ in 0..(MAX_DATABASE_BACKUPS + 2) {
            store.create_backup().unwrap();
        }

        let status = store.backup_status().unwrap();
        assert_eq!(status.backups.len(), MAX_DATABASE_BACKUPS);
        assert!(backup_directory.join("keep-me.db").is_file());

        drop(store);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn corrupted_database_is_rejected_without_overwriting_the_original() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-corrupt-database-test-{}",
            Uuid::new_v4().simple()
        ));
        fs::create_dir_all(&root).unwrap();
        let database_path = root.join("desktop-core.db");
        let original = b"this is not a sqlite database";
        fs::write(&database_path, original).unwrap();

        let error = match DesktopStore::open(&database_path) {
            Ok(_) => panic!("corrupted databases must be rejected"),
            Err(error) => error,
        };

        assert!(error.contains("integrity check"));
        assert!(error.contains("original database was preserved"));
        assert_eq!(fs::read(&database_path).unwrap(), original);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn shutdown_backup_is_only_created_after_database_changes() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-changed-backup-test-{}",
            Uuid::new_v4().simple()
        ));
        let store = DesktopStore::open(&root.join("desktop-core.db")).unwrap();
        assert!(store.create_backup_if_changed().unwrap().is_none());
        store.create_conversation("Changed".into(), None).unwrap();
        assert!(store.create_backup_if_changed().unwrap().is_some());
        assert!(store.create_backup_if_changed().unwrap().is_none());

        drop(store);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn restore_uses_verified_snapshot_and_preserves_a_safety_backup() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-restore-backup-test-{}",
            Uuid::new_v4().simple()
        ));
        let store = DesktopStore::open(&root.join("desktop-core.db")).unwrap();
        store
            .create_conversation("Before snapshot".into(), None)
            .unwrap();
        let selected = store.create_backup().unwrap();
        store
            .create_conversation("After snapshot".into(), None)
            .unwrap();

        let restored = store.restore_backup(&selected.file_name).unwrap();

        assert_eq!(restored.restored_backup, selected.file_name);
        assert_ne!(restored.safety_backup.file_name, selected.file_name);
        assert_eq!(store.list_conversations().unwrap().len(), 1);
        let safety_path = root.join("backups").join(restored.safety_backup.file_name);
        let safety = Connection::open_with_flags(
            safety_path,
            OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )
        .unwrap();
        let safety_count: i64 = safety
            .query_row("SELECT COUNT(*) FROM conversations", [], |row| row.get(0))
            .unwrap();
        assert_eq!(safety_count, 2);

        drop(safety);
        drop(store);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn restore_rejects_paths_and_unknown_backup_files() {
        let root = std::env::temp_dir().join(format!(
            "openrosalind-restore-validation-test-{}",
            Uuid::new_v4().simple()
        ));
        let store = DesktopStore::open(&root.join("desktop-core.db")).unwrap();

        assert!(store.restore_backup("../desktop-core.db").is_err());
        assert!(store
            .restore_backup("desktop-core-1000-deadbeef.db")
            .is_err());

        drop(store);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn conversation_and_agent_job_are_separate_records() {
        let store = store();
        let (conversation, job) = conversation_and_job(&store);

        assert_eq!(store.list_conversations().unwrap().len(), 1);
        let jobs = store.list_agent_jobs(conversation.id.clone()).unwrap();
        assert_eq!(jobs.len(), 1);
        assert_eq!(jobs[0].id, job.id);
        assert_eq!(jobs[0].status, "queued");
        assert_eq!(jobs[0].request["input"], "Summarize the dataset");

        let connection = store.connection.lock().unwrap();
        connection
            .execute("DELETE FROM conversations WHERE id = ?1", [conversation.id])
            .unwrap();
        let remaining: i64 = connection
            .query_row("SELECT COUNT(*) FROM agent_jobs", [], |row| row.get(0))
            .unwrap();
        assert_eq!(remaining, 0);
    }

    #[test]
    fn ui_chat_state_round_trips_replaces_and_isolates_owners() {
        let store = store();
        let chat = UiChatSnapshot {
            id: "chat-1".into(),
            function_id: "research_assistant".into(),
            title: "TP53 plan".into(),
            messages: vec![json!({
                "id": "message-1",
                "role": "user",
                "content": "Design a TP53 study"
            })],
            created_at: "2026-08-27T00:00:00.000Z".into(),
            updated_at: "2026-08-27T00:01:00.000Z".into(),
        };
        store
            .replace_ui_chat_state("user-a".into(), "chat-1".into(), vec![chat])
            .unwrap();
        let loaded = store.load_ui_chat_state("user-a".into()).unwrap();
        assert_eq!(loaded.active_chat_id, "chat-1");
        assert_eq!(loaded.chats.len(), 1);
        assert_eq!(
            loaded.chats[0].messages[0]["content"],
            "Design a TP53 study"
        );

        store
            .replace_ui_chat_state("user-a".into(), "".into(), vec![])
            .unwrap();
        assert!(store
            .load_ui_chat_state("user-a".into())
            .unwrap()
            .chats
            .is_empty());
        assert!(store
            .load_ui_chat_state("user-b".into())
            .unwrap()
            .chats
            .is_empty());
    }

    #[test]
    fn ui_chat_state_rejects_invalid_messages_without_overwriting_existing_data() {
        let store = store();
        let valid = UiChatSnapshot {
            id: "chat-1".into(),
            function_id: "research_assistant".into(),
            title: "Valid chat".into(),
            messages: vec![json!({"id": "message-1", "role": "assistant", "content": "ok"})],
            created_at: "2026-08-27T00:00:00.000Z".into(),
            updated_at: "2026-08-27T00:00:01.000Z".into(),
        };
        store
            .replace_ui_chat_state("user-a".into(), "chat-1".into(), vec![valid.clone()])
            .unwrap();
        let mut invalid = valid;
        invalid.messages = vec![json!({
            "id": "message-2",
            "role": "system",
            "content": "not allowed"
        })];
        let error = store
            .replace_ui_chat_state("user-a".into(), "chat-1".into(), vec![invalid])
            .unwrap_err();
        assert!(error.contains("user or assistant"));
        assert_eq!(
            store.load_ui_chat_state("user-a".into()).unwrap().chats[0].messages[0]["content"],
            "ok"
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn legacy_webkit_chat_values_decode_and_merge_by_newest_chat() {
        let encoded = "{\"activeChatId\":\"chat-1\",\"chats\":[]}";
        let utf16 = encoded
            .encode_utf16()
            .flat_map(u16::to_le_bytes)
            .collect::<Vec<_>>();
        assert_eq!(decode_utf16le(&utf16).unwrap(), encoded);
        assert_eq!(
            percent_decode("person%40example.com").unwrap(),
            "person@example.com"
        );

        let older = UiChatSnapshot {
            id: "chat-1".into(),
            function_id: "research_assistant".into(),
            title: "Older".into(),
            messages: vec![],
            created_at: "2026-08-26T00:00:00.000Z".into(),
            updated_at: "2026-08-26T00:00:00.000Z".into(),
        };
        let mut newer = older.clone();
        newer.title = "Newer".into();
        newer.updated_at = "2026-08-27T00:00:00.000Z".into();
        let merged = merge_legacy_ui_chat_states(vec![
            UiChatState {
                active_chat_id: "chat-1".into(),
                chats: vec![older],
            },
            UiChatState {
                active_chat_id: "chat-1".into(),
                chats: vec![newer],
            },
        ]);
        assert_eq!(merged.active_chat_id, "chat-1");
        assert_eq!(merged.chats[0].title, "Newer");
    }

    #[test]
    fn project_directory_authorization_is_explicit_unique_and_revocable() {
        let store = store();
        let root = env::temp_dir().join(format!("openrosalind-project-{}", Uuid::new_v4()));
        std::fs::create_dir(&root).unwrap();

        let authorization = store
            .authorize_project_directory("project-1", &root)
            .unwrap();
        assert_eq!(authorization.project_id, "project-1");
        assert_eq!(
            authorization.display_name,
            root.file_name().unwrap().to_string_lossy()
        );
        assert!(authorization.read);
        assert!(authorization.write);
        assert!(authorization.available);
        assert_eq!(
            store
                .get_project_directory_authorization("project-1")
                .unwrap()
                .unwrap()
                .display_path,
            root.canonicalize().unwrap().to_string_lossy()
        );
        let conversation = store
            .create_conversation("Authorized project".into(), Some("project-1".into()))
            .unwrap();
        let job = store
            .create_agent_job(conversation.id, json!({"mode": "tool-host"}))
            .unwrap();
        let grant = store
            .authorized_project_directory_for_agent_job(&job.id)
            .unwrap();
        assert_eq!(grant.project_id, "project-1");
        assert_eq!(grant.root, root.canonicalize().unwrap());
        assert!(grant.write);

        let duplicate = store
            .authorize_project_directory("project-2", &root)
            .unwrap_err();
        assert!(duplicate.contains("already authorized"));
        assert!(store.revoke_project_directory("project-1").unwrap());
        assert!(store
            .get_project_directory_authorization("project-1")
            .unwrap()
            .is_none());

        std::fs::remove_dir(&root).unwrap();
    }

    #[test]
    fn project_write_proposal_requires_a_complete_audited_read() {
        let store = store();
        let root = env::temp_dir().join(format!(
            "openrosalind-project-write-review-{}",
            Uuid::new_v4()
        ));
        std::fs::create_dir(&root).unwrap();
        std::fs::write(root.join("result.md"), "reviewed content").unwrap();
        store
            .authorize_project_directory("project-reviewed-write", &root)
            .unwrap();
        let conversation = store
            .create_conversation(
                "Reviewed write".into(),
                Some("project-reviewed-write".into()),
            )
            .unwrap();
        let job = store
            .create_agent_job(conversation.id, json!({"mode":"agent"}))
            .unwrap();

        let unreviewed = propose_tool_run(
            &store,
            &job.id,
            "project.file.write",
            json!({
                "path":"result.md",
                "content":"replacement",
                "expectedSha256":"0".repeat(64)
            }),
            None,
        )
        .unwrap_err();
        assert!(unreviewed.contains("successful, complete project.file.read"));

        let read = run_low_risk_tool(
            &store,
            &job.id,
            "project.file.read",
            json!({"path":"result.md"}),
        )
        .unwrap();
        let digest = read.output.unwrap()["sha256"].as_str().unwrap().to_string();
        let proposed = propose_tool_run(
            &store,
            &job.id,
            "project.file.write",
            json!({
                "path":"result.md",
                "content":"replacement",
                "expectedSha256":digest
            }),
            None,
        )
        .unwrap();
        assert_eq!(proposed.status, "awaiting_approval");

        std::fs::remove_dir_all(&root).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn project_directory_authorization_rejects_filesystem_root() {
        let error = validate_project_root(Path::new("/")).unwrap_err();
        assert!(error.contains("filesystem root"));
    }

    #[test]
    fn agent_job_rejects_embedded_credentials() {
        let store = store();
        let conversation = store
            .create_conversation("Credential boundary".into(), None)
            .unwrap();

        let error = store
            .create_agent_job(
                conversation.id,
                json!({"provider": {"api_key": "must-not-be-persisted"}}),
            )
            .unwrap_err();

        assert!(error.contains("must reference credentials"));
        let connection = store.connection.lock().unwrap();
        let count: i64 = connection
            .query_row("SELECT COUNT(*) FROM agent_jobs", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 0);
    }

    #[test]
    fn agent_job_rejects_oversized_protocol_payloads() {
        let store = store();
        let conversation = store
            .create_conversation("Large request".into(), None)
            .unwrap();

        let error = store
            .create_agent_job(
                conversation.id,
                json!({"messages": [{"role": "user", "content": "x".repeat(MAX_AGENT_JOB_REQUEST_BYTES)}]}),
            )
            .unwrap_err();

        assert!(error.contains("512 KiB"));
    }

    #[test]
    fn tool_run_persists_permission_snapshot_and_terminal_output() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        let tool_run = store
            .create_tool_run(
                &job.id,
                "text.statistics",
                "native",
                json!({"text": "Rosalind"}),
                json!({"risk": "low", "approval": "automatic", "network": "none"}),
                "running",
            )
            .unwrap();

        let completed = store
            .finish_tool_run(&tool_run.id, "succeeded", json!({"characters": 8}))
            .unwrap();
        let listed = store.list_tool_runs(&job.id).unwrap();

        assert_eq!(completed.status, "succeeded");
        assert_eq!(completed.output, Some(json!({"characters": 8})));
        assert_eq!(completed.permission_snapshot["network"], "none");
        assert_eq!(listed.len(), 1);
        assert!(listed[0].ended_at.is_some());
    }

    #[test]
    fn tool_run_artifacts_are_indexed_by_relative_path_and_digest() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        let tool_run = store
            .create_tool_run(
                &job.id,
                "python.run",
                "native",
                json!({"code": "print(1)"}),
                json!({"risk": "critical", "approval": "per-run"}),
                "running",
            )
            .unwrap();
        let artifacts = store
            .replace_tool_run_artifacts(
                &tool_run.id,
                &[NewArtifact {
                    id: "artifact-1".into(),
                    kind: "text".into(),
                    path: "reports/result.txt".into(),
                    sha256: "a".repeat(64),
                    size_bytes: 12,
                }],
            )
            .unwrap();

        assert_eq!(artifacts.len(), 1);
        assert_eq!(artifacts[0].tool_run_id, tool_run.id);
        assert_eq!(artifacts[0].agent_job_id, job.id);
        assert_eq!(artifacts[0].path, "reports/result.txt");
        assert_eq!(
            store.get_artifact("artifact-1").unwrap().sha256,
            "a".repeat(64)
        );
        assert!(store
            .replace_tool_run_artifacts(
                &tool_run.id,
                &[NewArtifact {
                    id: "artifact-2".into(),
                    kind: "text".into(),
                    path: "../outside.txt".into(),
                    sha256: "b".repeat(64),
                    size_bytes: 1,
                }],
            )
            .is_err());
    }

    #[test]
    fn high_risk_tool_run_requires_approval_before_start() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        let proposed = store
            .create_tool_run(
                &job.id,
                "python.run",
                "native",
                json!({"code": "print('safe test')"}),
                json!({"risk": "high", "approval": "per-run", "network": "host"}),
                "awaiting_approval",
            )
            .unwrap();

        assert!(store.start_approved_tool_run(&proposed.id).is_err());
        let approved = store.decide_tool_run(&proposed.id, true).unwrap();
        let running = store.start_approved_tool_run(&proposed.id).unwrap();
        let completed = store
            .finish_tool_run(&proposed.id, "succeeded", json!({"stdout": "safe test"}))
            .unwrap();

        assert_eq!(approved.status, "approved");
        assert_eq!(running.status, "running");
        assert_eq!(completed.status, "succeeded");
    }

    #[test]
    fn denied_tool_run_is_terminal() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        let proposed = store
            .create_tool_run(
                &job.id,
                "python.run",
                "native",
                json!({"code": "print('no')"}),
                json!({"risk": "high", "approval": "per-run"}),
                "awaiting_approval",
            )
            .unwrap();

        let denied = store.decide_tool_run(&proposed.id, false).unwrap();

        assert_eq!(denied.status, "denied");
        assert!(denied.ended_at.is_some());
        assert!(store.start_approved_tool_run(&proposed.id).is_err());
    }

    #[test]
    fn worker_status_and_progress_are_persisted_idempotently() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        let worker = WorkerJobStatus {
            job_id: job.id.clone(),
            status: "running".into(),
            cancellation_requested: false,
            progress: vec![WorkerJobProgress {
                sequence: 1,
                kind: "accepted".into(),
                payload: json!({"protocolVersion": 4}),
                created_at: 100,
            }],
            result: None,
            error: None,
            started_at: Some(101),
            ended_at: None,
            pending_model_request: None,
            pending_tool_request: None,
        };

        store.apply_worker_status(&job.id, worker.clone()).unwrap();
        let detail = store.apply_worker_status(&job.id, worker).unwrap();

        assert_eq!(detail.job.status, "running");
        assert_eq!(detail.events.len(), 1);
        assert_eq!(detail.events[0].kind, "accepted");
    }

    #[test]
    fn queued_job_can_be_cancelled_without_starting_worker() {
        let store = store();
        let (_, job) = conversation_and_job(&store);

        let detail = store.request_cancellation(&job.id).unwrap();

        assert_eq!(detail.job.status, "cancelled");
        assert!(detail.job.cancellation_requested);
        assert_eq!(detail.events[0].kind, "cancelled");
    }

    #[test]
    fn unfinished_jobs_recover_as_interrupted() {
        let store = store();
        let (_, job) = conversation_and_job(&store);
        {
            let connection = store.connection.lock().unwrap();
            connection
                .execute(
                    "UPDATE agent_jobs SET status = 'running', started_at = 10 WHERE id = ?1",
                    [&job.id],
                )
                .unwrap();
        }
        let DesktopStore { connection, .. } = store;
        let connection = Arc::try_unwrap(connection)
            .map_err(|_| "unexpected shared test connection")
            .unwrap()
            .into_inner()
            .unwrap();
        let reopened = DesktopStore::from_connection(connection).unwrap();

        let detail = reopened.get_agent_job_detail(&job.id).unwrap();
        assert_eq!(detail.job.status, "interrupted");
        assert_eq!(detail.events[0].kind, "interrupted");
    }

    #[test]
    fn creates_default_provider_without_a_secret() {
        let store = store();

        let profiles = store.list_provider_profiles().unwrap();

        assert_eq!(profiles.len(), 1);
        assert_eq!(profiles[0].id, DEFAULT_PROVIDER_ID);
        assert_eq!(profiles[0].model, DEFAULT_PROVIDER_MODEL);
        let connection = store.connection.lock().unwrap();
        let columns = connection
            .prepare("PRAGMA table_info(provider_profiles)")
            .unwrap()
            .query_map([], |row| row.get::<_, String>(1))
            .unwrap()
            .collect::<Result<Vec<_>, _>>()
            .unwrap();
        assert!(!columns
            .iter()
            .any(|column| column.contains("key") || column.contains("secret")));
    }

    #[test]
    fn validates_and_updates_provider_profile() {
        let store = store();

        let profile = store
            .save_provider_profile(
                Some(DEFAULT_PROVIDER_ID.into()),
                "Qwen Desktop".into(),
                "openai_compatible".into(),
                "https://example.test/v1/".into(),
                "qwen-test".into(),
                true,
            )
            .unwrap();

        assert_eq!(profile.base_url, "https://example.test/v1");
        assert_eq!(profile.model, "qwen-test");
        assert!(profile.is_default);
        assert_eq!(profile.credential_ref, DEFAULT_PROVIDER_ID);
    }

    #[test]
    fn provider_profile_rejects_insecure_remote_url() {
        let store = store();

        let error = store
            .save_provider_profile(
                None,
                "Unsafe".into(),
                "openai_compatible".into(),
                "http://example.test/v1".into(),
                "model".into(),
                false,
            )
            .unwrap_err();

        assert!(error.contains("HTTPS"));
    }
}
