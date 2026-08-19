from __future__ import annotations

import json
from pathlib import Path

import pytest

from isms_pii_toolkit.legal_api.client import LegalApiClient, LegalApiError
from isms_pii_toolkit.legal_api.matcher import control_law_references, match_interpretation
from isms_pii_toolkit.legal_api.models import InterpretationRecord, LawReference
from isms_pii_toolkit.legal_api.parser import (
    LegalXmlError,
    extract_law_references,
    normalize_law_go_kr_url,
    parse_interpretation_detail,
    parse_interpretation_list,
    parse_law_document,
)
from isms_pii_toolkit.legal_api.repository import LegalRepository
from isms_pii_toolkit.legal_api.service import control_legal_basis, search_interpretations

LIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ExpcSearch>
  <resultCode>00</resultCode><resultMsg>success</resultMsg>
  <expc id="1">
    <법령해석례일련번호>313107</법령해석례일련번호>
    <안건명><![CDATA[개인정보 수집 출처 통지 관련]]></안건명>
    <안건번호>23-0001</안건번호><질의기관명>개인정보보호위원회</질의기관명>
    <회신기관명>법제처</회신기관명><회신일자>2023.08.10</회신일자>
    <법령해석례상세링크>/DRF/lawService.do?target=expc&amp;ID=313107&amp;type=HTML</법령해석례상세링크>
  </expc>
</ExpcSearch>""".encode()

DETAIL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<LawService>
  <법령해석례일련번호>313107</법령해석례일련번호>
  <안건명>개인정보 수집 출처 통지 관련</안건명>
  <안건번호>23-0001</안건번호>
  <질의요지>정보주체 이외로부터 개인정보를 수집한 경우 통지가 필요한지?</질의요지>
  <회답>법정 요건에 해당하는 경우 통지하여야 합니다.</회답>
  <이유>개인정보 보호법 제20조의 문언과 취지를 고려해야 합니다.</이유>
  <관련법령>개인정보 보호법 제20조</관련법령>
</LawService>""".encode()

LAW_XML = """<법령><조문><조문단위><조문번호>17</조문번호><조문가지번호>0</조문가지번호>
<조문시행일자>20250313</조문시행일자><조문제목>개인정보의 제공</조문제목>
<조문내용>제17조(개인정보의 제공) ① 개인정보처리자는 다음 각 호의 어느 하나에 해당되는 경우 개인정보를 제3자에게 제공할 수 있다.</조문내용>
<항><항내용>① 정보주체의 동의를 받은 경우</항내용></항></조문단위></조문></법령>""".encode()

ADMRUL_XML = """<AdmRulService><조문내용>제4조(내부 관리계획의 수립ㆍ시행 및 점검) ① 개인정보처리자는 내부 관리계획을 수립ㆍ시행하여야 한다.</조문내용></AdmRulService>""".encode()


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self, _limit: int) -> bytes:
        return self.payload


def test_client_uses_https_and_keeps_key_server_side() -> None:
    requested: list[str] = []

    def opener(request, *, timeout):
        assert timeout == 3
        requested.append(request.full_url)
        return FakeResponse(LIST_XML)

    client = LegalApiClient(
        service_key="decoded secret+/=",
        timeout_seconds=3,
        max_retries=1,
        opener=opener,
    )
    records = client.search_interpretations("개인정보 보호법")
    assert records[0].serial_number == "313107"
    assert requested[0].startswith("https://apis.data.go.kr/1170000/law/expcSearchList.do?")
    assert "decoded secret" not in requested[0]


def test_client_decodes_portal_encoded_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "secret%2Bvalue%2F%3D")
    client = LegalApiClient.from_env()
    assert client.service_key == "secret+value/="


def test_client_rejects_non_https_base_url() -> None:
    client = LegalApiClient(service_key="secret", base_url="http://example.test", max_retries=1)
    with pytest.raises(LegalApiError):
        client.search_interpretations("개인정보")


def test_parse_interpretation_list_and_detail() -> None:
    records = parse_interpretation_list(LIST_XML)
    assert len(records) == 1
    assert records[0].interpretation_id == "expc-313107"
    assert records[0].response_date == "2023-08-10"
    assert records[0].original_url == (
        "https://www.law.go.kr/DRF/lawService.do?target=expc&ID=313107&type=HTML"
    )

    detail = parse_interpretation_detail(DETAIL_XML, fallback=records[0])
    assert detail.answer == "법정 요건에 해당하는 경우 통지하여야 합니다."
    assert detail.related_laws == [LawReference("개인정보 보호법", "제20조")]


def test_parse_and_store_law_documents(tmp_path: Path) -> None:
    metadata = {
        "documentId": "011357", "name": "개인정보 보호법", "documentType": "법률",
        "effectiveDate": "2025-03-13", "promulgationDate": "2025-03-13",
        "ministry": "개인정보보호위원회", "currentStatus": "현행",
        "detailUrl": "https://www.law.go.kr/DRF/lawService.do?target=law&type=XML",
    }
    law = parse_law_document(LAW_XML, metadata=metadata, target="law")
    assert law.articles[0].article == "제17조"
    assert law.articles[0].title == "개인정보의 제공"
    assert "정보주체의 동의" in law.articles[0].text
    repository = LegalRepository(tmp_path / "legal_kb")
    repository.save_law(law)
    stored = repository.find_article("개인정보보호법", "제17조")
    assert stored is not None and stored[1] == law.articles[0]

    admrul = parse_law_document(ADMRUL_XML, metadata={**metadata, "documentId": "73493", "name": "개인정보의 안전성 확보조치 기준"}, target="admrul")
    assert admrul.articles[0].article == "제4조"


