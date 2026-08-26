use std::{
    path::Path,
    sync::Mutex,
    time::{SystemTime, UNIX_EPOCH},
};

use rusqlite::{params, Connection, Row};
use serde::Serialize;
use serde_json::{json, Value};
use tauri::State;
use uuid::Uuid;

use super::agent::WorkerJobStatus;

const SCHEMA_VERSION: i64 = 3;
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

pub struct DesktopStore {
    connection: Mutex<Connection>,
}

impl DesktopStore {
    pub fn open(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|error| {
                format!("Unable to create Desktop Core data directory: {error}")
            })?;
        }
        let connection = Connection::open(path)
            .map_err(|error| format!("Unable to open Desktop Core database: {error}"))?;
        Self::from_connection(connection)
    }

    fn from_connection(connection: Connection) -> Result<Self, String> {
        let current_version = connection
            .pragma_query_value(None, "user_version", |row| row.get::<_, i64>(0))
            .map_err(|error| format!("Unable to inspect Desktop Core schema version: {error}"))?;
        if current_version > SCHEMA_VERSION {
            return Err(format!(
                "Desktop Core database schema {current_version} is newer than supported version {SCHEMA_VERSION}"
            ));
        }
        connection
            .execute_batch(
                r#"
                PRAGMA foreign_keys = ON;
                PRAGMA journal_mode = WAL;
                PRAGMA busy_timeout = 5000;

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
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
                CREATE INDEX IF NOT EXISTS agent_jobs_conversation_created
                    ON agent_jobs(conversation_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS agent_job_events_job_sequence
                    ON agent_job_events(agent_job_id, sequence);
                CREATE INDEX IF NOT EXISTS provider_profiles_default_updated
                    ON provider_profiles(is_default DESC, updated_at DESC);
                CREATE INDEX IF NOT EXISTS tool_runs_job_created
                    ON tool_runs(agent_job_id, created_at);
                CREATE INDEX IF NOT EXISTS artifacts_job_created
                    ON artifacts(agent_job_id, created_at);
                "#,
            )
            .map_err(|error| format!("Unable to migrate Desktop Core database: {error}"))?;

        let provider_created_at = unix_millis();
        connection
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
        connection
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
        connection
            .execute(
                "UPDATE agent_jobs SET status = 'interrupted', ended_at = ?1 WHERE status IN ('queued', 'running', 'cancelling')",
                [recovered_at],
            )
            .map_err(|error| format!("Unable to recover interrupted Agent jobs: {error}"))?;
        connection
            .pragma_update(None, "user_version", SCHEMA_VERSION)
            .map_err(|error| format!("Unable to record Desktop Core schema version: {error}"))?;
        Ok(Self {
            connection: Mutex::new(connection),
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

    fn lock_connection(&self) -> Result<std::sync::MutexGuard<'_, Connection>, String> {
        self.connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::agent::{WorkerJobProgress, WorkerJobStatus};

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
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('conversations', 'agent_jobs', 'agent_job_events', 'tool_runs', 'artifacts') ORDER BY name",
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
                "tool_runs"
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
        connection.pragma_update(None, "user_version", 4).unwrap();

        let error = match DesktopStore::from_connection(connection) {
            Ok(_) => panic!("newer schemas must be rejected"),
            Err(error) => error,
        };

        assert!(error.contains("newer than supported"));
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
                payload: json!({"protocolVersion": 2}),
                created_at: 100,
            }],
            result: None,
            error: None,
            started_at: Some(101),
            ended_at: None,
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
        let DesktopStore { connection } = store;
        let reopened = DesktopStore::from_connection(connection.into_inner().unwrap()).unwrap();

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
