# 국가법령정보 Open API 연동

## 목적

법령 Open API는 자가진단 판정을 대신하지 않는다. ISMS-P 통제의 관련 법령을 구조화하고, 법령해석례의 질의·회답·이유를 연결하여 판정 설명과 추가 확인 질문을 보강한다.

## 데이터 흐름

```text
공공데이터포털 expcSearchList.do (목록)
  → 국가법령정보센터 상세 XML
  → legal_api.parser 정규화
  → data/legal_kb/interpretations/*.json
  → 통제의 법령·조문과 자동 매핑
  → FastAPI 내부 조회 API
  → 자가진단 화면의 법적 근거 영역
```

외부 API는 사용자의 웹 요청 중 호출하지 않는다. 별도 동기화 명령이 로컬 지식베이스를 갱신하고, 웹은 마지막 정상 데이터를 제공한다.

## 설정

첨부 이미지나 문서에 노출된 인증키는 폐기하고 새 키를 발급한다. 공공데이터포털의 디코딩 인증키를 `.env`에만 기록한다.

```dotenv
DATA_GO_KR_SERVICE_KEY=
LAW_OPEN_API_BASE_URL=https://apis.data.go.kr/1170000/law
LAW_API_TIMEOUT_SECONDS=10
LAW_API_MAX_RETRIES=3
```

`.env`는 Git에 커밋하지 않는다. 프런트엔드 JavaScript, HTML, 요청 로그, 오류 응답에 인증키를 포함하지 않는다.

## 동기화

개발 환경에서 목록과 상세 본문을 수집한다.

```bash
source .venv/bin/activate
python scripts/sync_legal_interpretations.py --query "개인정보 보호법" --pages 1 --rows 20
```

목록만 확인하는 방법:

```bash
python scripts/sync_legal_interpretations.py --query "개인정보 보호법" --list-only --dry-run
```

초기에는 개인정보 보호법과 정보통신망법 관련 검색어만 사용한다. 일일 트래픽을 전부 소모하는 전체 상세 수집은 피한다.

## 내부 API

- `GET /legal/interpretations?q=검색어`
- `GET /legal/interpretations/{interpretation_id}`
- `GET /controls/{control_id}/legal-basis`

통제별 응답은 관련 조문, 매핑된 법령해석례, 매핑 점수·이유, 현행성 경고, 면책문구를 포함한다.

## 자동 매핑

현재 매핑은 다음 정보를 사용한다.

1. 법령명과 조문 정확 일치
2. 법령명 일치
3. 통제 제목 핵심어와 안건명·질의요지 일치
4. 현행성 상태에 따른 감점

자동 매핑은 `AUTO_SUGGESTED` 후보이다. 행정해석의 사실관계와 통제 요구사항을 사람이 확인한 뒤 `HUMAN_CONFIRMED`로 승격하는 관리자 기능은 다음 단계에서 추가한다.

## 보안 경계

- HTTPS 외부 API만 허용한다.
- 상세 링크는 `law.go.kr` 도메인만 허용한다.
- XML 응답은 2MB로 제한한다.
- `DOCTYPE`과 `ENTITY`가 포함된 XML을 거부한다.
- 외부 API 오류가 발생해도 기존 로컬 데이터는 유지한다.
- 원문 HTML을 `innerHTML`로 직접 넣지 않고 화면에서 이스케이프한다.
- 원문 링크는 `https://law.go.kr` 또는 `https://www.law.go.kr`만 허용한다.

## 현재 한계와 다음 단계

- 법령 개정 이력과 해석일을 자동 비교하는 현행성 판정은 아직 보수적으로 `UNKNOWN`을 사용한다.
- 법령해석례가 실제 통제와 관련되는지 관리자가 승인·거절하는 화면이 필요하다.
- 개인정보보호위원회 의결문, 분쟁조정, 판례는 별도 출처 유형으로 확장해야 한다.
- 데이터가 수천 건을 넘으면 JSON 저장소를 SQLite FTS5 또는 PostgreSQL로 이전한다.
