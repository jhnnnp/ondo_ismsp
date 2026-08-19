# 프론트엔드 모듈화 계획

## 목표

`control_map.html`에 결합된 마크업, 스타일, 상태, 화면 전환, API 호출을 단계적으로 분리한다.
React나 별도 번들러는 먼저 도입하지 않는다. 각 단계는 기존 `/controls/map` 동작과
브라우저 저장 데이터를 유지해야 한다.

## 변경하지 않는 제품 불변식

- 제품 본체는 ISMS-P 자가진단이다.
- 환경 설정 뒤 이번 세션 우선 통제 5~10개를 진단한다.
- 진단 상태는 `아직 모름 / 미이행 / 부분 이행 / 이행`이다.
- 전체 진행 `M/N`과 대기열을 유지한다.
- 기존 `localStorage` 키와 `/controls/*` API 계약을 유지한다.

## 단계

### 1. 물리적 자산 분리

상태: 완료

- `control_map.html`: 문서 구조와 접근성 마크업만 유지
- `control_map.css`: 모든 화면 스타일
- `control_map.js`: 현재 동작을 그대로 보존한 JavaScript
- FastAPI에서 CSS와 JavaScript를 명시적인 경로로 제공
- Python 패키지에 HTML, CSS, JavaScript를 포함

완료 기준:

- HTML에 인라인 `<style>`과 인라인 `<script>`가 없다.
- `/controls/map`과 두 자산 경로가 정상 응답한다.
- JavaScript 구문 검사가 통과한다.

### 2. 공통 기반 모듈 분리

상태: 완료

대상:

- [완료] `core/dom.js`: API 요청, DOM 조회, escape, toast
- [완료] `core/state.js`: 단일 상태 객체
- [완료] `core/constants.js`: 라벨, 저장 키, 화면 카피
- [완료] `core/storage.js`: 진단, 체크, 환경 설정 저장 및 복원
- [완료] `app.js`: 네이티브 ES Module 진입점
- [완료] `core/router.js`: 초기화, 화면 라우팅, 전역 이벤트 연결

규칙:

- 브라우저 네이티브 ES Module을 사용한다.
- 전역 `window`에 기능 함수를 노출하지 않는다.
- 상태 변경은 기능별 action 함수를 통해서만 수행한다.
- 빌드 단계는 추가하지 않는다.

완료 기준:

- 공통 모듈 간 순환 import가 없다.
- 저장 데이터와 API 요청 payload가 분리 전과 동일하다.
- 환경 → 자가진단 → 인증 화면 전환이 유지된다.

### 3. 기능 모듈 분리

상태: 완료

대상:

- [완료] `features/profile/view.js`: 환경 설정 DOM과 프로필 렌더링 분리
- [완료] `features/assessment/model.js`: 진단 상태와 대분류 계산 분리
- [완료] `features/assessment/filter.js`: 전체 통제 필터와 개수 계산 분리
- [완료] `features/assessment/view.js`: 툴바, 통제 행, 대분류 탐색 렌더링 분리
- [완료] `features/assessment/actions.js`: 체크, N/A, 저장 payload 상태 변경
- [완료] `features/assessment/controller.js`: 목록 로딩, 렌더 오케스트레이션, 상세 이동
- [완료] `features/session/model.js`: 이번 세션 우선 통제와 대기열 계산 분리
- [완료] `features/session/view.js`: 우선 진단 카드, 진행률, 대기열 렌더링 분리
- [완료] 프로필 적용 후 항상 숨겨지던 보조 질문 패널과 렌더링 코드 제거
- [완료] `features/analysis/utils.js`: 분석 포맷과 통제 위험 표현 분리
- [완료] `features/analysis/problems.js`: 개별·복합 문제 필터와 렌더링 분리
- [완료] `features/analysis/overlaps.js`: 겹치는 문제 테마·심각도 필터·카드 렌더링 분리
- [완료] `features/analysis/gaps.js`: 갭 클러스터·검색·필터·상세 탭 렌더링 분리
- [완료] `features/analysis/presentation.js`: 로딩·리포트·이력·섹션 전환 분리
- [완료] `features/analysis/summary.js`: 준비도·상태·권고 결과 조합 분리
- [완료] `features/analysis/controller.js`: 분석 API 요청·서술 오버레이·상태 갱신 분리
- [완료] `features/certification/controller.js`: 인증 준비 가이드 조회 분리
- [완료] `features/certification/view.js`: 인증 단계·의무·범위·준비 항목 렌더링 분리

경계:

- 기능 모듈은 다른 기능의 DOM을 직접 수정하지 않는다.
- 기능 간 연결은 state action과 명시적인 render 함수로 처리한다.
- 대분류 탐색 상태와 통제 목록 필터 상태를 별도로 유지한다.

완료 기준:

- 한 기능 수정이 다른 화면의 렌더 함수를 호출하지 않는다.
- 각 파일은 한 기능 책임만 가진다.
- `control_map.js` 단일 파일이 제거된다.

### 4. 스타일 분리

상태: 완료

대상:

- [완료] `styles/tokens.css`: 색상, 간격, 타이포그래피
- [완료] `styles/layout.css`: 공통 레이아웃과 반응형 규칙
- [완료] `styles/profile.css`
- [완료] `styles/assessment.css`
- [완료] `styles/analysis.css`
- [완료] `styles/certification.css`

완료 기준:

- 화면별 스타일 변경이 다른 화면에 영향을 주지 않는다.
- 중복 selector와 사용하지 않는 selector를 제거한다.
- 모바일 및 데스크톱 핵심 흐름을 시각 검증한다.

### 5. 검증 체계

상태: 완료

- FastAPI 테스트: HTML 및 정적 자산 응답, 콘텐츠 타입, 데모 비활성화
- JavaScript: `node --check`와 순수 함수 단위 테스트
- 브라우저 핵심 흐름:
  1. 환경 설정 적용
  2. 자가진단 자동 진입
  3. 진단 상태 변경 후 `M/N` 증가
  4. 대기열 재정렬
  5. 상세 보기와 대분류 필터 동작
  6. 새로고침 후 상태 복원

최종 검증 결과:

- Python 전체 테스트: 171개 통과
- JavaScript 구문 검사: 전체 모듈 통과
- `node:test`: 모델, 분석 포맷, 리포트 중복 제거 순수 함수 6개 통과
- wheel: 라우터, 진단 action/controller, 6개 CSS 모듈 포함 확인
- 브라우저: 환경 적용, 자동 진입, 상태 변경, 대기열 재정렬, 상세/대분류 이동,
  새로고침 복원, 인증 통제 이동 확인
- 반응형: 데스크톱과 390px 모바일에서 환경/자가진단/인증 화면 가로 오버플로 없음
- 분석 UX: 새로고침과 진단 변경 시 자동 분석 없음, 명시적 갱신 1회,
  확인 목록 단일 카드의 확인·무시·진행 저장 확인

## React 재검토 기준

다음 조건 중 둘 이상이 확인될 때만 React/Vite 전환을 별도 결정한다.

- 독립 화면과 재사용 컴포넌트가 계속 증가한다.
- 프론트엔드 개발자가 여러 명으로 늘어난다.
- Storybook, 컴포넌트 단위 시각 테스트가 필요하다.
- 클라이언트 라우팅과 복잡한 비동기 캐시가 필요하다.

React 도입 여부와 관계없이 2~4단계의 기능 경계와 상태 모델은 그대로 재사용한다.
