from __future__ import annotations

import asyncio
import os
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from . import __version__
from .control_assessment import analyze_assessment, bootstrap_assessment, certification_guide, list_checklist_controls
from .control_graph import (
    dashboard_stats,
    filter_controls,
    find_control,
    find_scenario,
    graph_for_scenario,
    list_evidences,
    list_scenarios,
    trace_scenario,
)
from .access_pass import (
    ADMIN_COOKIE_NAME,
    ADMIN_SESSION_HOURS,
    COOKIE_NAME,
    AccessPassError,
    access_pass_required,
    admin_configured,
    admin_console_path,
    clear_admin_session,
    create_admin_session,
    delete_pass,
    delete_passes,
    issue_pass_record,
    list_passes,
    pass_summary,
    public_status,
    register_pass,
    remaining_seconds,
    reserve_admin_login,
    resolve_admin_session,
    resolve_session,
    revoke_pass,
    update_pass_note,
    verify_admin_password,
    workspace_pass_required,
)
from .llm_report_guard import LlmReportGuard, LlmReportLimitError
from .organization_profile import normalize_organization_profile
from .scope_drafting import build_scope_draft
from .causal_retrieve import preview_check_impact
from .schemas import (
    AssessRequest,
    AssessResponse,
    BootstrapAssessmentResponse,
    ChecklistResponse,
    ChecklistControlResponse,
    CertificationGuideResponse,
    ControlLegalBasisResponse,
    InstitutionGuideResponse,
    LegalInterpretationDetailResponse,
    LegalInterpretationListResponse,
    SimpleCertHintsResponse,
    ControlGraphResponse,
    ControlListResponse,
    ControlResponse,
    DashboardResponse,
    EvidenceListResponse,
    AccessPassRegisterRequest,
    AccessPassStatusResponse,
    AdminLoginRequest,
    AdminPassBulkDeleteRequest,
    AdminPassBulkDeleteResponse,
    AdminPassIssueRequest,
    AdminPassIssueResponse,
    AdminPassListResponse,
    AdminPassNoteRequest,
    AdminPassRecordResponse,
    AdminSessionResponse,
    HealthResponse,
    OrganizationProfileRequest,
    OrganizationProfileResponse,
    PreviewCheckFindingResponse,
    PreviewCheckImpactRequest,
    PreviewCheckImpactResponse,
    ReportDocumentRequest,
    ReportRewriteRequest,
    ReportRewriteResponse,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioTraceResponse,
    ScopeDraftRequest,
    ScopeDraftResponse,
)

_DEMO_DIR = Path(__file__).resolve().parent
_CONTROL_MAP_ASSET_DIR = _DEMO_DIR / "web" / "control_map"
_LANDING_ASSET_DIR = _DEMO_DIR / "web" / "landing"
_ADMIN_ASSET_DIR = _DEMO_DIR / "web" / "admin"
_BRAND_ASSET_DIR = _DEMO_DIR / "web" / "brand"
_WEB_ASSET_MEDIA_TYPES = {
    ".css": "text/css",
    ".js": "text/javascript",
    ".webp": "image/webp",
}
_BRAND_ASSETS = {
    "favicon.ico": "image/x-icon",
    "favicon.svg": "image/svg+xml",
    "apple-touch-icon.png": "image/png",
}


def _demo_enabled() -> bool:
    return os.getenv("PII_TOOLKIT_ENABLE_DEMO", "1").lower() not in ("0", "false", "no")


def _api_docs_enabled() -> bool:
    explicit = os.getenv("PII_TOOLKIT_ENABLE_DOCS")
    if explicit is not None and explicit.strip() != "":
        return explicit.lower() not in ("0", "false", "no")
    return os.getenv("VERCEL_ENV", "").lower() != "production"


def _load_control_map_html() -> str:
    return (_DEMO_DIR / "control_map.html").read_text(encoding="utf-8")


def _load_landing_html() -> str:
    return (_DEMO_DIR / "landing.html").read_text(encoding="utf-8")


