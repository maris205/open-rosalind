# Reference Verification Skill

Use this skill when the user wants to verify whether references are real, detect fabricated citations, check DOI/PMID consistency, or audit a bibliography before manuscript submission.

## Purpose

Reduce the risk of hallucinated or fabricated references in biomedical writing by separating reference existence checks from model-generated writing.

## Input

Possible inputs:

- reference list
- DOI list
- PMID list
- bibliography copied from a manuscript
- model-generated citations
- claims plus attached references

## Output Structure

Return the answer in Chinese unless the user asks otherwise.

Use this structure:

1. 总体风险结论
2. 逐条参考文献核验表
3. DOI / PMID / 题名 / 作者 / 期刊 / 年份一致性检查
4. 高风险条目
5. 需要人工核验的条目
6. 建议修改或删除的引用
7. 下一步人工核验清单

## Verification Labels

Use these labels:

- Verified: DOI/PMID or trusted metadata source confirms that the reference appears to exist.
- Metadata Mismatch: the identifier exists, but title, year, journal, or author details appear inconsistent.
- Candidate Match: no exact identifier was supplied, but a bibliographic search returns a plausible match.
- Unverified: no reliable match was found.
- Fabrication Risk: the reference may be fabricated or too malformed to trust.

## Rules

- Do not invent references, DOI, PMID, authors, journals, years, or page numbers.
- Do not say a citation is verified unless a DOI, PMID, or external bibliographic source was checked.
- If no external lookup was performed, clearly label the result as format/risk screening only.
- Distinguish reference existence from claim support. A real paper may still fail to support the user's claim.
- For biomedical claims, recommend checking the original paper, not only metadata.
- Treat clinical efficacy, safety, diagnosis, survival, and treatment claims as high-risk even when the reference exists.
- End substantial outputs with the Edu Mode disclaimer.
