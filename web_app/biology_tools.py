"""Deterministic biology tools adapted from the main branch Skills v2 runtime."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any


UNIPROT_BASE = "https://rest.uniprot.org"
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
AA = set("ACDEFGHIKLMNPQRSTVWY*")
BASIC_NUCLEOTIDE = set("ACGTU")
HYDROPHOBIC = set("AVILMFWY")
POLAR = set("STNQCG")
POSITIVE = set("KRH")
NEGATIVE = set("DE")
AROMATIC = set("FWYH")
HGVS_RE = re.compile(r"(?:p\.)?([A-Z])([1-9]\d*)([A-Z*])", re.IGNORECASE)
ACCESSION_RE = re.compile(r"\b(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]{5}|[A-NR-Z0-9]{10})\b", re.IGNORECASE)


def fetch_json(url: str, params: dict[str, object] | None = None, timeout: int = 30) -> dict[str, Any]:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Open-Rosalind-Edu/0.3"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str, params: dict[str, object], method: str = "GET", timeout: int = 45) -> str:
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(
        url if method == "POST" else f"{url}?{encoded.decode()}",
        data=encoded if method == "POST" else None,
        headers={"User-Agent": "Open-Rosalind-Edu/0.3"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def ncbi_blastp(query_fasta: str, max_hits: int = 5, wait_timeout: int = 180) -> dict[str, Any]:
    email = os.environ.get("NCBI_EMAIL", "").strip()
    submit = request_text(
        BLAST_URL,
        {
            "CMD": "Put",
            "PROGRAM": "blastp",
            "DATABASE": "swissprot",
            "QUERY": query_fasta,
            "HITLIST_SIZE": max_hits,
            "EXPECT": 10,
            "FORMAT_TYPE": "XML",
            "TOOL": "Open-Rosalind-Edu",
            "EMAIL": email,
        },
        method="POST",
        timeout=60,
    )
    rid_match = re.search(r"RID\s*=\s*([A-Z0-9-]+)", submit)
    rtoe_match = re.search(r"RTOE\s*=\s*(\d+)", submit)
    if not rid_match:
        raise ValueError("NCBI BLAST 未返回 RID，任务提交失败。")
    rid = rid_match.group(1)
    initial_wait = min(max(int(rtoe_match.group(1)) if rtoe_match else 5, 3), 15)
    deadline = time.monotonic() + wait_timeout
    time.sleep(initial_wait)
    while time.monotonic() < deadline:
        status_text = request_text(BLAST_URL, {"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"})
        status_match = re.search(r"Status=(\w+)", status_text)
        status = status_match.group(1).upper() if status_match else "UNKNOWN"
        if status == "READY":
            if "ThereAreHits=yes" not in status_text:
                return {"rid": rid, "status": "READY", "has_hits": False, "hits": []}
            break
        if status in {"FAILED", "UNKNOWN"}:
            raise ValueError(f"NCBI BLAST 任务 {rid} 状态为 {status}。")
        time.sleep(5)
    else:
        return {"rid": rid, "status": "WAITING", "has_hits": False, "hits": []}

    xml_text = request_text(
        BLAST_URL,
        {"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML", "ALIGNMENTS": max_hits, "DESCRIPTIONS": max_hits},
        timeout=60,
    )
    root = ET.fromstring(xml_text)
    query_length = int(root.findtext(".//BlastOutput_query-len") or 0)
    hits: list[dict[str, Any]] = []
    for hit in root.findall(".//Hit")[:max_hits]:
        hsp = hit.find(".//Hsp")
        align_length = int(hsp.findtext("Hsp_align-len") or 0) if hsp is not None else 0
        identities = int(hsp.findtext("Hsp_identity") or 0) if hsp is not None else 0
        accession = hit.findtext("Hit_accession") or ""
        hits.append(
            {
                "accession": accession,
                "title": hit.findtext("Hit_def") or "",
                "length": int(hit.findtext("Hit_len") or 0),
                "evalue": hsp.findtext("Hsp_evalue") if hsp is not None else None,
                "bit_score": float(hsp.findtext("Hsp_bit-score") or 0) if hsp is not None else 0.0,
                "identity_percent": round(identities * 100 / align_length, 2) if align_length else 0.0,
                "query_coverage_percent": round(align_length * 100 / query_length, 2) if query_length else 0.0,
                "align_length": align_length,
                "url": f"https://www.ncbi.nlm.nih.gov/protein/{urllib.parse.quote(accession)}" if accession else "",
            }
        )
    return {"rid": rid, "status": "READY", "has_hits": bool(hits), "program": "blastp", "database": "swissprot", "query_length": query_length, "hits": hits}


def clean_sequence(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip() and not line.lstrip().startswith(">")]
    return re.sub(r"[^A-Za-z*]", "", "".join(lines)).upper()


def looks_like_sequence_input(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if re.search(r"(?:^|\n)\s*>", stripped):
        return True
    compact = re.sub(r"\s+", "", stripped)
    return len(compact) >= 10 and bool(re.fullmatch(r"[A-Za-z0-9*-]+", compact)) and not bool(ACCESSION_RE.fullmatch(stripped))


def protein_sequence_validation_error(value: str) -> str:
    symbols = [character.upper() for character in value if not character.isspace() and character not in {"-", "."}]
    if not symbols:
        return "FASTA 标题后未找到序列。请将序列放在标题下一行。"
    letters = [character for character in symbols if "A" <= character <= "Z" or character == "*"]
    nucleotide_fraction = sum(character in BASIC_NUCLEOTIDE for character in letters) / len(letters) if letters else 0.0
    expected = BASIC_NUCLEOTIDE if nucleotide_fraction >= 0.5 else AA
    invalid = list(dict.fromkeys(character for character in symbols if character not in expected))
    if invalid:
        return (
            f"无法可靠判定序列类型。检测到非法或不兼容字符：{'、'.join(invalid)}。"
            "请提供仅包含标准核酸或氨基酸字符的 FASTA 序列；本次未执行 BLAST。"
        )
    if nucleotide_fraction >= 0.9 and len(letters) >= 8:
        return "输入内容更像核酸序列，不适用于蛋白质分析。请改用序列分析工具；本次未执行 BLAST。"
    return ""


def looks_like_instruction_line(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]|\s|[，。！？；：]", value))


def fasta_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    name = "sequence"
    chunks: list[str] = []
    has_header = any(line.strip().startswith(">") for line in text.splitlines())
    collecting = not has_header
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(">"):
            if chunks:
                raw_sequence = "\n".join(chunks)
                records.append({"name": name, "sequence": clean_sequence(raw_sequence), "raw_sequence": raw_sequence})
            name = line[1:].strip() or f"sequence_{len(records) + 1}"
            chunks = []
            collecting = True
        elif line and collecting:
            if has_header and looks_like_instruction_line(line):
                collecting = False
            else:
                chunks.append(line)
    if chunks:
        raw_sequence = "\n".join(chunks)
        records.append({"name": name, "sequence": clean_sequence(raw_sequence), "raw_sequence": raw_sequence})
    return [record for record in records if record["sequence"]]


def protein_stats(sequence: str) -> dict[str, Any]:
    sequence = clean_sequence(sequence)
    invalid = sorted(set(sequence) - AA)
    counts = Counter(sequence)
    length = len(sequence)
    return {
        "length": length,
        "invalid": invalid,
        "composition": dict(sorted(counts.items())),
        "hydrophobic_percent": round(sum(counts[aa] for aa in HYDROPHOBIC) * 100 / length, 2) if length else 0.0,
        "charged_percent": round(sum(counts[aa] for aa in POSITIVE | NEGATIVE) * 100 / length, 2) if length else 0.0,
    }


def compact_uniprot(entry: dict[str, Any]) -> dict[str, Any]:
    description = entry.get("proteinDescription", {})
    recommended = description.get("recommendedName", {}).get("fullName", {}).get("value")
    if not recommended:
        recommended = description.get("submissionNames", [{}])[0].get("fullName", {}).get("value")
    functions: list[str] = []
    locations: list[str] = []
    for comment in entry.get("comments", []) or []:
        if comment.get("commentType") == "FUNCTION":
            functions.extend(item.get("value", "") for item in comment.get("texts", []) if item.get("value"))
        if comment.get("commentType") == "SUBCELLULAR LOCATION":
            for item in comment.get("subcellularLocations", []) or []:
                value = item.get("location", {}).get("value")
                if value:
                    locations.append(value)
    genes = [item.get("geneName", {}).get("value") for item in entry.get("genes", []) if item.get("geneName")]
    domains = [
        feature.get("description")
        for feature in entry.get("features", [])
        if feature.get("type") in {"Domain", "Region", "Repeat"} and feature.get("description")
    ]
    return {
        "accession": entry.get("primaryAccession"),
        "id": entry.get("uniProtkbId"),
        "name": recommended,
        "genes": genes,
        "organism": entry.get("organism", {}).get("scientificName"),
        "length": entry.get("sequence", {}).get("length"),
        "sequence": entry.get("sequence", {}).get("value"),
        "function": " ".join(functions),
        "locations": locations,
        "domains": domains[:20],
    }


def uniprot_fetch(accession: str) -> dict[str, Any]:
    return compact_uniprot(fetch_json(f"{UNIPROT_BASE}/uniprotkb/{urllib.parse.quote(accession)}.json"))


def uniprot_search(query: str, size: int = 5) -> list[dict[str, Any]]:
    data = fetch_json(
        f"{UNIPROT_BASE}/uniprotkb/search",
        {"query": query, "format": "json", "size": size, "fields": "accession,id,protein_name,organism_name,gene_names,length"},
    )
    return [compact_uniprot(entry) for entry in data.get("results", [])]


def select_uniprot_hit(query: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    accession = ACCESSION_RE.search(query)
    if accession:
        entry = uniprot_fetch(accession.group(0).upper())
        return entry, [entry]
    hits = uniprot_search(query, size=5)
    if not hits:
        return {}, []
    human = next((hit for hit in hits if hit.get("organism") == "Homo sapiens"), None)
    top = human or hits[0]
    return uniprot_fetch(str(top["accession"])), hits


def aa_class(aa: str) -> str:
    if aa in POSITIVE:
        return "positive"
    if aa in NEGATIVE:
        return "negative"
    if aa in HYDROPHOBIC:
        return "hydrophobic"
    if aa in POLAR:
        return "polar_uncharged"
    return "other"


def annotate_change(position: int, wt: str, mt: str, indel: bool = False) -> dict[str, Any]:
    if indel:
        return {"position": position, "wt": wt, "mt": mt, "category": "indel", "severity": "high", "flags": ["length-changing"]}
    flags: list[str] = []
    if mt == "*":
        flags.append("introduces stop codon")
    if aa_class(wt) != aa_class(mt):
        flags.append(f"class change: {aa_class(wt)} -> {aa_class(mt)}")
    if (wt in POSITIVE and mt in NEGATIVE) or (wt in NEGATIVE and mt in POSITIVE):
        flags.append("charge reversal")
    if wt == "P" or mt == "P":
        flags.append("proline involved")
    if wt == "G" or mt == "G":
        flags.append("glycine involved")
    if (wt == "C") ^ (mt == "C"):
        flags.append("cysteine gain/loss")
    if (wt in AROMATIC) ^ (mt in AROMATIC):
        flags.append("aromatic gain/loss")
    severity = "high" if any(flag in {"introduces stop codon", "charge reversal", "cysteine gain/loss"} for flag in flags) else ("medium" if flags else "low")
    return {"position": position, "wt": wt, "mt": mt, "category": "missense", "severity": severity, "flags": flags}


def mutation_diff(wild_type: str, mutant: str | None = None, mutation: str | None = None) -> dict[str, Any]:
    wt = clean_sequence(wild_type)
    if not wt:
        raise ValueError("缺少野生型蛋白质序列。")
    if mutation:
        match = HGVS_RE.fullmatch(mutation.strip())
        if not match:
            raise ValueError("无法解析突变，请使用如 p.R175H 的格式。")
        expected, position_text, changed = match.groups()
        position = int(position_text)
        if position > len(wt):
            raise ValueError(f"突变位置 {position} 超出序列长度 {len(wt)}。")
        actual = wt[position - 1]
        if actual != expected.upper():
            raise ValueError(f"位置 {position} 的野生型是 {actual}，与输入的 {expected.upper()} 不一致。")
        mt = wt[: position - 1] + changed.upper() + wt[position:]
        differences = [annotate_change(position, actual, changed.upper())]
    elif mutant:
        mt = clean_sequence(mutant)
        differences = [annotate_change(i + 1, a, b) for i, (a, b) in enumerate(zip(wt, mt)) if a != b]
        if len(wt) != len(mt):
            n = min(len(wt), len(mt))
            differences.append(annotate_change(n + 1, wt[n:] or "-", mt[n:] or "-", indel=True))
    else:
        raise ValueError("请提供突变型序列或 HGVS 蛋白质变异。")
    overall = "likely impactful" if any(item["severity"] == "high" for item in differences) else ("possibly impactful" if any(item["severity"] == "medium" for item in differences) else "low heuristic impact")
    return {"wt_length": len(wt), "mt_length": len(mt), "n_differences": len(differences), "differences": differences, "overall_assessment": overall}


def pubmed_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    search = fetch_json(f"{PUBMED_BASE}/esearch.fcgi", {"db": "pubmed", "term": query, "retmode": "json", "retmax": limit})
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    summary = fetch_json(f"{PUBMED_BASE}/esummary.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    result = summary.get("result", {})
    return [{"pmid": pmid, "title": result.get(pmid, {}).get("title", ""), "journal": result.get(pmid, {}).get("source", ""), "date": result.get(pmid, {}).get("pubdate", "")} for pmid in ids]


def protein_analysis(query: str, attachment: str = "") -> dict[str, Any]:
    sequence_input = attachment or (query if looks_like_sequence_input(query) else "")
    records = fasta_records(sequence_input) if sequence_input else []
    if re.search(r"(?:^|\n)\s*>", sequence_input) and not records:
        raise ValueError("FASTA 标题后未找到序列。请将序列放在标题下一行；本次未执行 BLAST。")
    if records:
        validation_error = protein_sequence_validation_error(records[0].get("raw_sequence", ""))
        if validation_error:
            raise ValueError(validation_error)
    evidence: list[dict[str, Any]] = []
    if records:
        evidence.append({"source": "local sequence analysis", "record": records[0]["name"], "stats": protein_stats(records[0]["sequence"])})
    accession = ACCESSION_RE.search(query)
    lookup = accession.group(0) if records and accession else ("" if records else query.strip())
    if not lookup and not records:
        raise ValueError("请输入 UniProt accession、基因/蛋白名称，或上传 FASTA。")
    entry: dict[str, Any] = {}
    hits: list[dict[str, Any]] = []
    if lookup and (ACCESSION_RE.search(lookup) or len(lookup.split()) <= 12):
        entry, hits = select_uniprot_hit(lookup)
        evidence.append({"source": "UniProt REST API", "query": lookup, "hits": hits})
    blast: dict[str, Any] = {}
    if records and len(records[0]["sequence"]) >= 20:
        blast = ncbi_blastp(f">{records[0]['name']}\n{records[0]['sequence']}")
        evidence.append({"source": "NCBI BLAST", "rid": blast.get("rid"), "result": blast})
        if not entry and blast.get("hits"):
            top_accession = str(blast["hits"][0].get("accession") or "").split(".")[0]
            if top_accession:
                try:
                    entry = uniprot_fetch(top_accession)
                except Exception:
                    pass
    return {"kind": "protein", "entry": entry, "sequence": records[0] if records else {}, "blast": blast, "evidence": evidence}


def extract_labeled_sequence(text: str, label: str) -> str:
    match = re.search(rf"(?:^|\n)\s*(?:{label})\s*[:：]\s*([^\n]+(?:\n(?!\s*[A-Za-z]+\s*[:：]).+)*)", text, re.IGNORECASE)
    return clean_sequence(match.group(1)) if match else ""


def mutation_assessment(query: str, attachment: str = "") -> dict[str, Any]:
    combined = f"{query}\n{attachment}".strip()
    records = fasta_records(attachment)
    wt = extract_labeled_sequence(combined, r"WT|wild[_ -]?type|野生型")
    mt = extract_labeled_sequence(combined, r"MT|mutant|突变型")
    if len(records) >= 2:
        wt, mt = records[0]["sequence"], records[1]["sequence"]
    mutation_match = HGVS_RE.search(query)
    mutation = mutation_match.group(0) if mutation_match else None
    gene_match = re.search(r"(?:gene|基因)\s*[:：]?\s*([A-Za-z0-9-]{2,20})", query, re.IGNORECASE)
    if not gene_match and mutation_match:
        prefix = query[: mutation_match.start()]
        candidates = re.findall(r"\b[A-Z][A-Z0-9-]{1,15}\b", prefix)
        gene = candidates[-1] if candidates else ""
    else:
        gene = gene_match.group(1) if gene_match else ""
    protein: dict[str, Any] = {}
    if not wt and gene:
        protein, _hits = select_uniprot_hit(f"gene_exact:{gene} AND organism_id:9606")
        wt = str(protein.get("sequence") or "")
    diff = mutation_diff(wt, mutant=mt or None, mutation=mutation) if wt and (mt or mutation) else {}
    literature = pubmed_search(" ".join(part for part in [gene, mutation, "mutation"] if part), limit=5) if gene and mutation else []
    return {
        "kind": "mutation",
        "gene": gene,
        "mutation": mutation,
        "protein": protein,
        "diff": diff,
        "literature": literature,
        "limitations": ["理化性质规则不是临床致病性分类。", "临床解释需要 ClinVar/ACMG 等证据的人工复核。"],
    }


def markdown_report(result: dict[str, Any]) -> str:
    if result["kind"] == "protein":
        entry = result.get("entry") or {}
        sequence = result.get("sequence") or {}
        stats = protein_stats(sequence.get("sequence", "")) if sequence else {}
        lines = ["# 蛋白质分析", ""]
        if entry:
            lines += ["## UniProt 实际查询结果", "", f"- Accession：{entry.get('accession')}", f"- Entry：{entry.get('id')}", f"- 名称：{entry.get('name')}", f"- 基因：{', '.join(entry.get('genes') or []) or '未提供'}", f"- 物种：{entry.get('organism')}", f"- 长度：{entry.get('length')}", f"- 功能：{entry.get('function') or '未提供'}", f"- 亚细胞定位：{', '.join(entry.get('locations') or []) or '未提供'}", f"- 结构域/区域：{'; '.join(entry.get('domains') or []) or '未提供'}", ""]
        if stats:
            lines += ["## FASTA 基础统计", "", f"- 记录：{sequence.get('name')}", f"- 长度：{stats['length']} aa", f"- 疏水残基比例：{stats['hydrophobic_percent']}%", f"- 带电残基比例：{stats['charged_percent']}%", f"- 异常字符：{', '.join(stats['invalid']) or '无'}", ""]
        blast = result.get("blast") or {}
        if blast:
            lines += ["## NCBI BLAST 实际查询结果", "", f"- RID：{blast.get('rid')}", f"- 状态：{blast.get('status')}", f"- 程序/数据库：{blast.get('program', 'blastp')} / {blast.get('database', 'swissprot')}", ""]
            for index, hit in enumerate(blast.get("hits", []), start=1):
                lines += [f"### 命中 {index}", "", f"- Accession：{hit.get('accession')}", f"- 描述：{hit.get('title')}", f"- E-value：{hit.get('evalue')}", f"- Identity：{hit.get('identity_percent')}%", f"- Query coverage：{hit.get('query_coverage_percent')}%", f"- NCBI：{hit.get('url')}", ""]
        if sequence and not entry and not blast.get("hits"):
            lines += ["> FASTA 已完成基础统计，但 BLAST 尚未返回可用命中，不能确定蛋白身份。", ""]
        return "\n".join(lines)
    diff = result.get("diff") or {}
    protein = result.get("protein") or {}
    lines = ["# 突变评估", "", "## 标准化输入", "", f"- 基因：{result.get('gene') or '未提供'}", f"- 变异：{result.get('mutation') or '使用 WT/MT 序列比较'}", f"- UniProt：{protein.get('accession') or '未解析'}", ""]
    if diff:
        lines += ["## 真实序列差异计算", "", f"- WT 长度：{diff.get('wt_length')}", f"- MT 长度：{diff.get('mt_length')}", f"- 差异数：{diff.get('n_differences')}", f"- 规则评估：{diff.get('overall_assessment')}", ""]
        for item in diff.get("differences", []):
            lines.append(f"- {item['position']}: {item['wt']} → {item['mt']}；{item['severity']}；{', '.join(item['flags']) or '无特殊理化标记'}")
        lines.append("")
    if result.get("literature"):
        lines += ["## PubMed 实际检索结果", ""]
        for item in result["literature"]:
            lines.append(f"- PMID {item['pmid']}：{item['title']} ({item['journal']}, {item['date']})")
        lines.append("")
    lines += ["## 证据边界", "", "- 以上序列差异为确定性计算。", "- 理化性质分级只是启发式结果，不等于致病性。", "- 临床解释前需要人工核验 ClinVar、ACMG、群体频率和功能实验。"]
    return "\n".join(lines)


def execute(tool: str, query: str, attachment: str = "") -> dict[str, Any]:
    if tool == "protein_analysis":
        result = protein_analysis(query, attachment)
    elif tool == "mutation_assessment":
        result = mutation_assessment(query, attachment)
    else:
        raise ValueError("不支持的生物学工具。")
    return {"ok": True, "mode": "tool", "result": result, "content": markdown_report(result)}
