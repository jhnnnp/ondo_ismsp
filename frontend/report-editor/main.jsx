import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import CharacterCount from "@tiptap/extension-character-count";
import { Markdown } from "@tiptap/markdown";
import { diffWordsWithSpace } from "diff";
import "./report-editor.css";

const HISTORY_LIMIT = 20;
const MODE_LABELS = {
  diagnostic_intro: "진단 배경·목적",
  result_interpretation: "진단 결과 해석",
  improvement_plan: "개선계획 작성",
  executive_brief: "경영진 요약",
};
const historyKey = (bridge) => `isms-p-report-history:${bridge.dataset.historyKey || "default"}`;

function readHistory(bridge) {
  try { return JSON.parse(localStorage.getItem(historyKey(bridge)) || "[]"); } catch (_) { return []; }
}

function writeBridge(bridge, value, edited = true) {
  bridge.value = value;
  bridge.dataset.userEdited = edited ? "1" : "0";
  bridge.dispatchEvent(new Event("input", { bubbles: true }));
}

function DiffText({ before, after, side }) {
  const parts = useMemo(() => diffWordsWithSpace(before, after), [before, after]);
  return <p className="react-report-diff-text">{parts.map((part, index) => {
    if ((side === "before" && part.added) || (side === "after" && part.removed)) return null;
    const className = part.added ? "is-added" : part.removed ? "is-removed" : "";
    return <span className={className} key={`${index}-${part.value}`}>{part.value}</span>;
  })}</p>;
}

