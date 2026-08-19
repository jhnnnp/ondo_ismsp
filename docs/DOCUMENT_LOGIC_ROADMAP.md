# 문서 기반 논리 로드맵

> **상태:** Phase 1–2 완료 + 근거 레벨 정교화 (2026-07-29)  
> **원칙:** 추론은 규칙/KB, 문서별 SSOT를 섞지 않는다. LLM은 facts-only 문장화만.

관련: [`CAUSAL_RETRIEVAL_ROADMAP.md`](CAUSAL_RETRIEVAL_ROADMAP.md), [`STRUCTURED_QUESTIONER.md`](STRUCTURED_QUESTIONER.md), [`OFFICIAL_KB_GAP.md`](OFFICIAL_KB_GAP.md), [`ORGANIC_PROOF_TABLE.md`](ORGANIC_PROOF_TABLE.md)

---

## 엔진 한 문단 (공식)

이 엔진은 ISMS-P 인증기준 안내서·사례집·결함 통계를 기반으로, 개별 통제의 체크리스트 미흡과 시나리오·분류·수동 관계 근거를 결합해 **서로 떨어져 보이는 통제들을 업무 흐름 단위의 유기적 문제로 재구성**합니다. 개별 문제 내용은 문서를 그대로 인용·요약하고, 복합 리스크 문장은 그 문제들을 연결하는 **해석**으로서, 근거 레벨(`casebook_cite` / `category_adjacent` / `interpret`)을 명시적으로 표시합니다.

---

## 1. 문서별 SSOT

| 문서 | 담당 | 금지 |
|------|------|------|
| `사례집.md` | 문제/영향/시나리오 문장 (`problem_kb`) | 연결 이유 창작을 “문서 명시”로 위장 |
| 결함1–5 / KISA CSV | `defectCount` **가중·우선순위**만 (`defect_weights.json`) | A→B 인과 단정 |
| 인증기준 안내서 | 확인사항·증적 예시·분류 인접 (`official_kb`) | 갭 판정 덮어쓰기 |
| 제도 안내서 | 준비/범위 카피 | 통제 판정 |

### 결함 CSV 역할 (고정)

- CSV는 통제별 **빈도/우선순위** 정보를 제공한다.
- 유기적 인과(어떤 통제가 어떤 통제의 ‘원인’인지)는 **사례집 / 분류·시나리오 / 수동 relation**으로 정의한다.
- CSV는 그 연결의 **대응 강도를 조정하는 weight**로만 사용한다.
- 설명 톤: “결함 빈도상 상위이므로 우선 대응” — “통계가 인과를 증명” 금지.

### 근거 레벨 (유기 연결)

| Level | 의미 | 설명 톤 |
|-------|------|---------|
| `casebook_cite` | 사례집 텍스트에 상대 영역 키워드/명시 | “사례집 텍스트 근거가 있는 유기 연결” |
| `category_adjacent` | 인증기준 분류·시나리오 인접 | “분류·시나리오상 같이 보는 게 타당한 연결” |
| `interpret` | 결함우선·수동 해석 | “문서 기반 + 해석형 재구성” (문서 명복합 결함 아님) |

---

## 2. 파이프라인

```text
사례집 → problem_kb 개별문제 → CausalFinding
결함통계 → defect_weights → 갭/퀘스트 우선순위(weight only)
인증기준 → official_kb → 퀘스트/도메인 체크 라벨
관계증거 → relation_evidence.json(groundingLevel) → compounds 재구성
```

유기적 연결은 **근거 레벨을 표시한 엣지**만 복합 문제로 승격한다.  
일반 템플릿(「탐지/차단/추적…」)은 금지한다.  
복합 문장은 “문서가 이미 적시”가 아니라 **개별 문제 조합 + 재구성** 톤을 쓴다.

---

## 3. Phase Done 정의

### Phase 1 — 유기적 연결 증거화

- [x] `scripts/build_evidence_relations.py` → `relation_evidence.json`
- [x] compounds에 `evidenceRefs` / `evidenceGrade` / `groundingLevel` 필수
- [x] 런타임 `synthesize_compounds` / cascade가 근거 태그·근거 레벨 사용
- [x] 고결함 쌍·템플릿 금지 테스트
- [x] 대표 15쌍 증명 표 [`ORGANIC_PROOF_TABLE.md`](ORGANIC_PROOF_TABLE.md)

### Phase 2 — 인증기준 ↔ 체크/퀘스트 정렬

- [x] API에 `officialChecks[]` / `casebookProblems[]` 분리
- [x] 파일럿 quest 라벨 ⊆ official checkQuestions
- [x] cascade/organicAnalysis에 근거 표기

### Phase 3+ (후순위)

- 결함 PNG로 동시발생 행렬 추정 (단일 조직 세션이 아님)
- 전 통제 official overlap 강제
- 저결함 quest handcraft / 증적 GRC / 벡터 RAG