def _load_admin_html(base_path: str) -> str:
    html = (_DEMO_DIR / "admin.html").read_text(encoding="utf-8")
    return html.replace("__ADMIN_BASE__", base_path.rstrip("/"))


def _load_web_asset(base_dir: Path, asset_path: str) -> tuple[str | bytes, str]:
    relative_path = Path(asset_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise FileNotFoundError(asset_path)
    media_type = _WEB_ASSET_MEDIA_TYPES.get(relative_path.suffix)
    full_path = base_dir / relative_path
    if media_type is None or not full_path.is_file():
        raise FileNotFoundError(asset_path)
    if relative_path.suffix in {".css", ".js"}:
        return full_path.read_text(encoding="utf-8"), media_type
    return full_path.read_bytes(), media_type


def _load_control_map_asset(asset_path: str) -> tuple[str | bytes, str]:
    return _load_web_asset(_CONTROL_MAP_ASSET_DIR, asset_path)


def _load_landing_asset(asset_path: str) -> tuple[str | bytes, str]:
    return _load_web_asset(_LANDING_ASSET_DIR, asset_path)


def _load_admin_asset(asset_path: str) -> tuple[str | bytes, str]:
    return _load_web_asset(_ADMIN_ASSET_DIR, asset_path)


def _load_brand_asset(filename: str) -> tuple[bytes, str]:
    media_type = _BRAND_ASSETS.get(filename)
    if media_type is None:
        raise FileNotFoundError(filename)
    full_path = _BRAND_ASSET_DIR / filename
    if not full_path.is_file() or full_path.resolve().parent != _BRAND_ASSET_DIR.resolve():
        raise FileNotFoundError(filename)
    return full_path.read_bytes(), media_type


def _brand_response(filename: str) -> Response:
    try:
        content, media_type = _load_brand_asset(filename)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Brand asset not found.") from error
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "no-store"})


CONTROL_MAP_HTML = _load_control_map_html()
_WORKSPACE_BASE = "/workspace"
_CONTROL_MAP_PAGES = frozenset({
    "dashboard",
    "scope",
    "assessment",
    "results",
    "evidence",
    "report",
    "sessions",
})


_WORKSPACE_ROBOTS_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}

_ROBOTS_TXT = """User-agent: *
Allow: /
Disallow: /workspace/
Disallow: /controls/
Disallow: /access/
Disallow: /docs
Disallow: /redoc
Disallow: /openapi.json
"""


def _workspace_html(http_request: Request | None = None) -> HTMLResponse:
    if not _demo_enabled():
        raise HTTPException(status_code=404, detail="Demo UI is disabled.")
    html = _load_control_map_html()
    unlocked = not workspace_pass_required()
    if http_request is not None and not unlocked:
        unlocked = resolve_session(http_request.cookies.get(COOKIE_NAME)) is not None
    if unlocked:
        html = html.replace('<html lang="ko" class="is-workspace-locked">', '<html lang="ko">', 1)
    return HTMLResponse(content=html, headers=dict(_WORKSPACE_ROBOTS_HEADERS))


def _workspace_location(page: str | None = None) -> str:
    if not page or page == "sessions":
        return _WORKSPACE_BASE
    if page == "dashboard":
        return f"{_WORKSPACE_BASE}/assessment"
    return f"{_WORKSPACE_BASE}/{page}"


def _legacy_workspace_redirect(page: str | None = None) -> RedirectResponse:
    if not _demo_enabled():
        raise HTTPException(status_code=404, detail="Demo UI is disabled.")
    if page and page not in _CONTROL_MAP_PAGES:
        raise HTTPException(status_code=404, detail="Control map page not found.")
    return RedirectResponse(_workspace_location(page), status_code=308)