function ReportEditor() {
  const bridge = document.getElementById("executiveReportStream");
  const [count, setCount] = useState(bridge?.value.length || 0);
  const [mode, setMode] = useState("result_interpretation");
  const [busy, setBusy] = useState(false);
  const [proposal, setProposal] = useState(null);
  const [history, setHistory] = useState(() => bridge ? readHistory(bridge) : []);
  const saveTimer = useRef(null);

  const syncValue = useCallback((current, edited = true) => {
    if (!bridge || !current) return "";
    const markdown = current.getMarkdown();
    writeBridge(bridge, markdown, edited);
    setCount(current.storage.characterCount.characters());
    return markdown;
  }, [bridge]);

  const editor = useEditor({
    extensions: [StarterKit, Markdown, CharacterCount],
    content: bridge?.value || "",
    contentType: "markdown",
    editorProps: { attributes: { class: "react-report-prosemirror", "aria-label": "진단 결과 보고서 편집기", spellcheck: "true" } },
    onUpdate: ({ editor: current }) => {
      const markdown = syncValue(current, true);
      window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => {
        const snapshot = { id: crypto.randomUUID(), savedAt: Date.now(), content: markdown };
        const next = [snapshot, ...readHistory(bridge)]
          .filter((item, index, items) => index === items.findIndex((candidate) => candidate.content === item.content))
          .slice(0, HISTORY_LIMIT);
        localStorage.setItem(historyKey(bridge), JSON.stringify(next));
        setHistory(next);
      }, 700);
    },
  });

  useEffect(() => {
    if (!bridge || !editor) return undefined;
    bridge.dataset.reactEditor = "1";
    const setContent = (event) => {
      const value = String(event.detail?.value ?? bridge.value ?? "");
      editor.commands.setContent(value, { contentType: "markdown", emitUpdate: false });
      bridge.value = value;
      setCount(editor.storage.characterCount.characters());
    };
    bridge.addEventListener("report-editor:set", setContent);
    return () => bridge.removeEventListener("report-editor:set", setContent);
  }, [bridge, editor]);

  useEffect(() => {
    if (editor) setCount(editor.storage.characterCount.characters());
  }, [editor]);

  useEffect(() => {
    const close = (event) => { if (event.key === "Escape") setProposal(null); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, []);

  const requestRewrite = async () => {
    if (!editor) return;
    const { from, to } = editor.state.selection;
    const selected = editor.state.doc.textBetween(from, to, "\n").trim();
    if (!selected) {
      window.dispatchEvent(new CustomEvent("report-editor:toast", { detail: "본문에서 개선할 문장을 먼저 선택하세요." }));
      editor.commands.focus();
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/controls/report/rewrite", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: selected, mode }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "문장 개선 요청에 실패했습니다.");
      setProposal({ ...result, from, to, selected });
    } catch (error) {
      window.dispatchEvent(new CustomEvent("report-editor:toast", { detail: `문장 개선 실패: ${error.message}` }));
    } finally { setBusy(false); }
  };

  const acceptProposal = () => {
    if (!editor || !proposal?.applied) return;
    const current = editor.state.doc.textBetween(proposal.from, proposal.to, "\n").trim();
    if (current !== proposal.selected) {
      setProposal(null);
      window.dispatchEvent(new CustomEvent("report-editor:toast", { detail: "본문이 변경되었습니다. 문장을 다시 선택하세요." }));
      return;
    }
    editor.chain().focus().insertContentAt({ from: proposal.from, to: proposal.to }, proposal.suggestion).run();
    setProposal(null);
  };

  const restoreHistory = (snapshot) => {
    if (!editor) return;
    editor.commands.setContent(snapshot.content, { contentType: "markdown" });
    setProposal(null);
  };

  return <>
    <div className="react-report-toolbar" aria-label="보고서 편집 도구">
      <div className="react-report-formatting">
        <button type="button" className={editor?.isActive("bold") ? "is-active" : ""} onClick={() => editor?.chain().focus().toggleBold().run()}><strong>B</strong></button>
        <button type="button" className={editor?.isActive("italic") ? "is-active" : ""} onClick={() => editor?.chain().focus().toggleItalic().run()}><em>I</em></button>
        <button type="button" className={editor?.isActive("bulletList") ? "is-active" : ""} onClick={() => editor?.chain().focus().toggleBulletList().run()}>목록</button>
      </div>
      <select aria-label="작성 목적" value={mode} onChange={(event) => setMode(event.target.value)}>{Object.entries(MODE_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select>
      <button type="button" className="react-report-improve" disabled={busy} onClick={requestRewrite}>{busy ? "작성 중…" : "선택 구간 재작성"}</button>
      <details className="react-report-history"><summary>변경 이력 <span>{history.length}</span></summary><div className="react-report-history-menu">
        {history.length ? history.map((item) => <button type="button" onClick={() => restoreHistory(item)} key={item.id}><strong>{new Date(item.savedAt).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}</strong><span>{item.content.slice(0, 48) || "빈 문서"}</span></button>) : <p>수정하면 자동으로 저장됩니다.</p>}
      </div></details>
    </div>
    <article className="report-page react-report-page" id="reportPage" aria-label="진단 결과 보고서 본문">
      <header className="report-page-letterhead"><span>ISMS-P 자체 점검</span><strong>결과 보고서</strong><small>참고용 · 인증 심사를 대체하지 않습니다</small></header>
      <EditorContent editor={editor} />
      <footer className="report-page-footer"><span>내용은 0.7초 후 브라우저에 자동 저장됩니다</span><span id="reportWordCount" role="status" aria-live="polite">본문 {count.toLocaleString("ko-KR")}자</span></footer>
      <div className="report-compose-overlay" id="reportComposeOverlay" hidden>
        <div className="report-compose-card" data-overlay-state="empty">
          <span>보고서</span><strong>진단 결과를 문서로 정리합니다</strong>
          <p>확인 목록을 기준으로 AI가 초안을 쓰고, 이 화면에서 바로 수정할 수 있습니다.</p>
          <div className="report-compose-actions"><button type="button" className="primary" data-write-ai-report>AI로 초안 작성</button><button type="button" data-run-analysis>확인 목록 갱신</button></div>
        </div>
        <div className="report-compose-card" data-overlay-state="writing" hidden>
          <span className="analyze-loading-mark" aria-hidden="true"></span><strong>AI가 초안을 작성하고 있습니다</strong><p>확정된 진단 결과를 문장으로만 정리합니다. 판정 값은 바뀌지 않습니다.</p>
        </div>
      </div>
    </article>
    {proposal && <div className="react-report-dialog" role="dialog" aria-modal="true" aria-labelledby="reactReportDialogTitle">
      <header><div><span>AI 재작성</span><strong id="reactReportDialogTitle">변경 내용을 확인하세요</strong></div><button type="button" aria-label="개선안 닫기" onClick={() => setProposal(null)}>×</button></header>
      <div className="react-report-diff-grid"><article><span>변경 전</span><DiffText before={proposal.original} after={proposal.suggestion} side="before" /></article><article><span>개선안</span><DiffText before={proposal.original} after={proposal.suggestion} side="after" /></article></div>
      <footer><span>{proposal.reason}</span><button type="button" onClick={() => setProposal(null)}>거절</button><button type="button" className="primary" disabled={!proposal.applied} onClick={acceptProposal}>개선안 수락</button></footer>
    </div>}
  </>;
}

const rootElement = document.getElementById("reportEditorReactRoot");
if (rootElement) createRoot(rootElement).render(<ReportEditor />);
