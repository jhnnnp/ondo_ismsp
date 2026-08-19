# ISMS-P Self-Assessment

ISMS-P 101개 통제를 기반으로 조직 프로파일, 인증 범위, 점검 체크리스트, 증적 후보와 미충족 위험을 검토하는 자가진단 프로젝트입니다.

개인정보 탐지·마스킹·암호화 데모는 이 저장소에서 제거했으며 별도 `pii-demo` 프로젝트로 분리했습니다.

## 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
isms-p-api
```

브라우저에서 `http://127.0.0.1:8000/`을 엽니다. API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

## 주요 기능

- 조직 규모·업종·클라우드·위탁·개인정보 처리 특성 기반 프로파일링
- ISMS-P 101개 통제 체크리스트 및 N/A 판정
- 인증 범위 검토 초안과 우선 점검 통제 추천
- 체크 미충족 → 문제 → 영향의 인과 분석
- 사례집·공식 안내서·법령 근거 연결
- 결정론적 분석 결과를 바탕으로 한 선택형 AI 보고서
- 브라우저 로컬 저장 기반 세션 관리

AI는 보고서 문장화만 담당하며 준비도, 갭, N/A, 인과와 통제 판정을 변경하지 않습니다. 실제 인증 심사나 증적 검증을 대체하지 않습니다.

## 주요 API

| 경로 | 설명 |
| --- | --- |
| `GET /` | ISMS-P 자가진단 화면 |
| `GET /health` | 서비스 상태 |
| `GET /controls` | 통제 검색 |
| `GET /controls/checklist` | 체크리스트 조회 |
| `POST /controls/bootstrap` | 초기 진단 구성 |
| `POST /controls/analyze` | 규칙 기반 진단 분석 |
| `POST /controls/report` | 재판정 후 전체 보고서 생성 |
| `POST /controls/scope/draft` | 인증 범위 검토 초안 |
| `GET /controls/{controlId}/legal-basis` | 통제별 법적 근거 |
| `GET /legal/interpretations` | 로컬 법령해석 검색 |

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `PII_TOOLKIT_API_HOST` | `127.0.0.1` | API 바인드 호스트 |
| `PII_TOOLKIT_API_PORT` | `8000` | API 포트 |
| `PII_TOOLKIT_ENABLE_DEMO` | `1` | HTML UI 제공 여부 |
| `OPENAI_API_KEY` / `PII_TOOLKIT_OPENAI_API_KEY` | 없음 | 선택형 AI 보고서 키 |
| `PII_TOOLKIT_OPENAI_MODEL` | `gpt-4o-mini` | 보고서 모델 |
| `DATA_GO_KR_SERVICE_KEY` | 없음 | 법령 데이터 동기화 키 |

기존 `PII_TOOLKIT_*` 접두사는 현재 설정 호환성을 위해 유지합니다.

## 테스트

```bash
pytest
node --test tests/js/control_map_pure.test.mjs
```

법령 연동 구조는 [docs/LEGAL_API_INTEGRATION.md](docs/LEGAL_API_INTEGRATION.md), 문서 근거 로직은 [docs/DOCUMENT_LOGIC_ROADMAP.md](docs/DOCUMENT_LOGIC_ROADMAP.md)를 참고하세요.

## 한계

- 실제 인증 심사, 법률 자문 또는 증적의 진위 검증 도구가 아닙니다.
- 사용자 인증·권한 관리·감사로그·멀티테넌시는 포함하지 않습니다.
- 범위 초안은 담당자와 경영진의 자산·데이터 흐름·위탁 증적 확인이 필요합니다.

MIT License
