#!/usr/bin/env python3
"""Local web UI for Open-Rosalind Edu.

The server is intentionally small and framework-free. It serves the static UI,
offers document upload text extraction, and wraps one OpenAI-compatible
chat-completions call for local use.
"""

from __future__ import annotations

import argparse
import email
import email.policy
import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, quote_plus, unquote


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
SKILLS_DIR = ROOT / ".openhands" / "skills"
CLAUDE_SKILLS_DIR = ROOT / ".claude" / "skills"
PROMPTS_DIR = ROOT / "prompts"
DEFAULT_BASE_URL = "https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.7-max"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_EXTRACTED_CHARS = 120_000
DISCLAIMER = (
    "提示：当前为 Open-Rosalind Edu 模式，输出仅用于学习、写作辅助和初稿生成，"
    "不保证结论、引用、实验方案或统计解释完全正确。正式提交、发表或用于科研决策前，"
    "请人工核验原始文献、数据和引用。本系统不提供临床诊断或治疗建议。"
)


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".rst"}
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
PMID_RE = re.compile(r"\bPMID[:\s]*(\d{6,9})\b|\bPubMed[:\s]*(\d{6,9})\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def decode_text_file(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")



def strip_bibtex_value(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if (value.startswith("{") and value.endswith("}")) or (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    value = re.sub(r"[{}]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def split_bibtex_entries(text: str) -> list[str]:
    entries: list[str] = []
    index = 0
    while True:
        start = text.find("@", index)
        if start == -1:
            break
        brace = text.find("{", start)
        if brace == -1:
            break
        depth = 0
        end = brace
        while end < len(text):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    entries.append(text[start : end + 1])
                    index = end + 1
                    break
            end += 1
        else:
            break
    return entries


def parse_bibtex_fields(entry: str) -> dict[str, str]:
    brace = entry.find("{")
    if brace == -1:
        return {}
    body = entry[brace + 1 : -1].strip()
    comma = body.find(",")
    if comma == -1:
        return {}
    body = body[comma + 1 :]
    fields: dict[str, str] = {}
    index = 0
    while index < len(body):
        match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[index:])
        if not match:
            break
        key = match.group(1).lower()
        value_start = index + match.end()
        if value_start >= len(body):
            break
        if body[value_start] == "{":
            depth = 0
            pos = value_start
            while pos < len(body):
                if body[pos] == "{":
                    depth += 1
                elif body[pos] == "}":
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
                pos += 1
            raw_value = body[value_start:pos]
            index = pos + 1
        elif body[value_start] == '"':
            pos = value_start + 1
            while pos < len(body):
                if body[pos] == '"' and body[pos - 1] != "\\":
                    pos += 1
                    break
                pos += 1
            raw_value = body[value_start:pos]
            index = pos + 1
        else:
            pos = body.find(",", value_start)
            if pos == -1:
                pos = len(body)
            raw_value = body[value_start:pos]
            index = pos + 1
        fields[key] = strip_bibtex_value(raw_value)
    return fields


def format_bibtex_reference(fields: dict[str, str]) -> str:
    authors = fields.get("author", "").replace(" and ", "; ")
    title = fields.get("title", "")
    venue = fields.get("journal") or fields.get("journaltitle") or fields.get("booktitle") or fields.get("publisher", "")
    year = fields.get("year", "")
    volume = fields.get("volume", "")
    number = fields.get("number", "")
    pages = fields.get("pages", "")
    doi = fields.get("doi", "")
    pmid = fields.get("pmid", "")
    parts = [part for part in [authors, title, venue, year] if part]
    ref = ". ".join(parts)
    details: list[str] = []
    if volume:
        details.append(f"vol. {volume}")
    if number:
        details.append(f"no. {number}")
    if pages:
        details.append(f"pages {pages}")
    if details:
        ref = f"{ref}. {', '.join(details)}"
    if doi:
        ref = f"{ref}. doi:{doi}"
    if pmid:
        ref = f"{ref}. PMID:{pmid}"
    return ref.strip().rstrip(".") + "."


def extract_bibtex(data: bytes) -> str:
    text = decode_text_file(data)
    references: list[str] = []
    for entry in split_bibtex_entries(text):
        fields = parse_bibtex_fields(entry)
        reference = format_bibtex_reference(fields)
        if reference.strip() != ".":
            references.append(reference)
    if not references:
        raise ValueError("未能从 BibTeX 中解析到参考文献条目。")
    return "\n".join(references)
def extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("当前环境缺少 python-docx，无法解析 DOCX。") from exc

    from io import BytesIO

    document = Document(BytesIO(data))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("当前环境缺少 pypdf，无法解析 PDF。") from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(f"[Page {index}]\n{text}")
    return "\n\n".join(parts)


def truncate_extracted_text(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_EXTRACTED_CHARS:
        return text, False
    return text[:MAX_EXTRACTED_CHARS], True


def extract_uploaded_document(filename: str, data: bytes) -> dict[str, object]:
    suffix = Path(filename).suffix.lower()
    kind = "document"
    if suffix == ".bib":
        text = extract_bibtex(data)
        kind = "bibliography"
    elif suffix in TEXT_EXTENSIONS:
        text = decode_text_file(data)
    elif suffix == ".docx":
        text = extract_docx(data)
    elif suffix == ".pdf":
        text = extract_pdf(data)
        kind = "paper"
    else:
        raise ValueError(f"暂不支持的文件类型：{suffix or 'unknown'}。支持 pdf/bib/txt/md/csv/tsv/json/docx。")

    text, truncated = truncate_extracted_text(text)
    if not text.strip():
        raise ValueError("未能从文件中提取到可用文本。扫描版 PDF 需要先 OCR。")
    return {
        "filename": filename,
        "size": len(data),
        "extension": suffix,
        "kind": kind,
        "text": text,
        "chars": len(text),
        "truncated": truncated,
    }
def parse_multipart_file(headers, body: bytes) -> tuple[str, bytes]:
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        raise ValueError("上传请求必须使用 multipart/form-data。")

    message = email.message_from_bytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body,
        policy=email.policy.default,
    )
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "document":
            continue
        filename = part.get_filename() or "uploaded.txt"
        data = part.get_payload(decode=True) or b""
        return filename, data
    raise ValueError("没有找到名为 document 的上传文件。")



def clean_identifier(value: str) -> str:
    return value.strip().rstrip(".,;)]}")


def extract_doi(reference: str) -> str:
    match = DOI_RE.search(reference)
    return clean_identifier(match.group(0)) if match else ""


def extract_pmid(reference: str) -> str:
    match = PMID_RE.search(reference)
    if not match:
        return ""
    return next(group for group in match.groups() if group)


def extract_year(reference: str) -> str:
    match = YEAR_RE.search(reference)
    return match.group(1) if match else ""


def normalize_tokens(text: str) -> set[str]:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    stopwords = {"the", "and", "for", "with", "from", "this", "that", "into", "using", "study", "analysis", "of", "in", "on", "a", "an", "to"}
    return {token for token in text.split() if len(token) > 2 and token not in stopwords}


def title_overlap(title: str, reference: str) -> float:
    title_tokens = normalize_tokens(title)
    if not title_tokens:
        return 0.0
    reference_tokens = normalize_tokens(reference)
    return len(title_tokens & reference_tokens) / len(title_tokens)


def parse_reference_lines(text: str) -> list[str]:
    if re.search(r"@\w+\s*{", text):
        try:
            return [line for line in extract_bibtex(text.encode("utf-8")).splitlines() if line.strip()]
        except ValueError:
            pass
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^\s*(\[\d+\]|\d+[.)]|[-*•])\s*", "", line).strip()
        if line:
            lines.append(line)
    if len(lines) <= 1 and ";" in text:
        candidates = [part.strip() for part in text.split(";") if len(part.strip()) > 30]
        return candidates or lines
    return lines
def fetch_json(url: str, timeout: int = 20) -> tuple[dict | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Open-Rosalind-Edu/0.2 (local reference verifier)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report lookup failures to UI
        return None, str(exc)


def crossref_by_doi(doi: str) -> tuple[dict | None, str]:
    data, error = fetch_json(f"https://api.crossref.org/works/{quote(doi, safe='')}")
    if not data:
        return None, error
    return data.get("message"), ""


def crossref_search(reference: str) -> tuple[dict | None, str]:
    data, error = fetch_json(f"https://api.crossref.org/works?rows=3&query.bibliographic={quote_plus(reference)}")
    if not data:
        return None, error
    items = data.get("message", {}).get("items", [])
    return (items[0] if items else None), "" if items else "No Crossref candidates"


def pubmed_by_pmid(pmid: str) -> tuple[dict | None, str]:
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={quote_plus(pmid)}&retmode=json"
    data, error = fetch_json(url)
    if not data:
        return None, error
    result = data.get("result", {})
    return result.get(pmid), "" if result.get(pmid) else "PMID not found"


def crossref_metadata(item: dict | None) -> dict[str, str]:
    if not item:
        return {}
    authors = item.get("author") or []
    first_author = ""
    if authors:
        first = authors[0]
        first_author = " ".join(part for part in [first.get("given", ""), first.get("family", "")] if part).strip()
    year = ""
    date_parts = (item.get("issued") or {}).get("date-parts") or []
    if date_parts and date_parts[0]:
        year = str(date_parts[0][0])
    return {
        "title": (item.get("title") or [""])[0],
        "journal": (item.get("container-title") or [""])[0],
        "year": year,
        "doi": item.get("DOI", ""),
        "firstAuthor": first_author,
        "url": item.get("URL", ""),
    }


def pubmed_metadata(item: dict | None) -> dict[str, str]:
    if not item:
        return {}
    authors = item.get("authors") or []
    first_author = authors[0].get("name", "") if authors else ""
    year_match = YEAR_RE.search(item.get("pubdate", ""))
    return {
        "title": item.get("title", ""),
        "journal": item.get("fulljournalname", "") or item.get("source", ""),
        "year": year_match.group(1) if year_match else "",
        "doi": "",
        "firstAuthor": first_author,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{item.get('uid', '')}/" if item.get("uid") else "",
    }


def assess_reference(reference: str) -> dict[str, object]:
    doi = extract_doi(reference)
    pmid = extract_pmid(reference)
    stated_year = extract_year(reference)
    checks: list[str] = []
    warnings: list[str] = []
    metadata: dict[str, str] = {}
    source = ""
    label = "Unverified"

    if doi:
        item, error = crossref_by_doi(doi)
        if item:
            metadata = crossref_metadata(item)
            source = "Crossref DOI"
            label = "Verified"
            checks.append("DOI exists in Crossref.")
        else:
            warnings.append(f"DOI lookup failed: {error or 'not found'}")
            label = "Fabrication Risk"
    elif pmid:
        item, error = pubmed_by_pmid(pmid)
        if item:
            metadata = pubmed_metadata(item)
            source = "PubMed PMID"
            label = "Verified"
            checks.append("PMID exists in PubMed.")
        else:
            warnings.append(f"PMID lookup failed: {error or 'not found'}")
            label = "Fabrication Risk"
    else:
        item, error = crossref_search(reference)
        if item:
            metadata = crossref_metadata(item)
            source = "Crossref bibliographic search"
            overlap = title_overlap(metadata.get("title", ""), reference)
            checks.append(f"Best Crossref candidate title overlap: {overlap:.2f}.")
            label = "Candidate Match" if overlap >= 0.45 else "Unverified"
            if overlap < 0.45:
                warnings.append("No DOI/PMID supplied and best title match is weak.")
        else:
            warnings.append(error or "No bibliographic candidate found.")

    if metadata:
        if stated_year and metadata.get("year") and stated_year != metadata["year"]:
            label = "Metadata Mismatch"
            warnings.append(f"Year mismatch: reference says {stated_year}, source says {metadata['year']}.")
        if metadata.get("title"):
            overlap = title_overlap(metadata["title"], reference)
            if overlap and overlap < 0.35:
                label = "Metadata Mismatch" if label == "Verified" else label
                warnings.append(f"Title overlap is low ({overlap:.2f}); manually compare the title.")

    if label in {"Unverified", "Fabrication Risk"}:
        warnings.append("Do not use this reference until manually verified from DOI, PMID, publisher page, or library database.")

    return {
        "reference": reference,
        "label": label,
        "doi": doi,
        "pmid": pmid,
        "statedYear": stated_year,
        "source": source,
        "metadata": metadata,
        "checks": checks,
        "warnings": warnings,
    }


def verify_references_text(text: str) -> dict[str, object]:
    references = parse_reference_lines(text)
    if not references:
        return {"ok": False, "error": "没有识别到参考文献条目。请每条参考文献单独成行。"}
    results = [assess_reference(reference) for reference in references[:80]]
    counts: dict[str, int] = {}
    for item in results:
        label = str(item["label"])
        counts[label] = counts.get(label, 0) + 1
    return {
        "ok": True,
        "count": len(results),
        "truncated": len(references) > len(results),
        "counts": counts,
        "results": results,
    }


def reference_report_markdown(result: dict[str, object]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Reference verification failed."))
    lines = ["# 参考文献验证报告", "", "## 总览", ""]
    counts = result.get("counts", {})
    for label in ["Verified", "Metadata Mismatch", "Candidate Match", "Unverified", "Fabrication Risk"]:
        lines.append(f"- {label}: {counts.get(label, 0)}")
    if result.get("truncated"):
        lines.append("- 注意：条目超过 80 条，本次只验证前 80 条。")
    lines.extend(["", "## 逐条结果", ""])
    for index, item in enumerate(result.get("results", []), start=1):
        metadata = item.get("metadata") or {}
        lines.append(f"### {index}. {item.get('label')}")
        lines.append("")
        lines.append(f"原始条目：{item.get('reference')}")
        if item.get("doi"):
            lines.append(f"DOI：{item.get('doi')}")
        if item.get("pmid"):
            lines.append(f"PMID：{item.get('pmid')}")
        if item.get("source"):
            lines.append(f"核验来源：{item.get('source')}")
        if metadata:
            lines.append(f"匹配题名：{metadata.get('title', '')}")
            lines.append(f"期刊：{metadata.get('journal', '')}")
            lines.append(f"年份：{metadata.get('year', '')}")
            lines.append(f"第一作者：{metadata.get('firstAuthor', '')}")
            if metadata.get("url"):
                lines.append(f"链接：{metadata.get('url')}")
        warnings = item.get("warnings") or []
        if warnings:
            lines.append("风险提示：")
            for warning in warnings:
                lines.append(f"- {warning}")
        lines.append("")
    lines.extend([
        "## 人工核验清单",
        "",
        "- 对 Metadata Mismatch、Unverified 和 Fabrication Risk 条目逐条打开 DOI、PMID、出版社页面或图书馆数据库核验。",
        "- 不要仅凭题名相似就认定引用真实存在。",
        "- 参考文献真实存在不等于支持正文 claim；高风险医学 claim 还需要阅读全文核验。",
        "",
        DISCLAIMER,
    ])
    return "\n".join(lines)

def read_skill_prompt(skill: str) -> str:
    openhands_path = SKILLS_DIR / skill / "SKILL.md"
    if openhands_path.exists():
        return read_text(openhands_path)
    claude_path = CLAUDE_SKILLS_DIR / skill / "SKILL.md"
    if claude_path.exists():
        return read_text(claude_path)
    return ""
def summarize_skill(skill_dir: Path) -> dict[str, str]:
    text = read_text(skill_dir / "SKILL.md")
    title = skill_dir.name.replace("_", " ").title()
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    purpose = ""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## Purpose" and index + 2 < len(lines):
            purpose = lines[index + 2].strip()
            break
    return {
        "id": skill_dir.name,
        "title": title,
        "purpose": purpose,
        "content": text,
    }


def load_skills() -> list[dict[str, str]]:
    if not SKILLS_DIR.exists():
        return []
    return [summarize_skill(path) for path in sorted(SKILLS_DIR.iterdir()) if path.is_dir()]


def build_messages(skill: str, user_input: str, history: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    system_prompt = read_text(PROMPTS_DIR / "system_edu.md")
    writing_policy = read_text(PROMPTS_DIR / "writing_policy.md")
    citation_policy = read_text(PROMPTS_DIR / "citation_policy.md")
    skill_prompt = read_skill_prompt(skill)
    system = "\n\n".join(part for part in [system_prompt, writing_policy, citation_policy, skill_prompt] if part)
    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-8:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:8000]})
    user = (
        "请根据所选 Open-Rosalind Edu Skill 处理以下输入。"
        "默认用中文、Markdown 输出，并在结尾附上 Edu Mode disclaimer。\n\n"
        f"{user_input.strip()}"
    )
    messages.append({"role": "user", "content": user})
    return messages


def call_openai_compatible(payload: dict) -> dict:
    api_key = payload.get("apiKey") or os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        return {
            "ok": False,
            "mode": "prompt_only",
            "error": "未提供 API Key。可在页面临时填写，或启动服务前设置 DASHSCOPE_API_KEY。",
            "prompt": payload.get("promptPreview", ""),
        }

    base_url = (payload.get("baseUrl") or os.environ.get("QWEN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = payload.get("model") or os.environ.get("QWEN_MODEL") or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": payload["messages"],
        "temperature": float(payload.get("temperature", 0.3)),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "mode": "error", "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:  # noqa: BLE001 - surface local web errors to UI
        return {"ok": False, "mode": "error", "error": str(exc)}

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"ok": True, "mode": "llm", "content": content, "raw": data}


class Handler(BaseHTTPRequestHandler):
    server_version = "OpenRosalindEdu/0.2"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, data: dict | list, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD_BYTES:
            raise ValueError(f"文件过大，最大支持 {MAX_UPLOAD_BYTES // 1024 // 1024} MB。")
        return self.rfile.read(length)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/config":
            self.send_json(
                {
                    "baseUrl": os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL),
                    "model": os.environ.get("QWEN_MODEL", DEFAULT_MODEL),
                    "hasEnvApiKey": bool(os.environ.get("DASHSCOPE_API_KEY")),
                    "disclaimer": DISCLAIMER,
                }
            )
            return
        if self.path == "/api/skills":
            self.send_json(load_skills())
            return

        path = "/" if self.path == "/" else unquote(self.path.split("?", 1)[0])
        file_path = STATIC_DIR / ("index.html" if path == "/" else path.lstrip("/"))
        if not file_path.exists() or not file_path.resolve().is_relative_to(STATIC_DIR.resolve()):
            self.send_error(404)
            return
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/verify-references":
            try:
                payload = self.read_json()
                input_value = payload.get("input", "")
                if not isinstance(input_value, str):
                    input_value = json.dumps(input_value, ensure_ascii=False)
                result = verify_references_text(input_value)
                if result.get("ok"):
                    result["content"] = reference_report_markdown(result)
                    self.send_json(result)
                else:
                    self.send_json(result, status=400)
            except Exception as exc:  # noqa: BLE001 - surface local verification errors to UI
                self.send_json({"ok": False, "error": f"参考文献验证失败：{exc}"}, status=500)
            return
        if self.path == "/api/upload":
            try:
                filename, data = parse_multipart_file(self.headers, self.read_body())
                result = extract_uploaded_document(filename, data)
                self.send_json({"ok": True, **result})
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=400)
            except Exception as exc:  # noqa: BLE001 - surface local parse errors to UI
                self.send_json({"ok": False, "error": f"解析失败：{exc}"}, status=500)
            return

        if self.path != "/api/generate":
            self.send_error(404)
            return
        payload = self.read_json()
        skill = payload.get("skill", "paper_summary")
        user_input = payload.get("input", "")
        history = payload.get("history") if isinstance(payload.get("history"), list) else []
        messages = build_messages(skill, user_input, history)
        prompt_preview = "\n\n".join(f"{item['role'].upper()}:\n{item['content']}" for item in messages)
        payload["messages"] = messages
        payload["promptPreview"] = prompt_preview
        result = call_openai_compatible(payload)
        if not result.get("ok") and result.get("mode") == "prompt_only":
            result["content"] = (
                "## 待发送 Prompt\n\n"
                "当前未配置 API Key。你可以复制下面的 prompt 到任意兼容模型，"
                "或在左侧临时填写 API Key 后重新生成。\n\n"
                "```text\n"
                f"{prompt_preview}\n"
                "```\n\n"
                f"{DISCLAIMER}"
            )
        self.send_json(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Open-Rosalind Edu web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Open-Rosalind Edu local web UI: http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
