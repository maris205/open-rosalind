use std::{
    path::Path,
    sync::Mutex,
    time::{SystemTime, UNIX_EPOCH},
};

use rusqlite::{params, Connection};
use serde::Serialize;
use serde_json::Value;
use tauri::State;
use uuid::Uuid;

const SCHEMA_VERSION: i64 = 1;

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
    id: String,
    conversation_id: String,
    status: String,
    request: Value,
    result: Option<Value>,
    cancellation_requested: bool,
    created_at: i64,
    started_at: Option<i64>,
    ended_at: Option<i64>,
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
                CREATE INDEX IF NOT EXISTS tool_runs_job_created
                    ON tool_runs(agent_job_id, created_at);
                CREATE INDEX IF NOT EXISTS artifacts_job_created
                    ON artifacts(agent_job_id, created_at);
                "#,
            )
            .map_err(|error| format!("Unable to migrate Desktop Core database: {error}"))?;
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
        let connection = self
            .connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())?;
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
        let connection = self
            .connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())?;
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
        let connection = self
            .connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())?;
        connection
            .execute(
                "INSERT INTO agent_jobs (id, conversation_id, status, request_json, cancellation_requested, created_at) VALUES (?1, ?2, ?3, ?4, 0, ?5)",
                params![job.id, job.conversation_id, job.status, request_json, job.created_at],
            )
            .map_err(|error| format!("Unable to create Agent job: {error}"))?;
        Ok(job)
    }

    fn list_agent_jobs(&self, conversation_id: String) -> Result<Vec<AgentJob>, String> {
        let connection = self
            .connection
            .lock()
            .map_err(|_| "Desktop Core database lock was poisoned".to_string())?;
        let mut statement = connection
            .prepare(
                "SELECT id, conversation_id, status, request_json, result_json, cancellation_requested, created_at, started_at, ended_at FROM agent_jobs WHERE conversation_id = ?1 ORDER BY created_at DESC, id",
            )
            .map_err(|error| format!("Unable to list Agent jobs: {error}"))?;
        let rows = statement
            .query_map([conversation_id], |row| {
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
            })
            .map_err(|error| format!("Unable to read Agent jobs: {error}"))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("Unable to decode Agent job: {error}"))
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
    use serde_json::json;

    fn store() -> DesktopStore {
        DesktopStore::from_connection(Connection::open_in_memory().unwrap()).unwrap()
    }

    #[test]
    fn migrates_all_local_agent_tables() {
        let store = store();
        let connection = store.connection.lock().unwrap();
        let mut statement = connection
            .prepare(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('conversations', 'agent_jobs', 'tool_runs', 'artifacts') ORDER BY name",
            )
            .unwrap();
        let tables = statement
            .query_map([], |row| row.get::<_, String>(0))
            .unwrap()
            .collect::<Result<Vec<_>, _>>()
            .unwrap();

        assert_eq!(
            tables,
            vec!["agent_jobs", "artifacts", "conversations", "tool_runs"]
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
        connection.pragma_update(None, "user_version", 2).unwrap();

        let error = match DesktopStore::from_connection(connection) {
            Ok(_) => panic!("newer schemas must be rejected"),
            Err(error) => error,
        };

        assert!(error.contains("newer than supported"));
    }

    #[test]
    fn conversation_and_agent_job_are_separate_records() {
        let store = store();
        let conversation = store
            .create_conversation("Research plan".into(), Some("project-1".into()))
            .unwrap();
        let job = store
            .create_agent_job(
                conversation.id.clone(),
                json!({"input": "Summarize the dataset"}),
            )
            .unwrap();

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
}
