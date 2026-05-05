from open_rosalind.orchestrator.router import detect_intent
from open_rosalind.tools import sequence as seq_tool
from open_rosalind.tools import mutation as mut_tool


def test_intent_accession():
    assert detect_intent("P38398").skill == "uniprot_lookup"


def test_intent_literature():
    assert detect_intent("find papers on CRISPR base editing").skill == "literature_search"


def test_intent_fasta():
    fasta = ">x\nACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
    assert detect_intent(fasta).skill == "sequence_basic_analysis"


def test_intent_default_uniprot():
    assert detect_intent("what is BRCA1").skill == "uniprot_lookup"


def test_sequence_analyze_dna():
    r = seq_tool.analyze("ACGTACGTACGT")
    rec = r["records"][0]
    assert rec["type"] == "dna"
    assert rec["length"] == 12
    assert rec["gc_percent"] == 50.0


def test_sequence_analyze_protein():
    r = seq_tool.analyze("MVKVGVNGFGRIGRLVTRA")
    rec = r["records"][0]
    assert rec["type"] == "protein"
    assert "approx_molecular_weight_da" in rec


def test_sequence_analyze_singleline_fasta():
    r = seq_tool.analyze(">demo MVKVGVNGFGRIGRLVTRA")
    rec = r["records"][0]
    assert rec["header"] == "demo"
    assert rec["length"] == 19
    assert rec["type"] == "protein"


def test_dna_translation_and_revcomp():
    r = seq_tool.analyze("ATGCGTACGTAA")
    rec = r["records"][0]
    assert rec["type"] == "dna"
    assert rec["translation_preview"].startswith("MRT")
    assert rec["reverse_complement_preview"].startswith("TTACGT")


def test_sequence_align_pairwise():
    r = seq_tool.align_pairwise("ACGT", "ACCT")
    assert r["mode"] == "global"
    assert r["score"] >= 3.0
    assert r["identity"] == 0.75
    assert r["alignment"]["sequence_a"] == "ACGT"
    assert r["alignment"]["sequence_b"] == "ACCT"


def test_mutation_hgvs_apply():
    wt = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD"
    out = mut_tool.diff_sequences(wild_type=wt, mutation="p.R175H")
    assert out["n_differences"] == 1
    d = out["differences"][0]
    assert d["wt"] == "R" and d["mt"] == "H" and d["position"] == 175
    flags_text = " ".join(d["flags"]).lower()
    assert "aromatic" in flags_text  # R→H gains aromaticity


def test_router_mutation_block():
    text = "WT: MEEPQSDR\nMT: p.R8H"
    intent = detect_intent(text)
    assert intent.skill == "mutation_effect"
    assert intent.payload.get("mutation") == "p.R8H"


def test_intent_classifier_triggers_on_embedded_sequence():
    from open_rosalind.orchestrator.intent_classifier import (
        needs_llm_classification, has_embedded_sequence, looks_like_natural_language,
    )
    assert needs_llm_classification("Translate this DNA: ATGGCCAAATTAA")
    assert needs_llm_classification("How long is human insulin (P01308)?") is False
    assert needs_llm_classification("ATGCGTACGTAA") is False
    assert needs_llm_classification("What is BRCA1?") is False
    assert has_embedded_sequence("Translate this: ATGGCCAAATTAA")
    assert looks_like_natural_language("What is the function of this protein?")


def test_skills_registry_shape():
    from open_rosalind.skills import SKILLS, list_cards, get_skill
    assert set(SKILLS) == {
        "sequence_basic_analysis", "uniprot_lookup",
        "literature_search", "mutation_effect",
    }
    cards = list_cards()
    assert len(cards) == 4
    for c in cards:
        assert c["name"] and c["category"] and c["safety_level"]
        assert isinstance(c["tools_used"], list)
    sk = get_skill("uniprot_lookup")
    assert sk is not None
    full = sk.to_full()
    assert "input_schema" in full and "output_schema" in full and full["examples"]


def test_skill_registry_backward_compat():
    from open_rosalind.skills import SKILL_REGISTRY
    assert callable(SKILL_REGISTRY["sequence_basic_analysis"])
    assert callable(SKILL_REGISTRY["mutation_effect"])


def test_session_store_write_read():
    import tempfile
    from open_rosalind.session import SessionStore
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(tmpdir)
        store.write_event("test-123", "start", user_input="hello")
        store.write_event("test-123", "skill_call", skill="uniprot_lookup", payload={"query": "P38398"})
        store.write_event("test-123", "skill_result", evidence={"entry": {"name": "BRCA1"}})
        store.write_event("test-123", "summary", text="BRCA1 is...")
        events = store.read_session("test-123")
        assert len(events) == 4
        assert events[0].kind == "start"
        assert events[1].kind == "skill_call"
        assert events[2].kind == "skill_result"
        assert events[3].kind == "summary"
        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test-123"
        assert sessions[0]["user_input"] == "hello"
        last_ev = store.get_last_evidence("test-123")
        assert last_ev == {"entry": {"name": "BRCA1"}}
