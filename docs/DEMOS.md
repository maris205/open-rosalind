# Open-Rosalind MVP1 — Demo Walkthrough

This document captures the four canonical MVP1 demos with **real, end-to-end outputs**
(routing → tool calls → trace → LLM summary). Each demo was generated against a live server
running `google/gemma-4-26b-a4b-it` via OpenRouter.

Reproduce locally:
```bash
python -m open_rosalind.cli serve   # listens on :6006
# then POST to /api/analyze with {"input": <text>, "mode": "auto"}
```

---

## Demo 1: BRCA1 question

- **Skill (auto-detected):** `uniprot_lookup`
- **Trace steps:** 1
- **Session ID:** `20260427-194158-d10943`

### Question

> What is BRCA1 and where is it located in the cell?

### Trace (tool steps)

| # | Tool | Input (truncated) | Output keys |
|---|---|---|---|
| 1 | `uniprot.search` | `{"query": "BRCA1", "size": 5}` | `query`, `count`, `hits` |

### Key evidence

Top UniProt hits (search returned 5 records):

| Accession | ID | Name | Organism | Length |
|---|---|---|---|---|
| `Q8RXD4` | BRCA1_ARATH | Protein BREAST CANCER SUSCEPTIBILITY 1 homolog | *Arabidopsis thaliana* | 941 |
| `Q95153` | BRCA1_CANLF | Breast cancer type 1 susceptibility protein homolog | *Canis lupus familiaris* | 1878 |
| `P38398` | BRCA1_HUMAN | Breast cancer type 1 susceptibility protein | *Homo sapiens* | 1863 |
| `B6VQ60` | BRCA1_CAEEL | Breast cancer type 1 susceptibility protein homolog | *Caenorhabditis elegans* | 612 |
| `P48754` | BRCA1_MOUSE | Breast cancer type 1 susceptibility protein homolog | *Mus musculus* | 1812 |

### LLM summary

### Summary
**BRCA1** (Breast cancer type 1 susceptibility protein) is a critical protein involved in maintaining genomic stability. In humans, it functions as an **E3 ubiquitin-protein ligase** that specifically mediates the formation of 'Lys-6'-linked polyubiquitin chains [UniProt:P38398]. It plays a central role in **DNA repair** by facilitating cellular responses to DNA damage [UniProt:P38398]. The protein often forms a heterodimer with **BARD1** to coordinate various cellular pathways, including ubiquitination and transcriptional regulation [UniProt:P38398].

Regarding its cellular location, the provided evidence indicates that BRCA1 is involved in regulating **centrosomal microtubule nucleation** [UniProt:Q95153, UniProt:P48754], but the specific subcellular compartments (such as the nucleus) are not explicitly detailed in the provided text snippets.

### Evidence
* **Function:** Acts as an E3 ubiquitin-protein ligase and is essential for DNA repair and cellular responses to DNA damage [UniProt:P38398, UniProt:Q95153, UniProt:P48754].
* **Complex Formation:** Forms a heterodimer with BARD1 to regulate DNA damage repair, ubiquitination, and transcriptional regulation [UniProt:P38398, UniProt:Q95153, UniProt:P48754].
* **Cellular Role:** Regulates centrosomal microtubule nucleation [UniProt:Q95153, UniProt:P48754].

---

## Demo 2: CRISPR papers (PubMed)

- **Skill (auto-detected):** `literature_search`
- **Trace steps:** 1
- **Session ID:** `20260427-194208-1bd262`

### Question

> Find recent papers about CRISPR base editing in 2024

### Trace (tool steps)

| # | Tool | Input (truncated) | Output keys |
|---|---|---|---|
| 1 | `pubmed.search` | `{"query": "(CRISPR base editing) AND 2024[dp]", "max_results": 5}` | `query`, `count`, `hits` |

### Key evidence

PubMed hits for cleaned query `(CRISPR base editing) AND 2024[dp]`:

| PMID | Year | Journal | Title |
|---|---|---|---|
| [38308006](https://pubmed.ncbi.nlm.nih.gov/38308006/) | 2024 | Nature reviews. Molecular cell biology | CRISPR technologies for genome, epigenome and transcriptome editing. |
| [38786024](https://pubmed.ncbi.nlm.nih.gov/38786024/) | 2024 | Cells | CRISPR-Based Gene Therapies: From Preclinical to Clinical Treatments. |
| [38909984](https://pubmed.ncbi.nlm.nih.gov/38909984/) | 2024 | Molecules and cells | Genome editing using CRISPR, CAST, and Fanzor systems. |
| [38661449](https://pubmed.ncbi.nlm.nih.gov/38661449/) | 2024 | The New England journal of medicine | Exagamglogene Autotemcel for Severe Sickle Cell Disease. |
| [39426588](https://pubmed.ncbi.nlm.nih.gov/39426588/) | 2024 | Life sciences | CRISPR innovations in tissue engineering and gene editing. |

### LLM summary

Several recent publications from 2024 discuss the landscape of CRISPR technologies, including base editing, within the broader context of genome, epigenome, and transcriptome engineering, as well as clinical applications.

### Summary of 2024 Literature
*   **Broad CRISPR Technologies:** A review in *Nature Reviews Molecular Cell Biology* covers the diverse applications of CRISPR technologies for editing the genome, epigenome, and transcriptome [PMID:38308006].
*   **Clinical Translation:** Research published in *Cells* explores the transition of CRISPR-based gene therapies from preclinical stages to clinical treatments [PMID:38786024].
*   **System Diversity:** Recent work in *Molecules and Cells* discusses genome editing using CRISPR alongside other systems like CAST and Fanzor [PMID:38909984].
*   **Tissue Engineering:** Innovations regarding CRISPR's role in tissue engineering and gene editing were highlighted in *Life Sciences* [PMID:39426588].
*   **Clinical Case Study:** While focused on Exagamglogene Autotemcel for Sickle Cell Disease, this *NEJM* publication represents the current clinical state of CRISPR-based therapeutics [PMID:38661449].

### Evidence
*   **[PMID:38308006]**: Review of CRISPR technologies for genome, epigenome, and transcriptome editing (2024).
*   **[PMID:38786024]**: Overview of CRISPR-based gene therapies from preclinical to clinical (2024).
*   **[PMID:38909984]**: Discussion on CRISPR, CAST, and Fanzor genome editing systems (2024).
*   **[PMID:39426588]**: Review of CRISPR innovations in tissue engineering (2024).
*   **[PMID:38661449]**: Clinical application of CRISPR (Exagamglogene Autotemcel) for Sickle Cell Disease (2024).

---

## Demo 3: FASTA protein analysis

- **Skill (auto-detected):** `sequence_basic_analysis`
- **Trace steps:** 2
- **Session ID:** `20260427-194219-7b5edc`

### Question

```
>demo MVKVGVNGFGRIGRLVTRAAFNSGKVDIVAINDPFIDLNYMVYMFQYDSTHGKFHGTVKAENGKLVINGNPITIFQERDPSKIKWGDAGAEYVVESTGVFTTMEKAGAHLQGGAKRVIISAPSADAPMFVMGVNHEKYDNSLKIISNASCTTNCLAPLAKVIHDNFGIVEGLMTTVHAITATQKTVDGPSGKLWRDGRGALQNIIPASTGAAKAVGKVIPELNGKLTGMAFRVPTANVSVVDLTCRLEKAAKYDDIKKVVKQASEGPLKGILGYTEHQVVSSDFNSDTHSSTFDAGAGIALNDHFVKLISWYDNETGYSNRVVDLMAHMASKE
```

### Trace (tool steps)

| # | Tool | Input (truncated) | Output keys |
|---|---|---|---|
| 1 | `sequence.analyze` | `{"sequence": ">demo MVKVGVNGFGRIGRLVTRAAFNSGKVDIVAINDPFIDLNYMVYMFQYDSTHGKFHGT...` | `records`, `total_records` |
| 2 | `uniprot.search` | `{"query": "MVKVGVNGFGRIGRLVTRAAFNSGKVDIVA", "size": 3}` | `query`, `count`, `hits` |

### Key evidence

Local `sequence.analyze` result:

- type: **protein**
- length: **333** residues
- approx MW: **35,795.69 Da**
- composition (top 8): `V`=32, `G`=32, `A`=32, `K`=25, `I`=22, `T`=22, `S`=21, `D`=20

### LLM summary

The provided sequence "demo" is a protein of 333 amino acids with an approximate molecular weight of 35,795.69 Da.

### Sequence Analysis
*   **Length:** 333 amino acids.
*   **Molecular Weight:** ~35.8 kDa.
*   **Compositional Highlights:** The sequence is highly enriched in Valine (V, 32), Glycine (G, 32), Alanine (A, 32), Lysine (K, 25), Isoleucine (I, 22), Threonine (T, 22), Serine (S, 21), and Aspartic acid (D, 20).
*   **Database Match:** A search of the N-terminal fragment (`MVKVGVNGFGRIGRLVTRAAFNSGKVDIVA`) yielded no direct hits in UniProt.

### Evidence
*   **Sequence Stats:** Length 333, MW 35795.69 Da.
*   **Composition:** High frequency of V, G, and A.
*   **UniProt Search:** 0 hits found for the provided query fragment.

---

## Demo 4: p53 R175H mutation

- **Skill (auto-detected):** `mutation_effect`
- **Trace steps:** 1
- **Session ID:** `20260427-194254-200ca2`

### Question

```
WT: MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD
MT: p.R175H
```

### Trace (tool steps)

| # | Tool | Input (truncated) | Output keys |
|---|---|---|---|
| 1 | `mutation.diff` | `{"wild_type": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDE...` | `wt_length`, `mt_length`, `n_differences`, `differences`, `overall_assessment`, `disclaimer` |

### Key evidence

Rule-based diff: **possibly impactful** (1 difference(s))

| Position | WT | MT | Category | Severity | Flags |
|---|---|---|---|---|---|
| 175 | `R` | `H` | missense | medium | aromatic gain/loss |

> _Rule-based heuristic only — not a substitute for PolyPhen/SIFT/AlphaMissense._

### LLM summary

The mutation **p.R175H** is a missense mutation located at position 175 of the protein sequence.

### Summary
The substitution of Arginine (R) with Histidine (H) at position 175 is classified as a **medium severity** mutation. The change involves an **aromatic gain/loss** characteristic. Based on rule-based heuristic analysis, the mutation is assessed as **possibly impactful** to the protein's function.

### Evidence
* **Mutation Type:** Missense (R $\rightarrow$ H) at position 175.
* **Severity:** Medium.
* **Chemical Property Change:** Aromatic gain/loss.
* **Heuristic Assessment:** Possibly impactful.

---

## What this MVP1 proves

- **Tool-first, LLM-second**: every fact in the summaries traces back to a UniProt / PubMed /
  local-compute call. The model only synthesizes; it never invents IDs or numbers.
- **Trace as a first-class output**: every response carries a structured `trace_steps` array
  *and* a JSONL file at `traces/<session>.jsonl` — replay the trace, reproduce the run.
- **Model-agnostic agent**: swapping `configs/default.yaml` (e.g. to a local OmniGene-4 vLLM
  endpoint) requires zero changes to the skills, tools, or routing.

See `open-rosalind.md` for the full design doc and `gpt2.md` for the MVP1 scope rationale.