def test_parser_rejects_entities_and_untrusted_detail_hosts() -> None:
    with pytest.raises(LegalXmlError):
        parse_interpretation_list(b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><x>&y;</x>')
    with pytest.raises(LegalXmlError):
        normalize_law_go_kr_url("https://evil.example/steal")


def test_extract_law_references_handles_multiple_articles() -> None:
    refs = extract_law_references("개인정보 보호법 제16조, 제19조 및 제20조")
    assert refs == [
        LawReference("개인정보 보호법", "제16조"),
        LawReference("개인정보 보호법", "제19조"),
        LawReference("개인정보 보호법", "제20조"),
    ]


def test_management_control_without_explicit_law_gets_certification_basis() -> None:
    refs = control_law_references({"controlId": "1.1.1", "areaId": "1", "laws": []})
    assert refs == [LawReference("정보통신망 이용촉진 및 정보보호 등에 관한 법률", "제47조")]


def test_repository_save_search_and_safe_id(tmp_path: Path) -> None:
    repository = LegalRepository(tmp_path / "legal_kb")
    record = parse_interpretation_detail(DETAIL_XML, fallback=parse_interpretation_list(LIST_XML)[0])
    repository.save(record)

    assert repository.get("expc-313107") == record
    assert repository.search(query="수집 출처") == [record]
    assert repository.search(law_name="개인정보 보호법", article="제20조") == [record]
    with pytest.raises(ValueError):
        repository.get("../../secret")


def test_matcher_and_control_legal_basis(tmp_path: Path) -> None:
    repository = LegalRepository(tmp_path / "legal_kb")
    record = parse_interpretation_detail(DETAIL_XML, fallback=parse_interpretation_list(LIST_XML)[0])
    repository.save(record)
    repository.save_law(parse_law_document(LAW_XML, metadata={
        "documentId": "011357", "name": "개인정보 보호법", "documentType": "법률",
        "effectiveDate": "2025-03-13", "promulgationDate": "2025-03-13",
        "ministry": "개인정보보호위원회", "currentStatus": "현행",
        "detailUrl": "https://www.law.go.kr/DRF/lawService.do?target=law&type=XML",
    }, target="law"))
    control = {
        "title": "개인정보 간접수집",
        "laws": ["개인정보 보호법 제16조, 제19조, 제20조"],
    }
    assert LawReference("개인정보 보호법", "제20조") in control_law_references(control)
    match = match_interpretation(control, record)
    assert match is not None
    assert match.score >= 50

    payload = control_legal_basis("3.1.5", repository=repository)
    assert payload is not None
    assert any(law["article"] == "제20조" for law in payload["laws"])
    assert payload["requirementSummary"]
    assert len(payload["auditQuestions"]) >= 3
    assert payload["evidenceExamples"]
    assert payload["defectExamples"]
    assert payload["guideSource"]["document"]
    assert payload["interpretationDataStatus"] in {"NOT_CONFIGURED", "UNKNOWN"}
    assert payload["interpretationCorpusSize"] == 1
    article_20 = next(law for law in payload["laws"] if law["article"] == "제20조")
    assert article_20["articleTitle"] == "정보주체 이외로부터 수집한 개인정보의 수집 출처 등 통지"
    assert article_20["sourceUrl"].startswith("https://www.law.go.kr/")
    assert payload["interpretations"][0]["interpretationId"] == "expc-313107"
    payload_331 = control_legal_basis("3.3.1", repository=repository)
    assert payload_331 is not None
    article_17 = next(law for law in payload_331["laws"] if law["article"] == "제17조")
    assert article_17["articleTitle"] == "개인정보의 제공"
    assert "정보주체의 동의" in article_17["articleText"]


def test_matcher_rejects_same_law_with_different_article() -> None:
    control = {"title": "개인정보 제3자 제공", "laws": ["개인정보 보호법 제17조"]}
    record = InterpretationRecord(
        interpretation_id="expc-unrelated",
        serial_number="1",
        title="개인정보 열람 요구",
        related_laws=[LawReference("개인정보 보호법", "제35조")],
    )
    assert match_interpretation(control, record) is None


def test_search_service_empty_repository(tmp_path: Path) -> None:
    payload = search_interpretations(repository=LegalRepository(tmp_path / "legal_kb"))
    assert payload["total"] == 0
    assert payload["items"] == []


def test_pipc_kisa_casebook_is_connected_without_impersonating_moleg() -> None:
    payload = control_legal_basis("3.3.4")
    assert payload is not None
    assert payload["casebookCorpusSize"] == 30
    assert len(payload["casebookExamples"]) == 1
    case = payload["casebookExamples"][0]
    assert case["title"] == "개인정보의 국외 이전"
    assert case["source"]["sourceType"] == "PIPC_KISA_CASEBOOK"
    assert case["source"]["provider"] == "개인정보보호위원회·한국인터넷진흥원"
    assert case["question"] and case["answer"] and case["reasoning"]
    assert "현행 법령" in case["warning"]
