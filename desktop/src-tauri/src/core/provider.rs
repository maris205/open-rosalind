use std::{
    collections::HashMap,
    io::{BufRead, BufReader},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};

use keyring::{Entry, Error as KeyringError};
use reqwest::{
    blocking::{Client, Response},
    header::CONTENT_TYPE,
    StatusCode,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{Emitter, State, WebviewWindow};
use zeroize::Zeroizing;

use super::storage::{DesktopStore, ProviderProfile, DEFAULT_PROVIDER_ID};

const CREDENTIAL_SERVICE: &str = "bio.openrosalind.desktop.model-provider";
const MAX_CREDENTIAL_BYTES: usize = 32 * 1024;
const MAX_MESSAGE_CHARACTERS: usize = 100_000;
const MAX_TOTAL_MESSAGE_CHARACTERS: usize = 500_000;
const MAX_RESPONSE_BYTES: usize = 512 * 1024;

trait CredentialVault: Send + Sync {
    fn available(&self) -> Result<(), String>;
    fn set(&self, reference: &str, secret: &str) -> Result<(), String>;
    fn get(&self, reference: &str) -> Result<Option<String>, String>;
    fn delete(&self, reference: &str) -> Result<(), String>;
}

struct SystemCredentialVault;

impl SystemCredentialVault {
    fn entry(reference: &str) -> Result<Entry, String> {
        Entry::new(CREDENTIAL_SERVICE, reference)
            .map_err(|error| format!("Unable to access the system credential store: {error}"))
    }
}

impl CredentialVault for SystemCredentialVault {
    fn available(&self) -> Result<(), String> {
        Entry::store_status()
            .as_ref()
            .map(|_| ())
            .map_err(|error| format!("System credential store is unavailable: {error}"))
    }

    fn set(&self, reference: &str, secret: &str) -> Result<(), String> {
        Self::entry(reference)?
            .set_password(secret)
            .map_err(|error| format!("Unable to save the Provider credential: {error}"))
    }

    fn get(&self, reference: &str) -> Result<Option<String>, String> {
        match Self::entry(reference)?.get_password() {
            Ok(secret) => Ok(Some(secret)),
            Err(KeyringError::NoEntry) => Ok(None),
            Err(error) => Err(format!("Unable to read the Provider credential: {error}")),
        }
    }

    fn delete(&self, reference: &str) -> Result<(), String> {
        match Self::entry(reference)?.delete_credential() {
            Ok(()) | Err(KeyringError::NoEntry) => Ok(()),
            Err(error) => Err(format!("Unable to delete the Provider credential: {error}")),
        }
    }
}

pub struct ProviderManager {
    vault: Arc<dyn CredentialVault>,
    cancellations: Mutex<HashMap<String, Arc<AtomicBool>>>,
}

impl ProviderManager {
    pub fn system() -> Self {
        Self {
            vault: Arc::new(SystemCredentialVault),
            cancellations: Mutex::new(HashMap::new()),
        }
    }

    #[cfg(test)]
    fn new(vault: Arc<dyn CredentialVault>) -> Self {
        Self {
            vault,
            cancellations: Mutex::new(HashMap::new()),
        }
    }

    pub(crate) fn credential(&self, reference: &str) -> Result<String, String> {
        self.vault
            .get(reference)?
            .ok_or_else(|| "Provider API Key is not configured".to_string())
    }

    fn set_credential(&self, reference: &str, secret: String) -> Result<(), String> {
        let secret = secret.trim();
        if secret.is_empty() || secret.len() > MAX_CREDENTIAL_BYTES || secret.contains(['\r', '\n'])
        {
            return Err(
                "Provider API Key must contain 1 to 32768 bytes without line breaks".into(),
            );
        }
        self.vault.set(reference, secret)
    }

    fn has_credential(&self, reference: &str) -> Result<bool, String> {
        Ok(self.vault.get(reference)?.is_some())
    }

    pub(crate) fn begin_request(&self, request_id: &str) -> Result<Arc<AtomicBool>, String> {
        if request_id.is_empty()
            || request_id.len() > 128
            || !request_id
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || character == '-')
        {
            return Err("Provider request id is invalid".into());
        }
        let mut cancellations = self
            .cancellations
            .lock()
            .map_err(|_| "Provider cancellation lock was poisoned".to_string())?;
        if cancellations.contains_key(request_id) {
            return Err("Provider request id is already active".into());
        }
        let cancellation = Arc::new(AtomicBool::new(false));
        cancellations.insert(request_id.into(), cancellation.clone());
        Ok(cancellation)
    }

    pub(crate) fn end_request(&self, request_id: &str) {
        if let Ok(mut cancellations) = self.cancellations.lock() {
            cancellations.remove(request_id);
        }
    }

    pub(crate) fn cancel_request(&self, request_id: &str) -> Result<bool, String> {
        let cancellations = self
            .cancellations
            .lock()
            .map_err(|_| "Provider cancellation lock was poisoned".to_string())?;
        if let Some(cancellation) = cancellations.get(request_id) {
            cancellation.store(true, Ordering::Release);
            Ok(true)
        } else {
            Ok(false)
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderChatMessage {
    role: String,
    content: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderDeltaEvent {
    request_id: String,
    delta: String,
    index: usize,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderChatResult {
    request_id: String,
    model: String,
    content: String,
    finish_reason: Option<String>,
    elapsed_millis: u128,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProviderProfileView {
    id: String,
    name: String,
    provider_type: String,
    base_url: String,
    model: String,
    is_default: bool,
    has_credential: bool,
    created_at: i64,
    updated_at: i64,
}

impl ProviderProfileView {
    fn from_profile(profile: ProviderProfile, has_credential: bool) -> Self {
        Self {
            id: profile.id,
            name: profile.name,
            provider_type: profile.provider_type,
            base_url: profile.base_url,
            model: profile.model,
            is_default: profile.is_default,
            has_credential,
            created_at: profile.created_at,
            updated_at: profile.updated_at,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CredentialVaultStatus {
    available: bool,
    backend: &'static str,
}

fn profile_view(
    manager: &ProviderManager,
    profile: ProviderProfile,
) -> Result<ProviderProfileView, String> {
    let has_credential = manager.has_credential(&profile.credential_ref)?;
    Ok(ProviderProfileView::from_profile(profile, has_credential))
}

fn validate_messages(messages: &[ProviderChatMessage]) -> Result<(), String> {
    if messages.is_empty() || messages.len() > 64 {
        return Err("Provider request must contain 1 to 64 messages".into());
    }
    let mut total = 0usize;
    for message in messages {
        if !matches!(message.role.as_str(), "system" | "user" | "assistant") {
            return Err("Provider message role must be system, user, or assistant".into());
        }
        let length = message.content.chars().count();
        if length == 0 || length > MAX_MESSAGE_CHARACTERS {
            return Err("Each Provider message must contain 1 to 100000 characters".into());
        }
        total = total.saturating_add(length);
    }
    if total > MAX_TOTAL_MESSAGE_CHARACTERS {
        return Err("Provider request exceeds the 500000 character limit".into());
    }
    Ok(())
}

fn http_error(status: StatusCode) -> String {
    match status.as_u16() {
        401 | 403 => "Provider authentication failed; check the API Key".into(),
        404 => "Provider endpoint or model was not found".into(),
        408 | 504 => "Provider request timed out".into(),
        429 => "Provider rate limit or quota was exceeded".into(),
        code => format!("Provider request failed with HTTP {code}"),
    }
}

fn response_content_type(response: &Response) -> &str {
    response
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .unwrap_or_default()
}

fn parse_non_streaming_response(response: Response) -> Result<(String, Option<String>), String> {
    let payload: Value = response
        .json()
        .map_err(|_| "Provider returned invalid JSON".to_string())?;
    let content = payload
        .pointer("/choices/0/message/content")
        .and_then(Value::as_str)
        .ok_or_else(|| "Provider response did not contain message content".to_string())?;
    let finish_reason = payload
        .pointer("/choices/0/finish_reason")
        .and_then(Value::as_str)
        .map(str::to_string);
    if content.len() > MAX_RESPONSE_BYTES {
        return Err("Provider response exceeded the 512 KiB limit".into());
    }
    Ok((content.to_string(), finish_reason))
}

fn stream_response(
    response: Response,
    request_id: &str,
    window: &WebviewWindow,
    cancellation: &AtomicBool,
) -> Result<(String, Option<String>), String> {
    let mut content = String::new();
    let mut finish_reason = None;
    let reader = BufReader::new(response);
    for line in reader.lines() {
        if cancellation.load(Ordering::Acquire) {
            return Err("Provider request was cancelled".into());
        }
        let line = line.map_err(|_| "Unable to read Provider stream".to_string())?;
        let Some(data) = line.strip_prefix("data:").map(str::trim) else {
            continue;
        };
        if data == "[DONE]" {
            break;
        }
        let payload: Value = serde_json::from_str(data)
            .map_err(|_| "Provider stream contained invalid JSON".to_string())?;
        if let Some(delta) = payload
            .pointer("/choices/0/delta/content")
            .and_then(Value::as_str)
        {
            if !delta.is_empty() {
                if content.len().saturating_add(delta.len()) > MAX_RESPONSE_BYTES {
                    return Err("Provider response exceeded the 512 KiB limit".into());
                }
                content.push_str(delta);
                window
                    .emit(
                        "desktop-provider-delta",
                        ProviderDeltaEvent {
                            request_id: request_id.into(),
                            delta: delta.into(),
                            index: content.chars().count(),
                        },
                    )
                    .map_err(|error| format!("Unable to emit Provider progress: {error}"))?;
            }
        }
        if let Some(reason) = payload
            .pointer("/choices/0/finish_reason")
            .and_then(Value::as_str)
        {
            finish_reason = Some(reason.to_string());
        }
    }
    if content.is_empty() && finish_reason.is_none() {
        return Err("Provider stream ended without content".into());
    }
    Ok((content, finish_reason))
}

pub(crate) fn execute_provider_chat(
    manager: &ProviderManager,
    profile: &ProviderProfile,
    request_id: &str,
    messages: &[ProviderChatMessage],
    temperature: f32,
    window: &WebviewWindow,
    cancellation: &AtomicBool,
) -> Result<ProviderChatResult, String> {
    validate_messages(messages)?;
    if !(0.0..=2.0).contains(&temperature) {
        return Err("Provider temperature must be between 0 and 2".into());
    }
    let secret = Zeroizing::new(manager.credential(&profile.credential_ref)?);
    let client = Client::builder()
        .connect_timeout(Duration::from_secs(15))
        .timeout(Duration::from_secs(180))
        .user_agent("OpenRosalind-Desktop/0.1")
        .build()
        .map_err(|_| "Unable to initialize the Provider HTTPS client".to_string())?;
    let started = Instant::now();
    let response = client
        .post(format!("{}/chat/completions", profile.base_url))
        .bearer_auth(secret.as_str())
        .json(&json!({
            "model": profile.model,
            "messages": messages,
            "temperature": temperature,
            "stream": true
        }))
        .send()
        .map_err(|_| "Unable to connect to the Provider".to_string())?;
    if !response.status().is_success() {
        return Err(http_error(response.status()));
    }
    if cancellation.load(Ordering::Acquire) {
        return Err("Provider request was cancelled".into());
    }
    let (content, finish_reason) = if response_content_type(&response).contains("text/event-stream")
    {
        stream_response(response, request_id, window, cancellation)?
    } else {
        parse_non_streaming_response(response)?
    };
    Ok(ProviderChatResult {
        request_id: request_id.into(),
        model: profile.model.clone(),
        content,
        finish_reason,
        elapsed_millis: started.elapsed().as_millis(),
    })
}

#[tauri::command]
pub fn desktop_credential_vault_status(
    manager: State<'_, ProviderManager>,
) -> Result<CredentialVaultStatus, String> {
    manager.vault.available()?;
    Ok(CredentialVaultStatus {
        available: true,
        backend: if cfg!(target_os = "macos") {
            "macOS Keychain"
        } else if cfg!(target_os = "windows") {
            "Windows Credential Manager"
        } else {
            "System Secret Service"
        },
    })
}

#[tauri::command]
pub fn desktop_list_provider_profiles(
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
) -> Result<Vec<ProviderProfileView>, String> {
    store
        .list_provider_profiles()?
        .into_iter()
        .map(|profile| profile_view(&manager, profile))
        .collect()
}

#[tauri::command]
pub fn desktop_save_provider_profile(
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
    profile_id: Option<String>,
    name: String,
    provider_type: String,
    base_url: String,
    model: String,
    api_key: Option<String>,
    set_default: Option<bool>,
) -> Result<ProviderProfileView, String> {
    let profile = store.save_provider_profile(
        profile_id,
        name,
        provider_type,
        base_url,
        model,
        set_default.unwrap_or(true),
    )?;
    if let Some(api_key) = api_key {
        manager.set_credential(&profile.credential_ref, api_key)?;
    }
    profile_view(&manager, profile)
}

#[tauri::command]
pub fn desktop_clear_provider_credential(
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
    profile_id: Option<String>,
) -> Result<ProviderProfileView, String> {
    let profile_id = profile_id.unwrap_or_else(|| DEFAULT_PROVIDER_ID.to_string());
    let profile = store.get_provider_profile(profile_id.trim())?;
    manager.vault.delete(&profile.credential_ref)?;
    Ok(ProviderProfileView::from_profile(profile, false))
}

#[tauri::command]
pub fn desktop_stream_provider_chat(
    window: WebviewWindow,
    manager: State<'_, ProviderManager>,
    store: State<'_, DesktopStore>,
    profile_id: Option<String>,
    request_id: String,
    messages: Vec<ProviderChatMessage>,
    temperature: f32,
) -> Result<ProviderChatResult, String> {
    let profile_id = profile_id.unwrap_or_else(|| DEFAULT_PROVIDER_ID.to_string());
    let profile = store.get_provider_profile(profile_id.trim())?;
    let cancellation = manager.begin_request(&request_id)?;
    let result = execute_provider_chat(
        &manager,
        &profile,
        &request_id,
        &messages,
        temperature,
        &window,
        &cancellation,
    );
    manager.end_request(&request_id);
    result
}

#[tauri::command]
pub fn desktop_cancel_provider_chat(
    manager: State<'_, ProviderManager>,
    request_id: String,
) -> Result<bool, String> {
    manager.cancel_request(request_id.trim())
}

#[cfg(test)]
mod tests {
    use std::{collections::HashMap, sync::Mutex};

    use super::*;

    #[derive(Default)]
    struct MemoryVault {
        values: Mutex<HashMap<String, String>>,
    }

    impl CredentialVault for MemoryVault {
        fn available(&self) -> Result<(), String> {
            Ok(())
        }

        fn set(&self, reference: &str, secret: &str) -> Result<(), String> {
            self.values
                .lock()
                .unwrap()
                .insert(reference.into(), secret.into());
            Ok(())
        }

        fn get(&self, reference: &str) -> Result<Option<String>, String> {
            Ok(self.values.lock().unwrap().get(reference).cloned())
        }

        fn delete(&self, reference: &str) -> Result<(), String> {
            self.values.lock().unwrap().remove(reference);
            Ok(())
        }
    }

    #[test]
    fn credential_is_never_exposed_by_profile_view() {
        let manager = ProviderManager::new(Arc::new(MemoryVault::default()));
        manager
            .set_credential(DEFAULT_PROVIDER_ID, "test-secret-value".into())
            .unwrap();
        let profile = ProviderProfile {
            id: DEFAULT_PROVIDER_ID.into(),
            name: "Qwen".into(),
            provider_type: "openai_compatible".into(),
            base_url: "https://example.test/v1".into(),
            model: "qwen-test".into(),
            credential_ref: DEFAULT_PROVIDER_ID.into(),
            is_default: true,
            created_at: 1,
            updated_at: 1,
        };

        let view = profile_view(&manager, profile).unwrap();
        let encoded = serde_json::to_string(&view).unwrap();

        assert!(view.has_credential);
        assert!(!encoded.contains("test-secret-value"));
        assert!(!encoded.contains("credentialRef"));
    }

    #[test]
    fn credentials_reject_empty_and_multiline_values() {
        let manager = ProviderManager::new(Arc::new(MemoryVault::default()));

        assert!(manager.set_credential("profile", "".into()).is_err());
        assert!(manager
            .set_credential("profile", "line-one\nline-two".into())
            .is_err());
    }

    #[test]
    fn validates_provider_chat_message_boundaries() {
        assert!(validate_messages(&[ProviderChatMessage {
            role: "user".into(),
            content: "Hello".into(),
        }])
        .is_ok());
        assert!(validate_messages(&[ProviderChatMessage {
            role: "tool".into(),
            content: "No".into(),
        }])
        .is_err());
        assert!(validate_messages(&[ProviderChatMessage {
            role: "user".into(),
            content: String::new(),
        }])
        .is_err());
    }

    #[test]
    fn cancellation_ids_are_unique_and_cooperative() {
        let manager = ProviderManager::new(Arc::new(MemoryVault::default()));
        let cancellation = manager.begin_request("request-1").unwrap();

        assert!(manager.begin_request("request-1").is_err());
        assert!(manager.cancel_request("request-1").unwrap());
        assert!(cancellation.load(Ordering::Acquire));
        manager.end_request("request-1");
        assert!(!manager.cancel_request("request-1").unwrap());
    }
}