def _build_report_docx(title: str, content: str) -> bytes:
    """Build a small, standards-compliant DOCX without adding a runtime dependency."""
    paragraphs: list[str] = []
    for raw_line in content.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            paragraphs.append("<w:p/>")
            continue
        style = ""
        text = line
        if line.startswith("### "):
            style, text = '<w:pPr><w:pStyle w:val="Heading3"/></w:pPr>', line[4:]
        elif line.startswith("## "):
            style, text = '<w:pPr><w:pStyle w:val="Heading2"/></w:pPr>', line[3:]
        elif line.startswith("# "):
            style, text = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>', line[2:]
        elif line.startswith(("- ", "* ")):
            style, text = '<w:pPr><w:pStyle w:val="ListParagraph"/></w:pPr>', f"• {line[2:]}"
        paragraphs.append(
            f'<w:p>{style}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        )

    title_xml = escape(title)
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>{title_xml}</w:t></w:r></w:p>
<w:p><w:r><w:rPr><w:color w:val="64748B"/></w:rPr><w:t>자가진단 참고자료 · 인증 심사를 대체하지 않습니다.</w:t></w:r></w:p>
{''.join(paragraphs)}
<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>
</w:body></w:document>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    document_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:eastAsia="Malgun Gothic"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="0F766E"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/></w:pPr></w:style>
</w:styles>'''
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/_rels/document.xml.rels", document_relationships)
    return output.getvalue()


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _cookie_secure(http_request: Request) -> bool:
    return http_request.url.scheme == "https"


def _apply_access_cookie(response: Response, http_request: Request, session_token: str, record: dict[str, object]) -> None:
    remaining = remaining_seconds(str(record.get("expiresAt") or ""))
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(http_request),
        max_age=max(1, remaining),
        path="/",
    )


def _admin_cookie_path() -> str:
    slug = admin_console_path()
    return f"/{slug}" if slug else "/unavailable"


def _admin_response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "X-Robots-Tag": "noindex, nofollow",
    }


def _apply_admin_cookie(response: Response, http_request: Request, session_token: str) -> None:
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(http_request),
        max_age=ADMIN_SESSION_HOURS * 3600,
        path=_admin_cookie_path(),
    )


def _clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(key=ADMIN_COOKIE_NAME, path=_admin_cookie_path())


def _enforce_admin(http_request: Request) -> None:
    if not admin_configured():
        raise HTTPException(status_code=503, detail="관리자 비밀번호가 설정되지 않았습니다.")
    if resolve_admin_session(http_request.cookies.get(ADMIN_COOKIE_NAME)) is None:
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")


def _enforce_ai_access_pass(http_request: Request) -> None:
    if not access_pass_required():
        return
    record = resolve_session(http_request.cookies.get(COOKIE_NAME))
    if record is None:
        raise HTTPException(status_code=403, detail="AI 보고서 사용권이 필요합니다.")


def _analyze_control_request(request: AssessRequest) -> dict[str, object]:
    """Recompute trusted structured facts from checklist inputs only."""
    profile = (
        request.organization_profile.model_dump(by_alias=True)
        if request.organization_profile is not None
        else None
    )
    scope_review = (
        request.scope_review.model_dump(by_alias=True)
        if request.scope_review is not None
        else None
    )
    return analyze_assessment(
        dict(request.assessments),
        request.scenario_id,
        request.control_checks,
        profile,
        scope_review,
        verbalize=False,
        domain_checks=request.domain_checks,
        verbalize_consistency=False,
        quest_checks=request.quest_checks,
        input_confidence=(
            {k: str(v) for k, v in request.input_confidence.items()}
            if request.input_confidence
            else None
        ),
        evidence_slots=(
            {
                slot_id: meta.model_dump(by_alias=True)
                for slot_id, meta in request.evidence_slots.items()
            }
            if request.evidence_slots
            else None
        ),
        verbalize_max_gaps=12,
        verbalize_include_quests=False,
        view=request.view,
        session_bundle_mode=request.session_bundle_mode,
    )


def create_app() -> FastAPI:
    docs_enabled = _api_docs_enabled()
    application = FastAPI(
        title="ISMS-P Self-Assessment API",
        description="ISMS-P 자가진단과 통제 분석 기능을 제공합니다.",
        version=__version__,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    report_guard = LlmReportGuard(
        requests_per_minute=_bounded_env_int(
            "PII_TOOLKIT_LLM_REPORTS_PER_MINUTE",
            6,
            1,
            60,
        ),
        max_concurrent=_bounded_env_int(
            "PII_TOOLKIT_LLM_REPORT_MAX_CONCURRENT",
            2,
            1,
            8,
        ),
    )

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home_page() -> HTMLResponse:
        if not _demo_enabled():
            raise HTTPException(status_code=404, detail="Demo UI is disabled.")
        return HTMLResponse(content=_load_landing_html(), headers={"Cache-Control": "no-store"})

    @application.get("/robots.txt", include_in_schema=False)
    def robots_txt() -> PlainTextResponse:
        return PlainTextResponse(_ROBOTS_TXT, media_type="text/plain; charset=utf-8")

    @application.get("/favicon.ico", include_in_schema=False)
    def favicon_ico() -> Response:
        return _brand_response("favicon.ico")

    @application.get("/favicon.svg", include_in_schema=False)
    def favicon_svg() -> Response:
        return _brand_response("favicon.svg")

    @application.get("/apple-touch-icon.png", include_in_schema=False)
    def apple_touch_icon() -> Response:
        return _brand_response("apple-touch-icon.png")

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @application.get("/access/status", response_model=AccessPassStatusResponse, tags=["access"])
    def access_status(http_request: Request) -> AccessPassStatusResponse:
        record = resolve_session(http_request.cookies.get(COOKIE_NAME))
        return AccessPassStatusResponse(**public_status(record))

    @application.post("/access/register", response_model=AccessPassStatusResponse, tags=["access"])
    def access_register(
        payload: AccessPassRegisterRequest,
        http_request: Request,
        response: Response,
    ) -> AccessPassStatusResponse:
        try:
            session_token, record = register_pass(payload.token)
        except AccessPassError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error
        _apply_access_cookie(response, http_request, session_token, record)
        return AccessPassStatusResponse(**public_status(record))

    admin_slug = admin_console_path()
    if admin_slug:
        admin_prefix = f"/{admin_slug}"

        @application.get(admin_prefix, response_class=HTMLResponse, include_in_schema=False)
        def admin_page() -> HTMLResponse:
            return HTMLResponse(
                content=_load_admin_html(admin_prefix),
                headers=_admin_response_headers(),
            )

        @application.get(f"{admin_prefix}/assets/{{asset_path:path}}", include_in_schema=False)
        def admin_asset(asset_path: str) -> Response:
            try:
                content, media_type = _load_admin_asset(asset_path)
            except FileNotFoundError as error:
                raise HTTPException(status_code=404, detail="Admin asset not found.") from error
            return Response(
                content=content,
                media_type=media_type,
                headers=_admin_response_headers(),
            )

        @application.get(f"{admin_prefix}/session", response_model=AdminSessionResponse, include_in_schema=False)
        def admin_session(http_request: Request) -> AdminSessionResponse:
            authenticated = resolve_admin_session(http_request.cookies.get(ADMIN_COOKIE_NAME)) is not None
            return AdminSessionResponse(configured=admin_configured(), authenticated=authenticated)

        @application.post(f"{admin_prefix}/login", response_model=AdminSessionResponse, include_in_schema=False)
        def admin_login(
            payload: AdminLoginRequest,
            http_request: Request,
            response: Response,
        ) -> AdminSessionResponse:
            client_id = http_request.client.host if http_request.client is not None else "unknown"
            try:
                reserve_admin_login(client_id)
            except AccessPassError as error:
                raise HTTPException(status_code=error.status_code, detail=str(error)) from error
            if not admin_configured():
                raise HTTPException(status_code=503, detail="관리자 비밀번호가 설정되지 않았습니다.")
            if not verify_admin_password(payload.password):
                raise HTTPException(status_code=401, detail="관리자 비밀번호가 올바르지 않습니다.")
            session_token = create_admin_session()
            _apply_admin_cookie(response, http_request, session_token)
            return AdminSessionResponse(configured=True, authenticated=True)

        @application.post(f"{admin_prefix}/logout", response_model=AdminSessionResponse, include_in_schema=False)
        def admin_logout(http_request: Request, response: Response) -> AdminSessionResponse:
            clear_admin_session(http_request.cookies.get(ADMIN_COOKIE_NAME))
            _clear_admin_cookie(response)
            return AdminSessionResponse(configured=admin_configured(), authenticated=False)

        @application.get(f"{admin_prefix}/passes", response_model=AdminPassListResponse, include_in_schema=False)
        def admin_list_passes(http_request: Request) -> AdminPassListResponse:
            _enforce_admin(http_request)
            return AdminPassListResponse(
                passes=[AdminPassRecordResponse(**item) for item in list_passes()]
            )

        @application.post(f"{admin_prefix}/passes", response_model=AdminPassIssueResponse, include_in_schema=False)
        def admin_issue_pass(
            payload: AdminPassIssueRequest,
            http_request: Request,
        ) -> AdminPassIssueResponse:
            _enforce_admin(http_request)
            token, record = issue_pass_record(
                duration_days=payload.duration_days,
                note=payload.note,
                kind=payload.kind,
            )
            return AdminPassIssueResponse(token=token, record=AdminPassRecordResponse(**pass_summary(record)))

        @application.post(
            f"{admin_prefix}/passes/bulk-delete",
            response_model=AdminPassBulkDeleteResponse,
            include_in_schema=False,
        )
        def admin_bulk_delete_passes(
            payload: AdminPassBulkDeleteRequest,
            http_request: Request,
        ) -> AdminPassBulkDeleteResponse:
            _enforce_admin(http_request)
            try:
                deleted = delete_passes(pass_ids=payload.ids, delete_all=payload.delete_all)
            except AccessPassError as error:
                raise HTTPException(status_code=error.status_code, detail=str(error)) from error
            return AdminPassBulkDeleteResponse(deleted=deleted)

        @application.patch(
            f"{admin_prefix}/passes/{{pass_id}}",
            response_model=AdminPassRecordResponse,
            include_in_schema=False,
        )
        def admin_update_pass_note(
            pass_id: str,
            payload: AdminPassNoteRequest,
            http_request: Request,
        ) -> AdminPassRecordResponse:
            _enforce_admin(http_request)
            try:
                record = update_pass_note(pass_id, payload.note)
            except AccessPassError as error:
                raise HTTPException(status_code=error.status_code, detail=str(error)) from error
            return AdminPassRecordResponse(**pass_summary(record))

        @application.post(
            f"{admin_prefix}/passes/{{pass_id}}/revoke",
            response_model=AdminPassRecordResponse,
            include_in_schema=False,
        )
        def admin_revoke_pass(pass_id: str, http_request: Request) -> AdminPassRecordResponse:
            _enforce_admin(http_request)
            try:
                record = revoke_pass(pass_id)
            except AccessPassError as error:
                raise HTTPException(status_code=error.status_code, detail=str(error)) from error
            return AdminPassRecordResponse(**pass_summary(record))

        @application.delete(
            f"{admin_prefix}/passes/{{pass_id}}",
            response_model=AdminPassRecordResponse,
            include_in_schema=False,
        )
        def admin_delete_pass(pass_id: str, http_request: Request) -> AdminPassRecordResponse:
            _enforce_admin(http_request)
            try:
                record = delete_pass(pass_id)
            except AccessPassError as error:
                raise HTTPException(status_code=error.status_code, detail=str(error)) from error
            return AdminPassRecordResponse(**pass_summary(record))

    @application.get("/workspace", response_class=HTMLResponse, include_in_schema=False)
    def workspace_page(http_request: Request) -> HTMLResponse:
        return _workspace_html(http_request)

    @application.get("/workspace/{page}", response_class=HTMLResponse, include_in_schema=False)
    def workspace_subpage(page: str, http_request: Request) -> HTMLResponse:
        if page not in _CONTROL_MAP_PAGES:
            raise HTTPException(status_code=404, detail="Control map page not found.")
        if page in {"dashboard", "sessions"}:
            return RedirectResponse(_workspace_location(page), status_code=308)
        return _workspace_html(http_request)

    @application.get("/controls/map", include_in_schema=False)
    def control_map_page() -> RedirectResponse:
        return _legacy_workspace_redirect()

    @application.get("/controls/map/assets/{asset_path:path}", include_in_schema=False)
    def control_map_asset(asset_path: str) -> Response:
        if not _demo_enabled():
            raise HTTPException(status_code=404, detail="Demo UI is disabled.")
        try:
            content, media_type = _load_control_map_asset(asset_path)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Control map asset not found.") from error
        return Response(
            content=content,
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/controls/map/{page}", include_in_schema=False)
    def control_map_workspace_page(page: str) -> RedirectResponse:
        return _legacy_workspace_redirect(page)

    @application.get("/landing/assets/{asset_path:path}", include_in_schema=False)
    def landing_asset(asset_path: str) -> Response:
        if not _demo_enabled():
            raise HTTPException(status_code=404, detail="Demo UI is disabled.")
        try:
            content, media_type = _load_landing_asset(asset_path)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Landing asset not found.") from error
        return Response(
            content=content,
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/controls/certification-guide", response_model=CertificationGuideResponse, tags=["isms-p-controls"])
    def control_certification_guide() -> CertificationGuideResponse:
        return CertificationGuideResponse(**certification_guide())

    @application.get("/controls/institution-guide", response_model=InstitutionGuideResponse, tags=["isms-p-controls"])
    def control_institution_guide() -> InstitutionGuideResponse:
        from .official_kb import institution_public_payload

        return InstitutionGuideResponse(**institution_public_payload())

    @application.get("/controls/simple-cert-hints", response_model=SimpleCertHintsResponse, tags=["isms-p-controls"])
    def control_simple_cert_hints(
        headcount_band: str = "1-50",
        uses_cloud: bool = True,
        has_on_prem_facility: bool = False,
    ) -> SimpleCertHintsResponse:
        from .official_kb import simple_cert_hints
        from .organization_profile import OrganizationContext

        ctx = OrganizationContext(
            headcount_band=headcount_band if headcount_band in {"1-50", "51-300", "301+"} else "1-50",
            industry="technology",
            pii_volume="low",
            uses_cloud=uses_cloud,
            has_on_prem_facility=has_on_prem_facility,
        )
        return SimpleCertHintsResponse(**simple_cert_hints(ctx.tags))

    @application.get("/controls/checklist", response_model=ChecklistResponse, tags=["isms-p-controls"])
    def control_checklist() -> ChecklistResponse:
        items = list_checklist_controls()
        return ChecklistResponse(
            total=len(items),
            controls=[ChecklistControlResponse(**item) for item in items],
        )

    @application.get("/controls/bootstrap-assessment", response_model=BootstrapAssessmentResponse, tags=["isms-p-controls"])
    def control_bootstrap_assessment() -> BootstrapAssessmentResponse:
        return BootstrapAssessmentResponse(assessments=bootstrap_assessment())  # type: ignore[arg-type]

    @application.post("/controls/analyze", response_model=AssessResponse, tags=["isms-p-controls"])
    def control_analyze(request: AssessRequest) -> AssessResponse:
        return AssessResponse(**_analyze_control_request(request))

    @application.post(
        "/controls/report",
        response_model=AssessResponse,
        tags=["isms-p-controls"],
        summary="Generate an AI report from server-recomputed checklist facts",
    )
    async def control_report(request: AssessRequest, http_request: Request) -> AssessResponse:
        """Write the report only after recomputing immutable facts on the server."""
        from .detail_narrative import apply_detail_narratives
        from .verbalize_inference import apply_verbalizing

        _enforce_ai_access_pass(http_request)
        client_id = http_request.client.host if http_request.client is not None else "unknown"
        try:
            async with report_guard.limit(client_id):
                structured = await asyncio.to_thread(_analyze_control_request, request)
                merged = await asyncio.to_thread(
                    apply_verbalizing,
                    structured,
                    enabled=True,
                    consistency_samples=1,
                    max_gaps=12,
                    include_quests=False,
                    report_only=True,
                )
                # 종합 보고서 후: 공식 안내서 청크 기반 상세 해설(빨간 상세 영역)
                merged = await asyncio.to_thread(apply_detail_narratives, merged, enabled=True)
        except LlmReportLimitError as error:
            raise HTTPException(status_code=429, detail=str(error)) from error
        return AssessResponse(**merged)

    @application.post(
        "/controls/report/docx",
        tags=["isms-p-controls"],
        summary="Export an edited assessment report as a Word document",
    )
    def control_report_docx(request: ReportDocumentRequest) -> Response:
        document = _build_report_docx(request.title, request.content)
        return Response(
            content=document,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="isms-p-report.docx"'},
        )

    @application.post(
        "/controls/report/rewrite",
        response_model=ReportRewriteResponse,
        tags=["isms-p-controls"],
        summary="Suggest a wording-only rewrite for selected report text",
    )
    async def control_report_rewrite(
        request: ReportRewriteRequest,
        http_request: Request,
    ) -> ReportRewriteResponse:
        from .report_rewrite import rewrite_report_passage

        _enforce_ai_access_pass(http_request)
        client_id = http_request.client.host if http_request.client is not None else "unknown"
        try:
            async with report_guard.limit(client_id):
                result = await asyncio.to_thread(
                    rewrite_report_passage,
                    request.text,
                    request.mode,
                )
        except LlmReportLimitError as error:
            raise HTTPException(status_code=429, detail=str(error)) from error
        return ReportRewriteResponse(**result)

    @application.post(
        "/controls/preview-check-impact",
        response_model=PreviewCheckImpactResponse,
        tags=["isms-p-controls"],
    )
    def control_preview_check_impact(request: PreviewCheckImpactRequest) -> PreviewCheckImpactResponse:
        profile = (
            request.organization_profile.model_dump(by_alias=True)
            if request.organization_profile is not None
            else None
        )
        context = normalize_organization_profile(profile)
        try:
            raw = preview_check_impact(
                dict(request.assessments),
                request.control_checks,
                control_id=request.control_id,
                check_key=request.check_key,
                checked=request.checked,
                organization_context=context,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def _slim(rows: list[dict[str, object]]) -> list[PreviewCheckFindingResponse]:
            slimmed: list[PreviewCheckFindingResponse] = []
            for row in rows:
                slimmed.append(
                    PreviewCheckFindingResponse(
                        findingId=str(row.get("findingId") or ""),
                        controlId=str(row.get("controlId") or ""),
                        checklistItemId=str(row.get("checklistItemId") or ""),
                        checklistItem=str(row.get("checklistItem") or ""),
                        problem=str(row.get("problem") or ((row.get("problems") or [""])[0])),
                        causalStatement=str(row.get("causalStatement") or ""),
                    )
                )
            return slimmed

        return PreviewCheckImpactResponse(
            controlId=str(raw["controlId"]),
            checkKey=str(raw["checkKey"]),
            checkLabel=str(raw["checkLabel"]),
            checked=bool(raw["checked"]),
            beforeCount=int(raw["beforeCount"]),
            afterCount=int(raw["afterCount"]),
            resolvedFindings=_slim(list(raw["resolvedFindings"])),
            remainingFindings=_slim(list(raw["remainingFindings"])),
            introducedFindings=_slim(list(raw["introducedFindings"])),
            summary=str(raw["summary"]),
        )

    @application.post(
        "/controls/organization-profile/validate",
        response_model=OrganizationProfileResponse,
        tags=["isms-p-controls"],
    )
    def validate_organization_profile(request: OrganizationProfileRequest) -> OrganizationProfileResponse:
        context = normalize_organization_profile(request.model_dump(by_alias=True))
        assert context is not None
        return OrganizationProfileResponse(**context.to_public_dict())

    @application.post(
        "/controls/scope/draft",
        response_model=ScopeDraftResponse,
        tags=["isms-p-controls"],
    )
    def draft_control_scope(request: ScopeDraftRequest) -> ScopeDraftResponse:
        context = normalize_organization_profile(
            request.organization_profile.model_dump(by_alias=True)
        )
        assert context is not None
        review = (
            request.scope_review.model_dump(by_alias=True)
            if request.scope_review is not None
            else None
        )
        return ScopeDraftResponse(**build_scope_draft(context, review))

    @application.get("/controls/dashboard", response_model=DashboardResponse, tags=["isms-p-controls"])
    def control_dashboard() -> DashboardResponse:
        return DashboardResponse(**dashboard_stats())

    @application.get("/controls/trace/{scenario_id}", response_model=ScenarioTraceResponse, tags=["isms-p-controls"])
    def control_trace(scenario_id: str) -> ScenarioTraceResponse:
        payload = trace_scenario(scenario_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return ScenarioTraceResponse(**payload)

    @application.get("/controls", response_model=ControlListResponse, tags=["isms-p-controls"])
    def controls(area: str | None = None, category: str | None = None, q: str | None = None) -> ControlListResponse:
        items = filter_controls(area_id=area, category_id=category, query=q)
        return ControlListResponse(total=len(items), controls=[ControlResponse(**item) for item in items])

    @application.get("/controls/evidences", response_model=EvidenceListResponse, tags=["isms-p-controls"])
    def control_evidences() -> EvidenceListResponse:
        return EvidenceListResponse(evidences=list_evidences())

    @application.get("/controls/scenarios", response_model=ScenarioListResponse, tags=["isms-p-controls"])
    def control_scenarios() -> ScenarioListResponse:
        return ScenarioListResponse(scenarios=list_scenarios())

    @application.get("/controls/scenarios/{scenario_id}", response_model=ScenarioResponse, tags=["isms-p-controls"])
    def control_scenario(scenario_id: str) -> ScenarioResponse:
        scenario = find_scenario(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return ScenarioResponse(**scenario)

    @application.get("/controls/graph", response_model=ControlGraphResponse, tags=["isms-p-controls"])
    def control_graph(scenario: str | None = None) -> ControlGraphResponse:
        payload = graph_for_scenario(scenario_id=scenario)
        if scenario and payload["scenario"] is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return ControlGraphResponse(**payload)

    @application.get(
        "/legal/interpretations",
        response_model=LegalInterpretationListResponse,
        tags=["legal-basis"],
    )
    def legal_interpretations(
        q: str | None = None,
        law_name: str | None = None,
        article: str | None = None,
    ) -> LegalInterpretationListResponse:
        from .legal_api.service import search_interpretations

        return LegalInterpretationListResponse(
            **search_interpretations(query=q, law_name=law_name, article=article)
        )

    @application.get(
        "/legal/interpretations/{interpretation_id}",
        response_model=LegalInterpretationDetailResponse,
        tags=["legal-basis"],
    )
    def legal_interpretation_detail(interpretation_id: str) -> LegalInterpretationDetailResponse:
        from .legal_api.service import interpretation_detail

        try:
            payload = interpretation_detail(interpretation_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        if payload is None:
            raise HTTPException(status_code=404, detail="Legal interpretation not found.")
        return LegalInterpretationDetailResponse(**payload)

    @application.get(
        "/controls/{control_id}/legal-basis",
        response_model=ControlLegalBasisResponse,
        tags=["legal-basis"],
    )
    def control_legal_basis_detail(control_id: str) -> ControlLegalBasisResponse:
        from .legal_api.service import control_legal_basis

        payload = control_legal_basis(control_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Control not found.")
        return ControlLegalBasisResponse(**payload)

    @application.get("/controls/{control_id}", response_model=ControlResponse, tags=["isms-p-controls"])
    def control_detail(control_id: str) -> ControlResponse:
        control = find_control(control_id)
        if control is None:
            raise HTTPException(status_code=404, detail="Control not found.")
        return ControlResponse(**control)

    return application


def _load_project_env() -> None:
    if "pytest" in sys.modules:
        return
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip().strip("'").strip('"')


_load_project_env()
app = create_app()


def run() -> None:
    import uvicorn

    _load_project_env()
    uvicorn.run(
        "isms_pii_toolkit.api:app",
        host=os.getenv("PII_TOOLKIT_API_HOST", "127.0.0.1"),
        port=int(os.getenv("PII_TOOLKIT_API_PORT", "8000")),
    )
