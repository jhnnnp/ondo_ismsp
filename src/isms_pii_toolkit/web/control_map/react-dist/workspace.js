const Is="isms-p-portfolio-assessment-v1",Ts="isms-p-portfolio-checks-v2",Rs="isms-p-portfolio-domain-checks-v1",Ps="isms-p-quest-checks-v1",Ms="isms-p-control-evidence-v1",Ns="isms-p-input-confidence-v1",tt="isms-p-analysis-history-v1",Ds="isms-p-organization-profile-v1",qs="isms-p-diagnosis-sessions-v1",U={unknown:"미점검",none:"미이행",partial:"부분 이행",done:"이행",evidenced:"이행",na:"해당 없음"},K={reviewed:"검토",policy:"정책",implemented:"구현",evidence:"증적"},Bs={reviewed:"검토",policy:"정책/절차",implemented:"구현/운영",evidence:"증적"},Y={1:"관리체계",2:"보호대책",3:"개인정보"},Qn={unknown:"모름",assumed:"추정",confirmed:"확인됨"},rs={assess:"물리 통제(전산실) 적용 여부만 고르면 됩니다. 인증 맞춤이 아니라 점검 범위 설정입니다.",analyze:"왼쪽 통제 항목에서 항목을 고르고, 오른쪽 카드에 진단 상태를 남기세요."},Le={assess:"점검 범위",analyze:"자가진단"},os={assess:"1단계 · 범위",analyze:"2단계 · 진단"},Pe={headcountBand:"1-50",industry:"technology",piiVolume:"low",usesCloud:!0,hasOnPremFacility:!1,usesOutsourcing:!1,usesRemoteAccess:!1,processesRrn:!1};function Os(e){const t=Math.max(0,Math.floor(Number(e)||0)),s=Math.floor(t/86400),n=Math.floor(t%86400/3600),a=Math.floor(t%3600/60);return s>0?`${s}일 ${n}시간`:n>0?`${n}시간`:a>0?`${a}분`:"1분 미만"}function Zn(e){return`${Os(e)} 남음`}function Et(e,t=Date.now()){if(!e)return 0;const s=Date.parse(e);return Number.isNaN(s)?0:Math.max(0,Math.floor((s-t)/1e3))}function Xn(e,t=Date.now()){const s=!!e?.active,n=s&&e?.kind==="invite",a=Et(e?.expiresAt,t);return n?{active:!0,meta:"등록됨",label:"초대권이 등록되었습니다."}:s&&a>0?{active:!0,meta:Os(a),label:`사용권 ${Zn(a)}`}:e?.expiresAt?{active:!1,expired:!0,meta:"만료",label:"사용권이 만료되었습니다. 다시 등록하세요."}:{active:!1,expired:!1,meta:"미등록",label:"사용권을 등록하세요."}}function P(e){return document.getElementById(e)}const qt="is-workspace-locked";let R={required:!0,workspaceRequired:!0,active:!1,remainingSeconds:0,expiresAt:null,durationDays:null},vt=0,ae=null,Me=null;function st(){const e=P("pageHeadPass"),t=P("pageHeadPassLabel"),s=P("pageHeadPassMeta");if(!e||!t||!s)return;if(!R.required){e.hidden=!0;return}e.hidden=!1;const n=Xn(R);e.classList.toggle("is-active",n.active),e.classList.toggle("is-expired",!!n.expired),e.classList.toggle("is-empty",!n.active&&!n.expired),t.textContent="사용권",s.textContent=n.meta,e.setAttribute("aria-label",n.label),document.querySelectorAll("[data-write-ai-report]").forEach(a=>{n.active||!R.required?(a.removeAttribute("data-access-required"),a.removeAttribute("title")):(a.setAttribute("data-access-required","true"),a.setAttribute("title","클릭하여 사용권을 등록한 뒤 AI 초안을 작성하세요."))})}function js(e){const t=P("workspaceAccessGate");Array.from(document.body.children).forEach(s=>{s!==t&&(e?s.setAttribute("inert",""):s.removeAttribute("inert"))})}function Bt(){document.documentElement.classList.add(qt);const e=P("workspaceAccessGate");e&&(e.setAttribute("aria-hidden","false"),e.removeAttribute("inert")),js(!0);const t=P("workspaceAccessInput");t&&document.activeElement!==t&&t.focus()}function Fs(){if(document.documentElement.classList.remove(qt),P("workspaceAccessGate")?.setAttribute("aria-hidden","true"),js(!1),Me){const t=Me;Me=null,t(!0)}}function Hs(){return new Promise(e=>{const t=Me;Me=s=>{t?.(s),e(s)}})}function zs(e=R){return!!e.workspaceRequired&&!e.active}function Ot(e=R){zs(e)?Bt():Fs()}function _s(){if(window.clearInterval(vt),!R.required||!R.expiresAt)return;const e=Et(R.expiresAt);if(e<=0){R={...R,active:!1,remainingSeconds:0},st(),Ot(R);return}const t=e<3600?1e3:3e4;vt=window.setInterval(()=>{st(),Et(R.expiresAt)<=0&&(window.clearInterval(vt),jt())},t)}async function jt(){try{const e=await fetch("/access/status",{credentials:"same-origin"});if(!e.ok)throw new Error("status");R=await e.json()}catch{R={required:!0,workspaceRequired:!0,active:!1,remainingSeconds:0,expiresAt:null,durationDays:null}}return st(),_s(),Ot(R),R}async function ea(e){const t=await fetch("/access/register",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:e})}),s=await t.json().catch(()=>({}));if(!t.ok)throw new Error(s.detail||"사용권을 등록하지 못했습니다.");return R=s,st(),_s(),Ot(R),R}function Ke(e=!1){if(P("accessPassDialog")?.close(),ae){const s=ae;ae=null,s(e)}}function Us(e,t,s,n){const a=P(e),r=P(t),o=P(s);!a||a.dataset.bound==="1"||(a.dataset.bound="1",a.addEventListener("submit",async l=>{l.preventDefault();const d=String(r?.value||"").trim();if(o&&(o.hidden=!0),d.length<16){o&&(o.hidden=!1,o.textContent="발급받은 초대 코드를 그대로 붙여넣으세요."),r?.focus();return}const u=P(n);u&&(u.disabled=!0);try{await ea(d),r&&(r.value=""),e==="accessPassForm"&&Ke(!0)}catch(f){o&&(o.hidden=!1,o.textContent=f.message||"사용권을 등록하지 못했습니다.")}finally{u&&(u.disabled=!1)}}))}function Gs(){const e=P("accessPassDialog");Us("accessPassForm","accessPassInput","accessPassError","accessPassSubmitBtn"),!(!e||e.dataset.bound==="1")&&(e.dataset.bound="1",e.addEventListener("click",t=>{t.target===e&&Ke(!1)}),e.addEventListener("cancel",t=>{t.preventDefault(),Ke(!1)}),P("accessPassCancelBtn")?.addEventListener("click",()=>Ke(!1)))}function Ws(){Us("workspaceAccessForm","workspaceAccessInput","workspaceAccessError","workspaceAccessSubmitBtn")}function xt(){Gs();const e=P("accessPassDialog"),t=P("accessPassInput"),s=P("accessPassError");return e?(s&&(s.hidden=!0),e.open?ae?new Promise(n=>{const a=ae;ae=r=>{a(r),n(r)}}):Promise.resolve(!1):new Promise(n=>{ae=n,e.showModal(),t?.focus(),t?.select()})):Promise.resolve(!1)}async function Vs(){const e=await jt();return!e.required||e.active?!0:document.documentElement.classList.contains(qt)?Hs():xt()}async function ta(){Ws();const e=await jt();return!e.workspaceRequired||e.active?(Fs(),!0):(Bt(),Hs())}function sa(){Gs(),Ws(),P("pageHeadPass")?.addEventListener("click",()=>{xt()}),window.addEventListener("access-pass:required",()=>{zs()?Bt():xt()});const e=window.fetch.bind(window);window.fetch=async(t,s)=>{const n=await e(t,s);try{const a=String(typeof t=="string"?t:t?.url||""),r=new URL(a,window.location.origin).pathname;n.status===403&&(r==="/controls/report"||r==="/controls/report/rewrite")&&window.dispatchEvent(new CustomEvent("access-pass:required"))}catch{}return n}}const p=e=>document.getElementById(e);async function ke(e,t){const s=await fetch(e,t);if(!s.ok)throw new Error(await s.text());return s.json()}let ht=null;function $(e,t={}){const s=p("toast");if(!s)return;const n=String(e||"").trim();if(!n)return;const a=/실패|오류|불러오지 못/.test(n)?"error":/찾을 수 없|없습니다|먼저|필요|변경되었습니다/.test(n)?"warning":"success",r=t.tone||a,o=r==="warning"?{title:"확인 필요",icon:"!"}:r==="error"?{title:"처리 실패",icon:"!"}:{title:"",icon:"✓"},l=t.title??o.title,d=s.querySelector(".toast-copy strong");s.dataset.tone=r,s.querySelector(".toast-icon").textContent=o.icon,d.textContent=l,d.hidden=!l,s.querySelector(".toast-copy p").textContent=n;const u=t.duration||(r==="success"?2200:4e3);s.style.setProperty("--toast-duration",`${u}ms`),s.classList.remove("show"),s.offsetWidth,s.classList.add("show"),window.clearTimeout(ht),ht=window.setTimeout(()=>s.classList.remove("show"),u),s.querySelector(".toast-close").onclick=()=>{window.clearTimeout(ht),s.classList.remove("show")}}function Ft({title:e="계속 진행할까요?",message:t="이 작업을 진행하기 전에 내용을 확인해 주세요.",confirmLabel:s="확인",cancelLabel:n="취소",tone:a="default"}={}){let r=p("appConfirmDialog");return r||(r=document.createElement("dialog"),r.id="appConfirmDialog",r.className="app-confirm-dialog",r.setAttribute("aria-labelledby","appConfirmTitle"),r.setAttribute("aria-describedby","appConfirmMessage"),r.innerHTML=`
      <form method="dialog" class="app-confirm-shell">
        <div class="app-confirm-icon" aria-hidden="true">!</div>
        <div class="app-confirm-copy">
          <span>확인</span>
          <h2 id="appConfirmTitle"></h2>
          <p id="appConfirmMessage"></p>
        </div>
        <div class="app-confirm-actions">
          <button type="submit" value="cancel" class="app-confirm-cancel"></button>
          <button type="submit" value="confirm" class="app-confirm-submit"></button>
        </div>
      </form>`,document.body.append(r),r.addEventListener("click",o=>{o.target===r&&r.close("cancel")})),r.dataset.tone=a,r.querySelector(".app-confirm-copy > span").textContent=a==="danger"?"삭제 확인":"확인",r.querySelector("#appConfirmTitle").textContent=e,r.querySelector("#appConfirmMessage").textContent=t,r.querySelector(".app-confirm-cancel").textContent=n,r.querySelector(".app-confirm-submit").textContent=s,r.showModal(),new Promise(o=>{r.addEventListener("close",()=>o(r.returnValue==="confirm"),{once:!0})})}function na(e){return new Promise(t=>setTimeout(t,e))}function c(e){return String(e).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}const i={currentView:"assess",diagnosisSessions:[],activeSessionId:null,allControls:[],checklist:[],assessments:{},controlChecks:{},controlEvidence:{},domainChecks:{},domainTouched:{},analysis:null,analysisHistory:[],analysisStale:!1,lastAiExecutiveReport:null,aiReportStale:!1,aiReportWriting:!1,reportReview:{},reportReturn:null,dashboard:null,areaFilter:"all",levelFilter:"all",assessSearch:"",expandedRows:new Set,collapsedCategories:new Set,activeCategoryId:null,categoriesBootstrapped:!1,analyzeSection:"actions",analyzeDetailTab:"problem",cascadeExpanded:!1,problemFiltersOpen:!1,detailReturnContext:null,expandedGapInline:{},expandedProblemCascade:new Set,expandedProblemGroups:new Set,expandedProblemItems:new Set,problemAreaFilter:"all",problemLevelFilter:"all",problemSeverityFilter:"all",problemSourceFilter:"all",problemChecklistQuery:"",problemViewMode:"all",selectedProblemCategory:null,selectedProblemControl:null,multigapSeverityFilter:"all",selectedMultigapTheme:null,expandedMultigapThemes:new Set,gapSearch:"",gapLevelFilter:"all",expandedGaps:new Set,expandedMultigaps:new Set,expandedProblemClusters:new Set,gapRevealPending:!1,analyzeScenarioId:null,sessionBundleMode:"chain",sessionSelectedControlId:null,pendingDoneEvidenceControlId:null,sessionCollapsedCategories:new Set,organizationProfile:null,pendingProfile:null,scopeDraft:null,questChecks:{},inputConfidence:{},legalBasisCache:{}},aa=["assessments","controlChecks","controlEvidence","domainChecks","domainTouched","questChecks","inputConfidence","reportReview"];function ye(e){return e&&typeof e=="object"&&!Array.isArray(e)?e:{}}function yt(e){return JSON.parse(JSON.stringify(e))}function Ks(){return globalThis.crypto?.randomUUID?globalThis.crypto.randomUUID():`diagnosis-${Date.now()}-${Math.random().toString(36).slice(2,10)}`}function Ht(){return{assessments:{},controlChecks:{},controlEvidence:{},domainChecks:{},domainTouched:{},questChecks:{},inputConfidence:{},reportReview:{},analysisHistory:[],organizationProfile:null,sessionSelectedControlId:null}}function ge(e){const t=ye(e),s=Ht();aa.forEach(r=>{s[r]=yt(ye(t[r]))});const n=ye(t.controlEvidence),a={};return Object.entries(n).forEach(([r,o])=>{Array.isArray(o)&&(a[r]=o.filter(l=>l&&typeof l=="object"&&String(l.title||"").trim()).map(l=>({id:String(l.id||`ev-${r}-${Math.random().toString(36).slice(2,8)}`),title:String(l.title||"").trim(),url:String(l.url||"").trim(),note:String(l.note||"").trim(),createdAt:String(l.createdAt||new Date().toISOString())})))}),s.controlEvidence=a,s.analysisHistory=Array.isArray(t.analysisHistory)?yt(t.analysisHistory.slice(0,8)):[],s.organizationProfile=yt(ye(t.organizationProfile)),Object.keys(s.organizationProfile).length||(s.organizationProfile=null),s.sessionSelectedControlId=typeof t.sessionSelectedControlId=="string"&&t.sessionSelectedControlId.trim()||null,s}const Js=48;function Ys(e,t="진단"){return String(e||"").replace(/\s+/g," ").trim().slice(0,Js)||t}function Ee({id:e=Ks(),name:t="새 진단",now:s=new Date().toISOString(),data:n=Ht()}={}){return{id:e,name:Ys(t),createdAt:s,updatedAt:s,data:ge(n)}}function ia(e,{id:t=Ks(),now:s=new Date().toISOString()}={}){return Ee({id:t,name:`${e?.name||"진단"} 복사본`,now:s,data:ge(e?.data)})}function Qs(e,t=101){const s=ye(e?.data?.assessments),n=Object.values(s),a=n.filter(d=>d==="na").length,r=n.filter(d=>d&&d!=="unknown"&&d!=="na").length,o=Math.max(t-a,0),l=o?Math.round(r/o*100):0;return{reviewed:r,applicable:o,na:a,percent:l}}function ra(e){const t=ye(e),s=Array.isArray(t.sessions)?t.sessions.filter(n=>n?.id).map(n=>{const a=Ee({id:String(n.id),name:String(n.name||"진단"),now:String(n.createdAt||n.updatedAt||new Date().toISOString()),data:n.data});return a.updatedAt=String(n.updatedAt||a.createdAt),a}):[];return{version:1,sessions:s,activeSessionId:oa(t,s)}}function oa(e,t){const s=typeof e?.activeSessionId=="string"?e.activeSessionId:null;return s&&t.some(n=>n.id===s)?s:null}function la(){return globalThis.crypto?.randomUUID?globalThis.crypto.randomUUID():`ev-${Date.now()}-${Math.random().toString(36).slice(2,8)}`}function zt(e){const t=i.controlEvidence?.[e];return Array.isArray(t)?t:[]}function Q(e){return zt(e).length>0}function Zs(e){return i.controlEvidence||(i.controlEvidence={}),Array.isArray(i.controlEvidence[e])||(i.controlEvidence[e]=[]),i.controlEvidence[e]}function ca(e,{title:t,url:s="",note:n=""}={}){const a=String(t||"").trim();if(!a)return{ok:!1,reason:"empty_title"};const r=String(s||"").trim(),o=String(n||"").trim(),l={id:la(),title:a,url:r,note:o,createdAt:new Date().toISOString()};return Zs(e).push(l),{ok:!0,item:l}}function da(e,t){const n=Zs(e).filter(a=>a.id!==t);return i.controlEvidence[e]=n,n.length}function x(e){const t=i.assessments[e]||"unknown";return t==="evidenced"?"done":t}function Xs(e,t){if(!e||!e.reviewed)return"unknown";const s=!!e.evidence&&(t?Q(t):!0);return e.policy&&e.implemented&&s?"done":e.policy||e.implemented?"partial":"none"}function _t(e){return e==="evidenced"||e==="done"?{reviewed:!0,policy:!0,implemented:!0,evidence:!0}:e==="partial"?{reviewed:!0,policy:!0,implemented:!1,evidence:!1}:e==="none"?{reviewed:!0,policy:!1,implemented:!1,evidence:!1}:{reviewed:!1,policy:!1,implemented:!1,evidence:!1}}function en(e,t){const s={...e};return t&&!Q(t)&&(s.evidence=!1),s.evidence&&(s.reviewed=!0,s.policy=!0,s.implemented=!0),(s.policy||s.implemented)&&!s.reviewed&&(s.reviewed=!0),s.reviewed||(s.policy=!1,s.implemented=!1,s.evidence=!1),s}function ls(e){return String(e||"").split(".").map(t=>Number(t)||0)}function Ce(e,t){const s=ls(e),n=ls(t),a=Math.max(s.length,n.length);for(let r=0;r<a;r+=1){const o=(s[r]||0)-(n[r]||0);if(o)return o}return 0}function Lt(e){const t=new Map;return e.forEach(s=>{const n=s.categoryId||"기타";t.has(n)||t.set(n,{categoryId:n,categoryName:s.categoryName||n,areaId:s.areaId,areaName:s.areaName||"",controls:[]}),t.get(n).controls.push(s)}),Array.from(t.values()).sort((s,n)=>Ce(s.categoryId,n.categoryId))}function nt(e){const t=e.length,s=e.filter(a=>x(a.id)!=="unknown").length,n=t?Math.round(s/t*100):0;return{total:t,reviewed:s,pct:n}}function ua(){new Set([...Object.keys(i.controlChecks||{}),...Object.keys(i.assessments||{}),...Object.keys(i.controlEvidence||{})]).forEach(t=>{if(i.assessments[t]==="na")return;i.assessments[t]==="evidenced"&&(i.assessments[t]="done");const s={...i.controlChecks[t]||_t(i.assessments[t]||"unknown")};s.evidence=Q(t);const n=en(s,t);i.controlChecks[t]=n,i.assessments[t]=Xs(n,t)})}const tn="isms-p-diagnosis-backup",It=1;function Je(e){return e&&typeof e=="object"&&!Array.isArray(e)?e:null}function pa(e,t=new Date().toISOString()){if(!Je(e)||!String(e.id||"").trim())throw new Error("내보낼 진단을 찾을 수 없습니다.");return{format:tn,version:It,exportedAt:t,notice:"사용자가 입력한 참고용 자가진단 백업이며 인증 적합성을 증명하지 않습니다.",session:{name:String(e.name||"진단"),createdAt:String(e.createdAt||t),updatedAt:String(e.updatedAt||t),data:ge(e.data)}}}function fa(e,t=101){let s;try{s=typeof e=="string"?JSON.parse(e):e}catch{throw new Error("JSON 형식의 진단 백업 파일이 아닙니다.")}if(!Je(s)||s.format!==tn)throw new Error("이 프로젝트에서 만든 진단 백업 파일이 아닙니다.");if(s.version!==It)throw new Error(`지원하지 않는 백업 버전입니다. 현재 지원 버전: ${It}`);const n=Je(s.session);if(!n||!Je(n.data))throw new Error("백업 파일에 진단 데이터가 없습니다.");const a=ge(n.data),r=Ee({name:String(n.name||"가져온 진단"),data:a});return{name:r.name,originalCreatedAt:String(n.createdAt||""),originalUpdatedAt:String(n.updatedAt||""),exportedAt:String(s.exportedAt||""),data:a,progress:Qs(r,t)}}function ga(e,t=[]){const s=new Set(t),n=`${String(e||"진단").trim()||"진단"} (가져옴)`;if(!s.has(n))return n;let a=2;for(;s.has(`${n} ${a}`);)a+=1;return`${n} ${a}`}function ma(e,t=[],s=new Date().toISOString()){return Ee({name:ga(e?.name,t),now:s,data:e?.data})}function J(e,t){try{const s=localStorage.getItem(e);return s?JSON.parse(s):t}catch{return t}}function te(){localStorage.setItem(qs,JSON.stringify({version:1,sessions:i.diagnosisSessions,activeSessionId:i.activeSessionId}))}function va(){return ge({assessments:J(Is,{}),controlChecks:J(Ts,{}),controlEvidence:J(Ms,{}),domainChecks:J(Rs,{}),questChecks:J(Ps,{}),inputConfidence:J(Ns,{}),reportReview:{},analysisHistory:J(tt,[]),organizationProfile:J(Ds,null)})}function ha(e){return!!(e.organizationProfile||Object.values(e).filter(t=>t&&typeof t=="object").some(t=>Object.keys(t).length))}function ya(){return ge({assessments:i.assessments,controlChecks:i.controlChecks,controlEvidence:i.controlEvidence,domainChecks:i.domainChecks,domainTouched:i.domainTouched,questChecks:i.questChecks,inputConfidence:i.inputConfidence,reportReview:{},analysisHistory:i.analysisHistory,organizationProfile:i.organizationProfile,sessionSelectedControlId:i.sessionSelectedControlId})}function ba(e){const t=ge(e);i.assessments=t.assessments,i.controlChecks=t.controlChecks,i.controlEvidence=t.controlEvidence,i.domainChecks=t.domainChecks,i.domainTouched=t.domainTouched,i.questChecks=t.questChecks,i.inputConfidence=t.inputConfidence,i.reportReview={},i.analysisHistory=t.analysisHistory,i.organizationProfile=t.organizationProfile?{...Pe,...t.organizationProfile,usesOutsourcing:!1,usesRemoteAccess:!1,processesRrn:!1}:null,i.sessionSelectedControlId=t.sessionSelectedControlId,i.analysis=null,i.analysisStale=!1,i.lastAiExecutiveReport=null,i.aiReportStale=!1,i.aiReportWriting=!1,i.reportReturn=null,i.currentView="assess",i.areaFilter="all",i.levelFilter="all",i.assessSearch="",i.expandedRows=new Set,i.collapsedCategories=new Set,i.activeCategoryId=null,i.categoriesBootstrapped=!1,i.analyzeSection="actions",i.expandedProblemGroups=new Set,i.expandedProblemItems=new Set,i.expandedGaps=new Set,i.expandedMultigaps=new Set,i.gapSearch="",i.scopeDraft=null,i.analyzeScenarioId=null,i.sessionBundleMode="chain",ua()}function wa(){const e=J(qs,null);if(e){const s=ra(e);return i.diagnosisSessions=s.sessions,i.activeSessionId=s.activeSessionId,i.diagnosisSessions}const t=va();return i.diagnosisSessions=ha(t)?[Ee({name:"기존 진단",data:t})]:[],i.activeSessionId=null,te(),i.diagnosisSessions}function Ut(e){const t=i.diagnosisSessions.find(s=>s.id===e);return t?(i.activeSessionId=t.id,ba(t.data),te(),t):null}function $a(){const e=new Set(i.diagnosisSessions.map(n=>n.name));let t=1;for(;e.has(`진단 ${t}`);)t+=1;const s=Ee({name:`진단 ${t}`,data:Ht()});return i.diagnosisSessions.unshift(s),te(),Ut(s.id),s}function Sa(e){const t=i.diagnosisSessions.find(n=>n.id===e);if(!t)return null;const s=ia(t);return i.diagnosisSessions.unshift(s),te(),s}function ka(e,t){const s=i.diagnosisSessions.findIndex(o=>o.id===e);if(s<0)return null;const n=i.diagnosisSessions[s],a=Ys(t,n.name);if(a===n.name)return n;const r={...n,name:a,updatedAt:new Date().toISOString()};return i.diagnosisSessions[s]=r,te(),r}function Ca(e){i.activeSessionId===e&&Ue();const t=i.diagnosisSessions.find(s=>s.id===e);if(!t)throw new Error("내보낼 진단을 찾을 수 없습니다.");return pa(t)}function Aa(e){return fa(e,i.checklist?.length||101)}function Ea(e){const t=ma(e,i.diagnosisSessions.map(s=>s.name));return i.diagnosisSessions.unshift(t),te(),t}function xa(e){const t=i.diagnosisSessions.length;return i.diagnosisSessions=i.diagnosisSessions.filter(s=>s.id!==e),i.activeSessionId===e&&(i.activeSessionId=null),i.diagnosisSessions.length===t?!1:(te(),!0)}function Ue(){if(!i.activeSessionId)return;const e=i.diagnosisSessions.findIndex(t=>t.id===i.activeSessionId);e<0||(i.diagnosisSessions[e]={...i.diagnosisSessions[e],updatedAt:new Date().toISOString(),data:ya()},te())}function me(){if(i.activeSessionId){Ue();return}localStorage.setItem(Is,JSON.stringify(i.assessments)),localStorage.setItem(Ts,JSON.stringify(i.controlChecks)),localStorage.setItem(Ms,JSON.stringify(i.controlEvidence||{})),localStorage.setItem(Rs,JSON.stringify(i.domainChecks)),localStorage.setItem(Ps,JSON.stringify(i.questChecks||{})),localStorage.setItem(Ns,JSON.stringify(i.inputConfidence||{}))}function La(e){if(i.organizationProfile=e,i.activeSessionId){Ue();return}localStorage.setItem(Ds,JSON.stringify(e))}const sn=[["제거","삭제","해지","말소","회수","폐기"],["계정","아이디","userid"],["불필요","미사용","휴면"],["패치","업데이트","보안패치","핫픽스"],["비밀번호","패스워드","password"],["권한","접근권한"],["관리자","root","admin","특권"],["암호화","tls","ssl"],["로그","접속기록","감사로그"],["백업","복구"],["악성코드","바이러스","랜섬웨어","백신"],["퇴직","퇴사","이직"],["외주","수탁","위탁","외부자"],["원격","vpn","재택"],["인증","mfa","otp","다중인증"]],Ia=["불필요","주기적","사용자","보안패치","보안","적용","점검","파일","최소","그룹","방화벽","개인정보","파기","보유기간","화면보호기","취약점","재직","계약종료","계약만료","계약","직무변경","필요성","잔존"],Ta=[...new Set([...sn.flat(),...Ia])].filter(e=>e.length>=2).sort((e,t)=>t.length-e.length),nn=new Map;sn.forEach(e=>{e.forEach(t=>{nn.set(t,e)})});function B(e){return String(e||"").toLowerCase().normalize("NFC").replace(/[\s\u00a0·.,;:()[\]{}'"'`~!@#$%^&*_+=|\\/<>?-]/g,"")}function N(e,t){if(e!=null){if(typeof e=="string"||typeof e=="number"){const s=String(e).trim();s&&t.push(s);return}if(Array.isArray(e)){e.forEach(s=>N(s,t));return}typeof e=="object"&&["item","label","title","text","problem","phrase","concepts"].forEach(s=>{e[s]&&N(e[s],t)})}}function an(e){const t=[];return N(e?.id,t),N(e?.title,t),N(e?.areaName,t),N(e?.categoryName,t),N(e?.tags,t),N(e?.checklistItems,t),N(e?.officialRequirement,t),N(e?.officialEvidenceExamples,t),N(e?.recommendedActions,t),N(e?.riskIfMissing,t),N(e?.searchHints,t),N(e?.searchEntries,t),N(e?.searchIntents,t),N(e?.officialChecks,t),B(t.join(" "))}function cs(e){const t=[];let s=0;for(;s<e.length;){let n="";for(const a of Ta)if(e.startsWith(a,s)){n=a;break}n?(t.push(n),s+=n.length):s+=1}return t}function Ra(e){let t=B(e);const s=["해주세요","인가요","입니다","합니다","했어요","해요","되어","됐다","있음","없음"];for(const n of s)if(t.length>n.length+1&&t.endsWith(n)){t=t.slice(0,-n.length);break}for(const n of["에서","으로","라고","까지","부터","이","가","을","를","은","는","의","에","로","도","만"])if(t.length>n.length+1&&t.endsWith(n)){t=t.slice(0,-n.length);break}return t}function rn(e){const t=String(e||"").trim().toLowerCase().normalize("NFC");if(!t)return[];const s=t.split(/[\s,./·]+/).map(Ra).filter(r=>r.length>=2);if(s.length>1){const r=s.flatMap(o=>{const l=cs(o);return l.length?l:[o]});return[...new Set(r)]}const n=B(t),a=cs(n);return a.length>=2?[...new Set(a)]:n?[n]:[]}function Pa(e){const t=B(e),s=nn.get(t);return s?[...new Set(s.map(n=>B(n)))]:[t]}function be(e,t){return Pa(t).some(s=>s&&e.includes(s))}function on(e,t){const s=B(t);return s?(e?.searchIntents||[]).reduce((n,a)=>{const r=[...new Set((a?.concepts||[]).map(B).filter(Boolean))];if(!r.length)return n;const o=r.filter(m=>s.includes(m)).length,l=r.length===1?1:Math.min(2,r.length);if(o<l)return n;const d=o/r.length,u=Math.min(r.reduce((m,g)=>m+g.length,0),18)/18,f=Math.max(0,Math.min(100,Number(a?.weight)||0));return Math.max(n,42+d*28+u*12+f*.18)},0):0}const Ma=new Set(["재직","계약","계약종료","계약만료","직무변경","필요성","잔존","퇴사","퇴직","외주"]);function Na(e,t){return t.length<3?!1:(e?.searchEntries||[]).filter(n=>Number(n?.weight)>=90&&n?.text).some(n=>{const a=B(n.text);return t.some(r=>Ma.has(r)&&be(a,r))})}function Da(e,t){if(!e||!t)return 0;const s=e.length,n=t.length;let a=0,r=new Array(n+1).fill(0);for(let o=1;o<=s;o+=1){const l=new Array(n+1).fill(0);for(let d=1;d<=n;d+=1)e[o-1]===t[d-1]&&(l[d]=r[d-1]+1,l[d]>a&&(a=l[d]));r=l}return a}function ln(e,t){const s=String(t||"").trim();if(!s)return!0;const n=B(s);if(!n)return!0;const a=an(e);if(a.includes(n))return!0;const r=String(e?.id||"").toLowerCase();if(r&&r.includes(s.toLowerCase())||/^\d+(\.\d+)*$/.test(s)&&B(r)===n)return!0;const o=rn(s);if(on(e,s)>=60)return!0;if(o.length>=2){const l=o.filter(d=>be(a,d)).length;return Na(e,o)?!0:o.length===2?l===2:l>=2&&l/o.length>=.6}return n.length>=6?Da(n,a)>=Math.min(6,Math.ceil(n.length*.65)):a.includes(n)}function ds(e,t){const s=String(t||"").trim();if(!s)return 0;const n=B(s),a=B(e?.title);if(B(e?.id)===n||String(e?.id||"").toLowerCase()===s.toLowerCase())return 100;if(a.includes(n))return 90;const o=rn(s),l=on(e,s),d=(e?.searchHints||[]).map(y=>B(y)),u=(e?.searchEntries||[]).map(y=>({text:B(y?.text),weight:Math.max(0,Math.min(100,Number(y?.weight)||0))})).filter(y=>y.text),f=u.filter(y=>y.text.includes(n)).reduce((y,L)=>Math.max(y,L.weight),0);if(f)return Math.max(70+Math.round(f*.2),Math.round(l));const m=u.reduce((y,L)=>{if(!o.length)return y;const v=o.filter(k=>be(L.text,k)).length;if(!v)return y;const S=v/o.length,b=Math.min(v,3)/3;return Math.max(y,S*38+b*22+L.weight*.18)},0);if(d.some(y=>y.includes(n)))return Math.max(90,Math.round(l));const h=o.filter(y=>be(a,y)).length,w=o.filter(y=>d.some(L=>be(L,y))).length,A=an(e),E=o.filter(y=>be(A,y)).length;return o.length&&h===o.length?Math.max(82,Math.round(m)):o.length&&w===o.length?Math.max(76,Math.round(m)):o.length&&E===o.length?Math.max(64,Math.round(m)):Math.max(Math.round(l),Math.round(m),E?35+Math.round(E/o.length*20):0)}function cn(e,t){const s=Array.isArray(e)?e:[];return String(t||"").trim()?[...s].sort((n,a)=>{const r=ds(a,t)-ds(n,t);return r||String(n.id).localeCompare(String(a.id),"en",{numeric:!0})}):s}function Gt(e){return ln(e,i.assessSearch)}function qa(){const e={};return i.checklist.forEach(t=>{e[t.areaId]||(e[t.areaId]=t.areaName)}),e}function Ve(e){return i.checklist.filter(t=>e!=="all"&&t.areaId!==e||!Gt(t)?!1:i.levelFilter==="all"||x(t.id)===i.levelFilter).length}function Ba(){return{all:Ve("all"),1:Ve("1"),2:Ve("2"),3:Ve("3")}}function Oa(){return i.checklist.filter(e=>i.areaFilter!=="all"&&e.areaId!==i.areaFilter?!1:Gt(e))}function us(){return i.areaFilter==="all"?i.checklist:i.checklist.filter(e=>e.areaId===i.areaFilter)}function dn(){return i.levelFilter!=="all"||!!i.assessSearch.trim()}function ja(e){return i.checklist.filter(t=>i.areaFilter!=="all"&&t.areaId!==i.areaFilter||!Gt(t)?!1:e==="all"||x(t.id)===e).length}function Fa(){return Object.fromEntries(["all","unknown","none","partial","done","na"].map(t=>[t,ja(t)]))}function lt(){const e=Oa(),t=i.levelFilter==="all"?e:e.filter(s=>x(s.id)===i.levelFilter);return cn(t,i.assessSearch)}function un(){return Object.values(i.assessments).filter(e=>e!=="unknown"&&e!=="na").length}function pn(){const e=Object.keys(i.assessments).length||101,t=Object.values(i.assessments).filter(s=>s==="na").length;return Math.max(e-t,0)}function fn(e){return`<span class="status-pill level-${e}">${U[e]||e}</span>`}function ps(e){try{const t=new URL(e||"");return t.protocol!=="https:"||!["law.go.kr","www.law.go.kr"].includes(t.hostname)?"":t.href}catch{return""}}function Ha(e){return String(e||"").replace(/개인 정보/g,"개인정보").replace(/정보 주체/g,"정보주체").replace(/공동 주택/g,"공동주택").replace(/관리 주체/g,"관리주체").replace(/주택 관리/g,"주택관리").replace(/관리 사무소/g,"관리사무소").replace(/입주자대표 회의/g,"입주자대표회의").replace(/개인정보 처리자/g,"개인정보처리자").replace(/\s+/g," ").trim()}function za(e){const t=[],s=new Set,n=String(e||""),a=/(\d+)\)\s*\1\)\s*/g;let r="",o=0,l=a.exec(n);for(;l;){r+=n.slice(o,l.index);const d=n.slice(l.index+l[0].length),u=d.match(/^(.{4,400}?)참조\)?/)||d.match(/^(.{4,400}?)(?:같음|의미함|이유서|심사보고서)[).,]?/);if(u){let f=u[0];f.endsWith("참조")&&d[f.length]===")"&&(f+=")");const m=l[1],g=f.replace(/[,\s]+$/,"").trim();g&&!s.has(`${m}:${g}`)&&(t.push({num:m,text:g}),s.add(`${m}:${g}`)),r+=`{{FN:${m}}}`,o=l.index+l[0].length+f.length,a.lastIndex=o}else r+=l[0],o=l.index+l[0].length;l=a.exec(n)}return r+=n.slice(o),{text:r,notes:t}}function _a(e){const t=String(e||""),s=t.search(/\s*(?:※\s*법령정비\s*권고사항|<\s*관계\s*법령\s*>)/);if(s>=0)return{body:t.slice(0,s).trim(),appendix:t.slice(s).trim()};const n=t.search(/\s((?:「[^」]+」|[가-힣A-Za-z0-9ㆍ·\s]{4,80}(?:법률|시행령|시행규칙))\s+제\d+조\()/);return n>=0&&n>t.length*.45?{body:t.slice(0,n).trim(),appendix:t.slice(n).trim()}:{body:t.trim(),appendix:""}}function Ua(e){return String(e||"").replace(/\r\n?/g,`
`).replace(/\u00a0/g," ").replace(/(\d+)\s*[•·]\s*(?:\n|$)/g,`
`).replace(/(\d+\))\s*\1/g,"$1 ").replace(/(할 것인데|할 것인바|있는바|하는바|인바)\s*(\{\{FN:\d+\}\})\s*,/g,`$1$2,
`).replace(/(합니다|됩니다|있습니다|없습니다|않습니다|봅니다|입니다|것입니다|판단됩니다|어렵습니다|해당하지 않습니다|요청함)\.(\{\{FN:\d+\}\})\s+/g,`$1.$2
`).replace(/(\{\{FN:\d+\}\})\s+([의인에을를은는과와로하])/g,"$1$2").replace(/(\{\{FN:\d+\}\})\s+,/g,"$1,").replace(/\s*<\s*([^<>]{2,40})\s*>\s*/g,`
<$1>
`).replace(/\s+([가나다라마바사아자차카타파하])\.\s+(?=「|[가-힣]|제\d)/g,`
$1. `).replace(/(?:^|\n)\s*([①-⑳])\s+/g,`
$1 `).replace(/\s+(※)\s+/g,`
$1 `).replace(/\s+[○●]\s+/g,`
- `).replace(/(?:^|\n)\s*[-–∙·•▪◦]\s+/g,`
- `).replace(/\n{3,}/g,`

`).trim()}function Ga(e){if(!/여부와/.test(e))return[e];const t=e.split(/\s*여부와\s+/);if(t.length!==2)return[e];const s=t[0].trim(),n=t[1].trim();return!s||!n?[e]:!/(여부|있는지|할지|인지|「)/.test(s)||!/(여부|「)/.test(n)?[e]:[/여부\??$/.test(s)?s:`${s} 여부`,n]}function fs(e){if(e.length<90)return[e];const t=e.split(new RegExp("(?<=(?:합니다|됩니다|있습니다|없습니다|않습니다|봅니다|입니다|것입니다|판단됩니다|어렵습니다|해당하지 않습니다|요청함)\\.)(?:\\{\\{FN:\\d+\\}\\})?\\s+|(?<=(?:할 것인데|할 것인바|있는바|하는바|인바)(?:\\{\\{FN:\\d+\\}\\})?,)\\s+"));return t.length>1?t.map(s=>s.trim()).filter(Boolean):[e]}function Wa(e,t){return/^(행위 주체 내용|관리주체|질의 배경|질의배경|관계 법령|법령정비 권고사항|결론)$/.test(e)||e.length<=40&&/(?:결정례|판례|구조도|법적 근거)$/.test(e)?!0:e.length<=16&&!/[.!?。?]$/.test(e)&&!/^[①-⑳가나다라마바사\d]/.test(e)&&/^[①-⑳]/.test(t||"")}function q(e){return c(Ha(e)).replace(/\{\{FN:(\d+)\}\}/g,'<sup class="legal-fn-mark">$1)</sup>').replace(/(대법원|헌법재판소)\s+\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*선고\s+[0-9가-힣]+(?:\s*(?:판결|결정)(?:례)?)?/g,'<em class="legal-precedent">$&</em>').replace(/「([^」]+)」/g,'<strong class="legal-cite">「$1」</strong>').replace(/(제\d+조(?:의\d+)?(?:제\d+항)?(?:제\d+호)?(?:[가-하]목)?(?:단서|본문)?)/g,'<b class="legal-article-ref">$1</b>')}function Va(e){const t=Ua(e).split(/\n+/).map(u=>u.trim()).filter(u=>u&&!/^\d+\s*[•·]\s*$/.test(u)&&!/^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+$/.test(u)).flatMap(u=>/^([가나다라마바사아자차카타파하]\.|[①-⑳]|\d{1,2}\.|-|※|<)/.test(u)?[u]:fs(u));if(!t.length)return[];const s=[];let n=[],a=[],r="";const o=()=>{if(!n.length)return;const u=n.join(" "),f=/[?？]$/.test(u.trim())?' class="legal-question-point"':"";s.push(`<p${f}>${q(u)}</p>`),n=[]},l=()=>{if(!a.length)return;const u=r==="hangul",f=r==="bullet",m=f?"ul":"ol",g=u?"legal-hangul-list":f?"legal-bullet-list":"legal-reasoning-list";s.push(`<${m} class="${g}">${a.map(h=>`<li>${q(h)}</li>`).join("")}</${m}>`),a=[],r=""},d=(u,f)=>{r&&r!==u&&l(),r=u,a.push(f)};return t.forEach((u,f)=>{const m=u.replace(/^<\s*([^>]+)\s*>$/,"$1").trim(),g=/^<\s*([^>]+)\s*>$/.test(u),h=m.match(/^([가나다라마바사아자차카타파하])\.\s*(.+)$/),w=m.match(/^(\d{1,2})\.\s+(.+)$/),A=m.match(/^([①-⑳])\s*(.+)$/),E=m.match(/^-\s*(.+)$/),y=m.match(/^※\s*(.+)$/),L=/^(?:[①-⑳]|\d{1,2}\.)\s*[∼~～]/.test(m),v=t[f+1]||"";if(L){o(),l(),s.push(`<p class="legal-note">${q(m)}</p>`);return}if(g||Wa(m,v)){o(),l(),s.push(`<h5>${q(m)}</h5>`);return}if(y){o(),l(),y[1].length<=20&&/(?:배경|참고|비고|권고사항)/.test(y[1])?s.push(`<h5>${q(y[1])}</h5>`):s.push(`<p class="legal-note">${q(y[1])}</p>`);return}if(h){o();const b=h[2].match(/^(질의[^.?]{0,40}(?:대하여|공통사항|결론))\s+(.+)$/);if(b){l(),s.push(`<h5>${q(`${h[1]}. ${b[1]}`)}</h5>`),fs(b[2]).forEach(k=>{n.push(k),o()});return}d("hangul",h[2]);return}if(w||A||E){o(),d(E?"bullet":"decimal",(w||A||E)[w||A?2:1]);return}const S=Ga(m);if(S.length>1){o(),S.forEach(b=>d("decimal",b));return}if(a.length){const b=a[a.length-1];if(!(/[.)”’]$/.test(b)&&/^(이 |그 |따라서|그러므로|한편|반면|결론적으로|대법원|헌법재판소)/.test(m))){a[a.length-1]=`${b} ${m}`;return}}l(),n.push(m),o()}),o(),l(),s}function Ka(e){return e.length?`<aside class="legal-footnotes">${e.map(s=>`<p><sup class="legal-fn-mark">${c(s.num)})</sup> ${q(s.text)}</p>`).join("")}</aside>`:""}function Ja(e){const t=String(e||"").replace(/<\s*관계\s*법령\s*>/g,`
`).replace(/\s*(※\s*법령정비\s*권고사항)\s*/g,`
$1
`).replace(/\s+((?:「[^」]+」|[가-힣A-Za-z0-9ㆍ·][가-힣A-Za-z0-9ㆍ·\s]{2,70}(?:법률|보호법|기본법|시행령|시행규칙|법))\s+제\d+조(?:의\d+)?\()/g,`
$1`).replace(/(제\d+조(?:의\d+)?\([^)]+\))\s+(?=[가-힣①-⑳])/g,`$1
`).replace(/\s+([①-⑳]\s*[∼~～]\s*[①-⑳]\s*\(생\s*략\))/g,`
$1`).replace(/\s+(\d{1,2}\s*[∼~～]\s*\d{1,2}\s*\(생\s*략\))/g,`
$1`).replace(/\s+([①-⑳])\s+/g,`
$1 `).replace(/\s+(\d{1,2})\.\s+/g,`
$1. `).replace(/\s+([가나다라마바사아자차카타파하])\.\s+/g,`
$1. `).split(/\n+/).map(a=>a.trim()).filter(Boolean);if(!t.length)return"";const s=[];t.forEach(a=>{const r=a.match(/^※\s*(.+)$/);if(r){s.push(`<h5>${q(r[1])}</h5>`);return}if(/^(관계 법령|법령정비 권고사항)$/.test(a)){s.push(`<h5>${q(a)}</h5>`);return}if(/제\d+조(?:의\d+)?\(/.test(a)){s.push(`<h5 class="legal-text-heading">${q(a)}</h5>`);return}if(/^[①-⑳]\s*[∼~～]/.test(a)||/^\d{1,2}\s*[∼~～]/.test(a)){s.push(`<p class="legal-note">${q(a)}</p>`);return}if(/^[①-⑳]/.test(a)){s.push(`<p class="legal-text-clause">${q(a)}</p>`);return}if(/^\d{1,2}\.\s*/.test(a)){s.push(`<p class="legal-text-item">${q(a)}</p>`);return}if(/^[가나다라마바사아자차카타파하]\.\s*/.test(a)){s.push(`<p class="legal-text-subitem">${q(a)}</p>`);return}s.push(`<p>${q(a)}</p>`)});const n=s.findIndex(a=>a.includes("legal-text-heading"));return n>=0&&s.splice(n,0,"<h5>관계 법령</h5>"),`<section class="legal-related-laws">${s.join("")}</section>`}function Tt(e){const{text:t,notes:s}=za(e),{body:n,appendix:a}=_a(t),r=Va(n),o=Ka(s),l=a?Ja(a):"";return!r.length&&!o&&!l?"":`<div class="legal-prose legal-reasoning-content">${r.join("")}${o}${l}</div>`}function Ie(e,t,s){const n=Tt(t);return n?`<section class="legal-reading-section is-${s}"><h4>${c(e)}</h4>${n}</section>`:""}function Wt(e,t=i.legalBasisCache?.[e]){if(!t||t.status==="idle")return'<p class="today-detail-note">관련 법령과 법령해석을 불러오는 중입니다.</p>';if(t.status==="loading")return'<p class="today-detail-note" role="status">법적 근거를 불러오는 중...</p>';if(t.status==="error")return`
      <p class="legal-error">법적 근거를 불러오지 못했습니다.</p>
      <button type="button" class="legal-retry" data-retry-legal="${c(e)}">다시 시도</button>
    `;const s=t.data||{},n=(s.laws||[]).map((g,h)=>{const w=ps(g.sourceUrl);return`
      <li class="legal-law-item">
        <div>
          <strong>${c(g.lawName||"관련 법령")}</strong>
          ${g.article?`<span>${c(g.article)}</span>`:""}
          ${g.articleTitle?`<small>${c(g.articleTitle)}</small>`:""}
          ${g.basisType==="COMMON_CERTIFICATION_BASIS"?'<em class="legal-basis-kind">제도 공통 근거</em>':""}
        </div>
        <div class="legal-law-actions">
          ${w?`<a class="legal-source-link" href="${c(w)}" target="_blank" rel="noopener noreferrer">법령 원문</a>`:""}
          ${g.articleText?`<button type="button" class="legal-article-open" data-open-law-article="${h}" data-law-control="${c(e)}">조문 내용 보기</button>`:'<span class="legal-article-unavailable">본문 없음</span>'}
        </div>
      </li>
    `}).join(""),a=(s.interpretations||[]).map(g=>{const h=ps(g.source?.originalUrl),w=g.warning||(g.temporalStatus==="REVIEW_REQUIRED"?"해석 이후 관련 법령이 개정되었을 수 있어 현재 적용 여부를 검토해야 합니다.":"");return`
      <details class="legal-interpretation-card">
        <summary>
          <span>
            <strong>${c(g.title||"법령해석례")}</strong>
            <small>${c(g.caseNumber||g.interpretationId||"")} · ${c(g.responseDate||"회신일 미상")}</small>
          </span>
          ${Number.isFinite(g.matchScore)?`<em>${c(g.matchLabel||"조문 일치")} · ${c(g.matchScore)}점</em>`:""}
        </summary>
        <div class="legal-interpretation-body">
          ${w?`<p class="legal-warning">${c(w)}</p>`:""}
          ${(g.matchReasons||[]).length?`<div class="legal-interpretation-meta"><b>이 통제와 연결된 이유</b><span>${g.matchReasons.map(c).join(" · ")}</span></div>`:""}
          <div class="legal-interpretation-reading">
            ${Ie("질의 요지",g.question,"question")}
            ${Ie("공식 회답",g.answer,"answer")}
            ${Ie("판단 이유",g.reasoning,"reason")}
          </div>
          ${h?`<div class="legal-interpretation-footer"><span>법령해석은 참고자료이며 현재 사실관계에 대한 적합 판정을 대신하지 않습니다.</span><a class="legal-source-link" href="${c(h)}" target="_blank" rel="noopener noreferrer">국가법령정보센터 원문 보기</a></div>`:""}
        </div>
      </details>
    `}).join(""),r=s.interpretationDataStatus==="NOT_CONFIGURED"?"법령해석 Open API 동기화가 아직 설정되지 않았습니다. 인증키 설정 후 수집하면 질의요지·회답·이유가 표시됩니다.":`현재 수집된 법령해석 ${Number(s.interpretationCorpusSize||0)}건 중 관련 조문이 정확히 일치하는 해석례가 없습니다.`,o=(s.casebookExamples||[]).map(g=>{const h=g.source||{};return`
      <details class="legal-interpretation-card legal-casebook-card">
        <summary>
          <span>
            <strong>${c(g.title||"개인정보 법령해석 사례")}</strong>
            <small>${c(h.document||"2023 개인정보 법령해석 사례 30선")} · ${c(g.sourcePage?`${g.sourcePage}쪽`:"페이지 미상")}</small>
          </span>
          <em>내용 보기</em>
        </summary>
        <div class="legal-interpretation-body">
          ${g.warning?`<p class="legal-warning">${c(g.warning)}</p>`:""}
          ${Ie("질의 요지",g.question,"question")}
          ${Ie("사례집 답변",g.answer,"answer")}
          ${g.reasoning?`<details class="legal-reasoning-more"><summary>판단 이유 자세히 보기</summary>${Tt(g.reasoning)}</details>`:""}
          <p class="legal-casebook-source">출처: ${c(h.provider||"개인정보보호위원회·한국인터넷진흥원")} · ${c(h.publishedAt||"2023-12")}</p>
        </div>
      </details>
    `}).join(""),l=(s.officialGuidance||[]).map(g=>`
    <details class="legal-interpretation-card legal-casebook-card official-guidance-card">
      <summary>
        <span>
          <span class="legal-source-badge">개인정보보호위원회 공식 안내서</span>
          <strong>${c(g.section||g.title||"관련 안내")}</strong>
          <small>${c(g.title||"")} · ${c(g.publishedAt||"")} · ${c((g.pages||[]).length?`${g.pages.join("–")}쪽`:"페이지 미상")}</small>
        </span>
        <em>내용 보기</em>
      </summary>
      <div class="legal-interpretation-body official-guidance-body">
        <p class="official-guidance-applicability">${c(g.applicability||"일반 개인정보처리자")}</p>
        ${Tt(g.summary||"")}
        ${(g.checkpoints||[]).length?`
          <section>
            <h4>이 통제에서 확인할 사항</h4>
            <ul>${g.checkpoints.map(h=>`<li>${c(h)}</li>`).join("")}</ul>
          </section>
        `:""}
      </div>
    </details>
  `).join(""),d=(s.interpretations||[]).length,u=(s.casebookExamples||[]).length,f=(s.officialGuidance||[]).length,m=(s.laws||[]).length;return`
    <div class="legal-resource-counts" aria-label="관련 자료 수">
      <span><b>법령</b> ${m}건</span>
      <span><b>법령해석</b> ${d}건</span>
      <span><b>공식 사례</b> ${u}건</span>
      <span><b>공식 안내서</b> ${f}건</span>
    </div>
    <section class="legal-law-section">
      <h4>관련 법령 <span>${m}건</span></h4>
      <ul class="legal-law-list">${n||"<li>구조화된 관련 조문이 없습니다.</li>"}</ul>
    </section>
    <section class="legal-interpretation-section">
      <h4>관련 법령해석 <span>${d}건</span></h4>
      ${a||`<p class="legal-empty-state">${c(r)}</p>`}
      <p class="legal-disclaimer">${c(s.disclaimer||"법령해석례는 진단 결과를 직접 확정하지 않습니다.")}</p>
    </section>
    ${o||l?`
      <section class="legal-reference-section">
        <h4>공식 참고자료 <span>${u+f}건</span></h4>
        ${o?`
          <details class="legal-resource-disclosure legal-casebook-section">
            <summary>
              <span><b>관련 공식 사례집</b><small>개인정보위·KISA의 공식 학습·참고 사례</small></span>
              <em>${u}건 보기</em>
            </summary>
            <div class="legal-resource-disclosure-body legal-reference-list">${o}</div>
          </details>
        `:""}
        ${l?`
          <details class="legal-resource-disclosure official-guidance-section">
            <summary>
              <span><b>관련 공식 안내서</b><small>일반 개인정보처리자용 실무 해설</small></span>
              <em>${f}건 보기</em>
            </summary>
            <div class="legal-resource-disclosure-body legal-reference-list">${l}</div>
          </details>
        `:""}
      </section>
    `:""}
    ${s.lastUpdatedAt?`<p class="legal-updated">법령 데이터 동기화: ${c(s.lastUpdatedAt)}</p>`:""}
  `}function Ya(){const e=Ba(),t=qa(),s=p("areaFilterGroup");if(s){const r=[{id:"all",label:"전체"},{id:"1",label:Y[1]},{id:"2",label:Y[2]},{id:"3",label:Y[3]}];s.innerHTML=r.map(o=>{const l=o.id==="all"?e.all:e[o.id]||0,d=o.id==="all"?`전체 ${l}개 통제`:`${t[o.id]||o.label} (${l}개)`;return`
        <button type="button" class="filter-btn${i.areaFilter===o.id?" active":""}" data-area-filter="${o.id}" title="${d}">
          ${o.label}<span class="filter-count">${l}</span>
        </button>
      `}).join("")}const n=Fa(),a=p("levelFilterGroup");if(a){const r=[{id:"all",label:"전체"},{id:"unknown",label:"미점검"},{id:"none",label:"미이행"},{id:"partial",label:"부분 이행"},{id:"done",label:"이행"},{id:"na",label:"해당 없음"}];a.innerHTML=r.map(o=>`
      <button type="button" class="filter-btn${i.levelFilter===o.id?" active":""}" data-level-filter="${o.id}">
        ${o.label}<span class="filter-count">${n[o.id]||0}</span>
      </button>
    `).join("")}}function Qa(e,{ensureChecks:t,ensureDomainChecks:s}){const n=x(e.id),a=t(e.id),r=i.inputConfidence?.[e.id]||"unknown",o=i.expandedRows.has(e.id),l=e.checklistItems||[],d=o?s(e.id,l):i.domainChecks[e.id]||{},u=l.map((y,L)=>{const v=String(L+1),S=!!d[v];return o?`
        <li class="domain-check-item">
          <label>
            <input type="checkbox" data-domain-control="${e.id}" data-domain-item="${v}"${S?" checked":""}>
            <span><strong>${v}.</strong> ${c(y)}</span>
          </label>
        </li>
      `:`<li><strong>${v}.</strong> ${c(y)}</li>`}).join(""),f=(e.recommendedActions||[]).map(y=>`<li>${c(y)}</li>`).join(""),m=(e.officialEvidenceExamples||[]).slice(0,6).map(y=>`<li>${c(y)}</li>`).join(""),g=zt(e.id),h=g.length?g.map(y=>`<li><strong>${c(y.title)}</strong>${y.url?` · ${c(y.url)}`:""}${y.note?` · ${c(y.note)}`:""}</li>`).join(""):"<li>등록된 증적 없음 (이행 판정에 필요)</li>",w=n==="evidenced"?"done":n,A=e.officialRequirement?`<div class="detail-block"><h3>인증기준 (안내서)</h3><p>${c(e.officialRequirement)}</p></div>`:"",E=o?`<div class="detail-block legal-basis-block">
          <h3>법적 근거 및 참고자료</h3>
          <p class="today-detail-note">공식 자료와 프로젝트의 통제 연결 결과를 구분하여 표시합니다.</p>
          <div data-legal-basis="${c(e.id)}">${Wt(e.id)}</div>
        </div>`:"";return`
      <div class="assess-row${o?" expanded":""}${w!=="unknown"&&w!=="na"?" is-reviewed":""}${w==="none"?" is-risk":""}" data-control="${e.id}">
        <div class="assess-row-head">
        <span class="assess-expand-icon" aria-hidden="true">▾</span>
          <div class="assess-row-text">
            <div class="assess-row-meta-line">
              <span class="assess-id">${e.id}</span>
              ${fn(w)}
              <label class="assess-confidence" title="이 통제 입력의 신뢰도 (모름/추정/확인됨)">
                신뢰도
                <select data-row-confidence="${c(e.id)}" aria-label="${c(e.id)} 입력 신뢰도">
                  <option value="unknown"${r==="unknown"?" selected":""}>모름</option>
                  <option value="assumed"${r==="assumed"?" selected":""}>추정</option>
                  <option value="confirmed"${r==="confirmed"?" selected":""}>확인됨</option>
                </select>
              </label>
            </div>
          <span class="assess-title" title="${e.areaName} / ${e.categoryName}">${e.title}</span>
          </div>
          <div class="audit-checks" aria-label="${e.id} 자체진단 체크 항목">
            ${Object.keys(K).map(y=>`
            <label class="audit-check" title="${e.id} ${Bs[y]}">
                <input type="checkbox" data-check-control="${e.id}" data-check-key="${y}"${a[y]?" checked":""}>
                <span>${K[y]}</span>
              </label>
            `).join("")}
          </div>
        </div>
        <div class="assess-row-body">
          <div class="assess-detail-grid">
            <div class="detail-block">
              <h3>주요 확인사항 (안내서)</h3>
              <p style="font-size:12px;color:var(--muted);margin:0 0 8px;">인증기준 안내서 주요 확인사항. 체크하면 해당 문항은 문제 근거에서 제외됩니다. 이행은 등록 증적이 있을 때만 가능합니다.</p>
              <ul class="domain-check-list">${u||"<li>항목 없음</li>"}</ul>
            </div>
            ${A}
            ${E}
            <div class="detail-block">
            <h3>미이행 시 취약점/심사 리스크</h3>
              <p>${c(e.riskIfMissing||"-")}</p>
            </div>
            <div class="detail-block">
              <h3>등록된 증적</h3>
              <p style="font-size:12px;color:var(--muted);margin:0 0 8px;">자가진단 상세 카드에서 링크/메모를 등록하세요.</p>
              <ul>${h}</ul>
            </div>
            ${m?`
              <div class="detail-block">
                <h3>증거자료 예시 (안내서)</h3>
                <ul>${m}</ul>
              </div>
            `:""}
            ${f?`
              <div class="detail-block">
                <h3>권장 조치</h3>
                <ul>${f}</ul>
              </div>
            `:""}
          </div>
        </div>
      </div>
  `}function Za(e,t,s){const n=p("assessRailFilterHint");if(n){if(!dn()){n.hidden=!0,n.innerHTML="";return}n.hidden=!1,n.innerHTML=`
    필터 적용 중 — 목록 <strong>${e}개</strong> /
    분류 트리 ${t}개 기준.
    <button type="button" id="resetAssessFiltersBtn">필터 초기화</button>
  `,n.querySelector("#resetAssessFiltersBtn")?.addEventListener("click",()=>{s()})}}function Ye(e,t){const s=p("assessCategoryNav");if(!s)return;const n=dn();if(!e.length){s.innerHTML='<p class="detail-empty">표시할 분류가 없습니다.</p>';return}const a=new Map;e.forEach(o=>{const l=o.areaId||"0";a.has(l)||a.set(l,{areaId:l,areaName:o.areaName||Y[l]||"기타",groups:[]}),a.get(l).groups.push(o)});const r=Array.from(a.values()).sort((o,l)=>Ce(o.areaId,l.areaId));s.innerHTML=r.map(o=>{const l=o.groups.reduce((f,m)=>f+m.controls.filter(g=>t.has(g.id)).length,0),d=o.groups.reduce((f,m)=>f+m.controls.length,0),u=n?`${l}/${d}`:String(d);return`
    <div class="assess-area-block">
      <div class="assess-area-label">
        <span>${Y[o.areaId]||o.areaName}</span>
        <span>${u}</span>
      </div>
      ${o.groups.map(f=>{const m=f.controls.filter(E=>t.has(E.id)).length,g=nt(f.controls),h=n&&m===0,w=i.activeCategoryId===f.categoryId?" active":"",A=n?`${m}/${f.controls.length}`:`${g.reviewed}/${g.total} (${g.pct}%)`;return`
          <button type="button" class="assess-nav-item${w}${h?" is-dimmed":""}" data-jump-category="${f.categoryId}" title="${c(f.categoryName)}${n?` — 필터 ${m}개`:` (${g.pct}%)`}">
            <strong>${f.categoryId} ${f.categoryName}</strong>
            <span class="assess-nav-meta">${A}</span>
          </button>
        `}).join("")}
    </div>
  `}).join(""),s.querySelectorAll("[data-jump-category]").forEach(o=>{o.addEventListener("click",()=>{const l=o.dataset.jumpCategory,u=(e.find(m=>m.categoryId===l)?.controls||[]).filter(m=>t.has(m.id));if(n&&!u.length){$("이 분류에는 현재 필터 조건에 맞는 통제가 없습니다.");return}i.activeCategoryId=l,i.collapsedCategories.delete(l);const f=document.querySelector(`[data-category-group="${l}"]`);f&&(f.classList.remove("collapsed"),f.scrollIntoView({behavior:"smooth",block:"start"})),Ye(e,t)})})}const H="/workspace",bt="/controls/map",G={sessions:{id:"sessions",path:H,title:"진단 관리"},scope:{id:"scope",path:`${H}/scope`,title:"점검 범위"},assessment:{id:"assessment",path:`${H}/assessment`,title:"자가진단",workspace:"assessment"},results:{id:"results",path:`${H}/results`,title:"진단 결과",workspace:"results"},evidence:{id:"evidence",path:`${H}/evidence`,title:"증적 관리",workspace:"evidence"},report:{id:"report",path:`${H}/report`,title:"보고서",workspace:"report"}};let gn=null;function Xa(e){gn=e}function mn(e){return String(e||"").replace(/\/+$/,"")||"/"}function ei(e){const t=mn(e);return t===bt||t.startsWith(`${bt}/`)?H+t.slice(bt.length):t}function ct(e=globalThis.location?.pathname){const t=ei(e);return t===`${H}/sessions`?G.sessions:t===`${H}/dashboard`?G.assessment:Object.values(G).find(s=>mn(s.path)===t)||null}function ce(e,t={}){gn?.(e,t)}function V(e){return i.controlChecks[e]||(i.controlChecks[e]=_t(i.assessments[e]||"unknown")),i.controlChecks[e]}function Vt(e,t){const s=t||[];if(i.domainChecks[e])s.forEach((n,a)=>{const r=String(a+1);r in i.domainChecks[e]||(i.domainChecks[e][r]=!1)});else{const n={},a=V(e),r=Object.keys(K);s.forEach((o,l)=>{const d=String(l+1),u=r[l];n[d]=u?!!a[u]:!1}),i.domainChecks[e]=n}return i.domainChecks[e]}function vn(e,t,s){const n=(i.checklist||[]).find(a=>a.id===e);Vt(e,n?.checklistItems||[]),i.domainChecks[e]||(i.domainChecks[e]={}),i.domainChecks[e][String(t)]=!!s,i.domainTouched[e]=!0,me()}function hn(){const e={};return Object.keys(i.domainTouched||{}).forEach(t=>{i.domainChecks[t]&&(e[t]=i.domainChecks[t])}),Object.keys(e).length?e:null}function ti(e){(i.inputConfidence?.[e]||"unknown")==="unknown"&&(i.inputConfidence[e]="assumed")}function Ae(e,t){const s=i.assessments[e],n=en(t,e);if(i.controlChecks[e]=n,s==="na"){i.assessments[e]="na";return}i.assessments[e]=Xs(n,e),i.assessments[e]!=="unknown"&&ti(e)}function si(e){const t=new Set((e.applicabilityNotes||[]).map(s=>s.controlId).filter(Boolean));Object.keys(i.assessments).forEach(s=>{i.assessments[s]==="na"&&!t.has(s)&&(i.assessments[s]="unknown")}),t.forEach(s=>{i.assessments[s]="na"})}let W={},Rt=null;function ni(e){try{const t=new URL(e||"");return t.protocol==="https:"&&["law.go.kr","www.law.go.kr"].includes(t.hostname)?t.href:""}catch{return""}}function ai(e){return String(e||"").split(/\n+/).map(t=>t.trim()).filter(Boolean).map(t=>{const s=c(t);return/^제\d+조(?:의\d+)?(?:\(|$)/.test(t)?`<h3 class="legal-text-heading">${s}</h3>`:/^[①②③④⑤⑥⑦⑧⑨⑩]/.test(t)?`<p class="legal-text-clause">${s}</p>`:/^\d+[.．]\s*/.test(t)?`<p class="legal-text-item">${s}</p>`:/^[가-하][.．]\s*/.test(t)?`<p class="legal-text-subitem">${s}</p>`:`<p>${s}</p>`}).join("")}function ii(){let e=document.querySelector("#lawArticleDialog");return e||(e=document.createElement("dialog"),e.id="lawArticleDialog",e.className="app-modal legal-article-dialog",e.setAttribute("aria-labelledby","lawArticleDialogTitle"),e.innerHTML=`
    <div class="app-modal-shell legal-dialog-shell">
      <header class="app-modal-header legal-dialog-header">
        <div>
          <span class="legal-dialog-eyebrow">관련 법령 조문</span>
          <h2 id="lawArticleDialogTitle"></h2>
          <p class="legal-dialog-subtitle"></p>
        </div>
        <button type="button" class="app-modal-close legal-dialog-close" data-law-dialog-close aria-label="조문 창 닫기">×</button>
      </header>
      <div class="app-modal-scroll legal-dialog-scroll">
        <div class="legal-dialog-meta" aria-label="법령 정보"></div>
        <article class="legal-dialog-body"></article>
        <footer class="legal-dialog-footer"></footer>
      </div>
    </div>
  `,e.querySelector("[data-law-dialog-close]").addEventListener("click",()=>e.close()),e.addEventListener("click",t=>{t.target===e&&e.close()}),e.addEventListener("close",()=>{Rt?.focus(),Rt=null}),document.body.append(e),e)}function ri(e,t,s){const n=i.legalBasisCache?.[e]?.data?.laws?.[t];if(!n?.articleText){$("표시할 조문 본문이 없습니다.");return}const a=ii(),r=[n.lawName||"관련 법령",n.article].filter(Boolean).join(" "),o=[n.documentType,n.currentStatus,n.effectiveDate?`시행 ${n.effectiveDate}`:"",n.ministry,n.basisType==="COMMON_CERTIFICATION_BASIS"?"제도 공통 근거":"통제 직접 근거"].filter(Boolean),l=ni(n.sourceUrl);a.querySelector("#lawArticleDialogTitle").textContent=r,a.querySelector(".legal-dialog-subtitle").textContent=n.articleTitle||"현행 조문 본문",a.querySelector(".legal-dialog-meta").innerHTML=o.map(d=>`<span>${c(d)}</span>`).join(""),a.querySelector(".legal-dialog-body").innerHTML=ai(n.articleText),a.querySelector(".legal-dialog-footer").innerHTML=l?`<a class="legal-dialog-source" href="${c(l)}" target="_blank" rel="noopener noreferrer">국가법령정보센터에서 원문 보기 ↗</a>`:"",Rt=s,a.showModal()}function oi(e){e.querySelectorAll("[data-open-law-article]").forEach(t=>{t.addEventListener("click",()=>{ri(t.dataset.lawControl,Number(t.dataset.openLawArticle),t)})})}async function at(e,{force:t=!1}={}){const s=i.legalBasisCache?.[e];if(!t&&s?.status==="ready"){wt(e);return}if(!(!t&&s?.status==="loading")){i.legalBasisCache[e]={status:"loading"},wt(e);try{const n=await ke(`/controls/${encodeURIComponent(e)}/legal-basis`);i.legalBasisCache[e]={status:"ready",data:n}}catch(n){i.legalBasisCache[e]={status:"error",error:String(n?.message||n)}}wt(e)}}function wt(e){const t=document.querySelector(`[data-legal-basis="${CSS.escape(e)}"]`);t&&(t.innerHTML=Wt(e),t.querySelector("[data-retry-legal]")?.addEventListener("click",()=>{at(e,{force:!0})}),oi(t))}function li(e){W={...e}}function Ne(e){me(),Kt(),di(e),i.analysis?(W.renderConfirmationActions(i.analysis),W.renderStats(),W.markAnalysisStale?.()):i.currentView==="assess"&&xe()}function yn(e,t,s){if(t==="evidence"&&s&&!Q(e)){$("증적 링크/메모를 먼저 등록하세요."),Ne(e);return}if(t==="evidence"&&!s&&Q(e)){$("등록된 증적이 있습니다. 목록에서 삭제한 뒤 해제하세요."),Ne(e);return}const n={...V(e),[t]:s};Ae(e,n),Ne(e)}function gs(e,t,{quiet:s=!1}={}){return ca(e,t).ok?(Ae(e,{...V(e),evidence:!0}),i.sessionSelectedControlId=e,Ne(e),s||$(`${e} 증적을 등록했습니다.`),!0):($("증적 제목을 입력하세요."),!1)}function ci(e,t){return da(e,t),Ae(e,{...V(e),evidence:Q(e)}),i.sessionSelectedControlId=e,Ne(e),$(Q(e)?"증적을 삭제했습니다.":"증적을 삭제해 부분 이행으로 조정됩니다."),!0}function di(e){const t=document.querySelector(`#assessList .assess-row[data-control="${e}"]`);if(!t){i.currentView==="assess"&&xe();return}const s=x(e),n=V(e);t.classList.toggle("is-reviewed",s!=="unknown"&&s!=="na"),t.classList.toggle("is-risk",s==="none");const a=t.querySelector(".assess-row-meta-line .status-pill");if(a){const o=document.createElement("div");o.innerHTML=fn(s),a.replaceWith(o.firstElementChild)}Object.keys(K).forEach(o=>{const l=t.querySelector(`input[data-check-control="${e}"][data-check-key="${o}"]`);l&&(l.checked=!!n[o])});const r=t.closest(".assess-category-group");if(r){const o=[...r.querySelectorAll(".assess-row")].map(g=>g.dataset.control),l=o.length,d=o.filter(g=>x(g)!=="unknown").length,u=l?Math.round(d/l*100):0,f=r.querySelector(".assess-category-progress strong"),m=r.querySelector(".assess-category-bar i");f&&(f.textContent=`${d}/${l}`),m&&(m.style.width=`${u}%`)}}function bn(e){const t=lt();return t.length?(t.forEach(s=>{Ae(s.id,e(V(s.id)))}),me(),Kt(),xe(),t.length):($("현재 필터에 해당하는 통제가 없습니다."),0)}function ui(e,t){const s=bn(n=>{const a={...n,[e]:t};return e!=="reviewed"&&t&&(a.reviewed=!0),e==="reviewed"&&!t&&(a.policy=!1,a.implemented=!1,a.evidence=!1),e==="evidence"&&t&&(a.policy=!0,a.implemented=!0),a});s&&$(`${K[e]} ${t?"체크":"해제"}: ${s}개`)}function pi(e){const s={all:{reviewed:!0,policy:!0,implemented:!0,evidence:!0},none:{reviewed:!1,policy:!1,implemented:!1,evidence:!1},reviewed:{reviewed:!0,policy:!1,implemented:!1,evidence:!1}}[e];if(!s)return;const n=bn(()=>({...s}));if(!n)return;$(`${{all:"전체 체크",none:"전체 해제",reviewed:"검토만 체크"}[e]}: ${n}개`)}function fi({keepArea:e=!0}={}){i.levelFilter="all",i.assessSearch="",p("assessSearch")&&(p("assessSearch").value=""),e||(i.areaFilter="all"),i.categoriesBootstrapped=!1,xe()}function gi(e){const t=lt();if(!t.length)return{checked:!1,indeterminate:!1};const s=t.filter(n=>V(n.id)[e]).length;return{checked:s===t.length,indeterminate:s>0&&s<t.length}}function mi(){const e=lt(),t=p("assessFilterSummary"),s=p("assessColBulk");if(!t||!s)return;const n=i.areaFilter==="all"?"전체 영역":Y[i.areaFilter]||`영역 ${i.areaFilter}`,a=i.levelFilter==="all"?"전체 상태":U[i.levelFilter],r=i.assessSearch.trim()?` / 검색 "${i.assessSearch.trim()}"`:"";t.innerHTML=`<strong>${e.length}개</strong> 표시 / ${n} / ${a}${r}`,s.innerHTML=Object.keys(K).map(o=>`
    <label class="bulk-check-toggle" title="현재 목록 ${K[o]} 전체">
      <input type="checkbox" data-bulk-check="${o}">
      <span>${K[o]} 전체</span>
    </label>
  `).join(""),s.querySelectorAll("[data-bulk-check]").forEach(o=>{const l=o.dataset.bulkCheck,d=gi(l);o.checked=d.checked,o.indeterminate=d.indeterminate,o.addEventListener("change",()=>{ui(l,o.checked)})})}function Kt(){const e=p("assessProgressLabel"),t=p("assessProgressPct"),s=p("assessProgressFill"),n=p("levelSummary");if(!e&&!t&&!s&&!n)return;const a=i.checklist.length?i.checklist.filter(d=>{const u=x(d.id);return u!=="unknown"&&u!=="na"}).length:un(),r=i.checklist.length?i.checklist.filter(d=>x(d.id)!=="na").length:pn(),o=r?Math.round(a/r*100):0;e&&(e.textContent=`응답 진행: ${a} / ${r}`),t&&(t.textContent=`${o}%`),s&&(s.style.width=`${o}%`);const l=Object.keys(U).reduce((d,u)=>(d[u]=0,d),{});(i.checklist.length?i.checklist:i.allControls).forEach(d=>{const u=x(d.id);l[u]=(l[u]||0)+1}),n&&(n.innerHTML=Object.keys(U).map(d=>`
      <div class="level-summary-item">
        <span class="level-${d}">${U[d]}</span>
        <strong>${l[d]||0}</strong>
      </div>
    `).join(""))}function vi(e){return Qa(e,{ensureChecks:V,ensureDomainChecks:Vt})}function ms(e,t){Za(e,t,()=>{fi({keepArea:!0})})}function xe(){const e=p("assessList");if(!e)return;Ya(),mi();const t=Lt(us());if(!i.checklist.length){e.innerHTML='<p class="detail-empty">체크리스트를 불러오는 중...</p>',ms(0,0),Ye([],new Set);return}const s=lt(),n=new Set(s.map(r=>r.id));if(ms(s.length,us().length),!s.length){e.innerHTML='<p class="detail-empty">조건에 맞는 통제가 없습니다. 영역/상태 필터 또는 검색어를 바꿔 보세요.</p>',Ye(t,n);return}const a=Lt(s);!i.categoriesBootstrapped&&t.length&&(i.collapsedCategories=new Set(t.slice(1).map(r=>r.categoryId)),i.activeCategoryId=t[0].categoryId,i.categoriesBootstrapped=!0),Ye(t,n),e.innerHTML=a.map((r,o)=>{const l=nt(r.controls),d=i.collapsedCategories.has(r.categoryId);return`
      <section class="assess-category-group${d?" collapsed":""}" data-category-group="${r.categoryId}" style="animation-delay:${Math.min(o*.02,.2)}s">
        <button type="button" class="assess-category-head" data-toggle-category="${r.categoryId}" aria-expanded="${d?"false":"true"}">
          <span class="assess-category-id">${r.categoryId}</span>
          <span class="assess-category-title">
            <strong>${r.categoryName}</strong>
            <span>${r.areaName} / ${r.controls.length}개 통제</span>
          </span>
          <span class="assess-category-progress">
            <strong>${l.reviewed}/${l.total}</strong>
            <span class="assess-category-bar" aria-hidden="true"><i style="width:${l.pct}%"></i></span>
          </span>
          <span class="assess-category-chevron" aria-hidden="true">▾</span>
        </button>
        <div class="assess-category-body">
          <div class="assess-category-grid">
            ${r.controls.map(u=>vi(u)).join("")}
          </div>
        </div>
      </section>
    `}).join(""),e.querySelectorAll("[data-toggle-category]").forEach(r=>{r.addEventListener("click",()=>{const o=r.dataset.toggleCategory,l=r.closest(".assess-category-group"),d=!i.collapsedCategories.has(o);d?i.collapsedCategories.add(o):i.collapsedCategories.delete(o),i.activeCategoryId=o,l&&l.classList.toggle("collapsed",d),r.setAttribute("aria-expanded",d?"false":"true"),document.querySelectorAll("#assessCategoryNav [data-jump-category]").forEach(u=>{u.classList.toggle("active",u.dataset.jumpCategory===o)})})}),e.querySelectorAll(".assess-row-head").forEach(r=>{r.addEventListener("click",o=>{if(o.target.closest("label.audit-check, input[type=checkbox], .domain-check-item, .assess-confidence, select[data-row-confidence]"))return;const d=r.closest(".assess-row").dataset.control,u=!i.expandedRows.has(d);u?i.expandedRows.add(d):i.expandedRows.delete(d),xe(),u&&at(d)})}),e.querySelectorAll("[data-legal-basis]").forEach(r=>{at(r.dataset.legalBasis)}),e.querySelectorAll("[data-row-confidence]").forEach(r=>{r.addEventListener("click",o=>o.stopPropagation()),r.addEventListener("change",o=>{o.stopPropagation();const l=r.getAttribute("data-row-confidence");l&&(i.inputConfidence[l]=r.value,me(),$(`${l} 신뢰도를 ${Qn[r.value]||r.value}로 저장했습니다.`),i.analysis&&W.renderConfirmationActions(i.analysis))})}),e.querySelectorAll("[data-check-control]").forEach(r=>{r.addEventListener("click",o=>{o.stopPropagation()}),r.addEventListener("change",o=>{o.stopPropagation(),yn(r.dataset.checkControl,r.dataset.checkKey,r.checked)})}),e.querySelectorAll("[data-domain-control]").forEach(r=>{r.addEventListener("click",o=>o.stopPropagation()),r.addEventListener("change",o=>{o.stopPropagation(),vn(r.dataset.domainControl,r.dataset.domainItem,r.checked)})})}async function hi(e=null){const t=e||await ke("/controls/checklist");i.checklist=t.controls;const s=JSON.stringify([i.assessments,i.controlChecks]);i.checklist.forEach(n=>{n.id in i.assessments||(i.assessments[n.id]="unknown"),V(n.id)}),s!==JSON.stringify([i.assessments,i.controlChecks])&&me(),Kt(),xe()}function yi(e,t){let s=t==="evidenced"?"done":t,n=!1;s==="done"&&!Q(e)&&(s="partial",n=!0),i.pendingDoneEvidenceControlId=null,Ae(e,_t(s)),s==="done"&&Ae(e,{...V(e),evidence:!0}),s==="unknown"?i.inputConfidence[e]="unknown":i.inputConfidence[e]="confirmed",i.sessionSelectedControlId=e,me(),$(n?"증적 없이 부분 이행으로 저장했습니다.":`${e} 진단: ${U[s]||s}`),i.analysis&&(W.renderConfirmationActions(i.analysis),W.renderStats(),W.markAnalysisStale?.())}function wn(){const e=p("reportReturnBar");if(!e)return;const t=i.reportReturn;if(e.hidden=!t,!t)return;const s=p("reportReturnTitle"),n=p("reportReturnStatus");if(s){const a=[t.controlId,t.controlTitle].filter(Boolean).join(" ");s.textContent=[t.itemTitle,a].filter(Boolean).join(" · ")}n&&(n.textContent=i.analysisStale?"진단이 변경되었습니다. 돌아간 뒤 확인 목록을 갱신하세요.":"이 통제를 점검한 뒤 원래 카드로 돌아갈 수 있습니다.")}function bi(e){const t=(e?document.querySelector(`.session-detail-card[data-today-control="${CSS.escape(e)}"]`):null)||document.querySelector(".session-detail-card")||p("sessionDetailPane");if(!t||((t.querySelector(".today-card-top")||t.querySelector(".today-question")||t).scrollIntoView({behavior:"smooth",block:"start"}),!e))return;const n=p("sessionMasterTree"),a=n?.querySelector(`[data-select-control="${CSS.escape(e)}"]`);if(a&&n){const r=a.offsetTop,o=r+a.offsetHeight,l=n.scrollTop,d=l+n.clientHeight;(r<l||o>d)&&(n.scrollTop=Math.max(0,r-n.clientHeight/3))}}async function $n(e){if(e){if(i.analysis&&i.organizationProfile){i.sessionSelectedControlId=e,W.switchView?.("analyze"),W.switchAnalyzeSection?.("actions");const t=p("analyzeContent");t&&(t.style.display=""),W.renderConfirmationActions?.(i.analysis),wn(),window.requestAnimationFrame(()=>{window.setTimeout(()=>bi(e),80)});return}ce("assessment"),$("먼저 점검 범위를 적용하고 진단을 시작하세요.")}}function dt(){return{headcountBand:p("profileHeadcount")?.value||Pe.headcountBand,industry:p("profileIndustry")?.value||Pe.industry,piiVolume:p("profilePiiVolume")?.value||Pe.piiVolume,usesCloud:!!p("profileCloud")?.checked,hasOnPremFacility:!!p("profileOnPrem")?.checked,usesOutsourcing:!1,usesRemoteAccess:!1,processesRrn:!1}}function it(e=dt()){return!!(e?.usesCloud||e?.hasOnPremFacility)}function wi(e){const t={...Pe,...e||{}};p("profileHeadcount")&&(p("profileHeadcount").value=t.headcountBand||"1-50"),p("profileIndustry")&&(p("profileIndustry").value=t.industry||"technology"),p("profilePiiVolume")&&(p("profilePiiVolume").value=t.piiVolume||"low"),p("profileCloud")&&(p("profileCloud").checked=!!t.usesCloud),p("profileOnPrem")&&(p("profileOnPrem").checked=!!t.hasOnPremFacility)}function Sn(e){const t=e||dt();return t.usesCloud&&!t.hasOnPremFacility?["바뀌는 결과: 물리/전산실 통제 6개(2.4.1~2.4.6)만 N/A.","나머지 통제는 그대로 점검 대상입니다."]:t.usesCloud&&t.hasOnPremFacility?["바뀌는 결과: 물리 통제도 점검 대상(N/A 없음).","클라우드·전산실을 함께 운영하는 범위로 둡니다."]:!t.usesCloud&&t.hasOnPremFacility?["바뀌는 결과: 자체 전산실 기준으로 물리 통제를 점검.","N/A 규칙은 적용되지 않습니다."]:["운영 환경을 아직 고르지 않았습니다.","클라우드 또는 자체 인프라를 하나 이상 선택하세요."]}function kn(){const e=p("profileImpact");if(!e)return;const t=dt(),s=it(t),n=i.checklist?.length||101,a=s&&t.usesCloud&&!t.hasOnPremFacility?6:0,r=Sn(t).map(o=>`<li>${c(o)}</li>`).join("");e.classList.toggle("is-incomplete",!s),e.innerHTML=s?`
    <div class="profile-impact-head"><span>적용 결과</span><em>${a?`${a}개 통제 제외`:"전체 통제 적용"}</em></div>
    <strong>${a?"운영 환경에 맞춰 범위를 조정했습니다":"전체 통제를 점검합니다"}</strong>
    <dl class="profile-impact-metrics">
      <div><dt>전체 통제</dt><dd>${n}</dd></div>
      <div><dt>적용</dt><dd>${Math.max(n-a,0)}</dd></div>
      <div><dt>N/A</dt><dd>${a}</dd></div>
    </dl>
    <div class="profile-impact-bar" aria-label="적용 통제 ${Math.max(n-a,0)}개"><i style="width:${n?Math.round((n-a)/n*100):0}%"></i></div>
    <ul>${r}</ul>`:`
    <div class="profile-impact-head"><span>적용 결과</span><em>환경 미선택</em></div>
    <strong>운영 환경을 선택하세요</strong>
    <ul>${r}</ul>`,$i(s)}function $i(e=it()){const t=p("applyProfileBtn");t&&(t.disabled=!e)}function Be(){const e=p("view-assess");if(!e)return;const t=!!i.organizationProfile;e.classList.toggle("is-prestart",!t),e.classList.toggle("is-ready",t)}function Pt({focus:e=!0}={}){const t=p("profileInline");t&&(t.classList.add("open"),wi(i.organizationProfile),p("profileForm").style.display="",p("profileLede").style.display="",p("profileTitle").textContent=i.organizationProfile?"진단 환경 수정":"현재 운영 환경을 선택하세요",kn(),e&&(t.scrollIntoView({behavior:"smooth",block:"start"}),window.setTimeout(()=>p("profileCloud")?.focus(),0)),Be())}function Cn(){const e=p("profileInline");if(e){if(!i.organizationProfile){e.classList.add("open"),Be();return}e.classList.remove("open"),Be()}}function Jt(){const e=p("profileContextPanel");if(!e)return;if(!i.organizationProfile){e.innerHTML='<strong>아직 점검 범위 설정 전입니다.</strong><div class="profile-context-chips"><span>클라우드만 쓰면 물리 6개가 N/A가 됩니다.</span></div>';return}const t=i.organizationProfile,s=Sn(t),n=[t.usesCloud&&!t.hasOnPremFacility?"물리 6개 N/A":null,t.usesCloud?"클라우드":null,t.hasOnPremFacility?"자체전산실":null,!t.usesCloud&&!t.hasOnPremFacility?"N/A 없음":null].filter(Boolean);e.innerHTML=`
    <strong>현재 점검 범위</strong>
    <div class="profile-context-chips">${n.map(a=>`<span>${c(String(a))}</span>`).join("")}</div>
    <p class="panel-desc" style="margin:8px 0 0;">${c(s[0]||"")}</p>
  `}function Si(){const e=(i.checklist||[]).filter(s=>x(s.id)!=="na");return{reviewed:e.filter(s=>{const n=x(s.id);return n!=="unknown"&&n!=="na"}).length,applicable:e.length}}function Ge(){return(i.checklist||[]).filter(e=>x(e.id)!=="na")}function An(){return Ge().filter(e=>x(e.id)==="unknown")}function En(){return Ge().filter(e=>{const t=x(e.id);return t==="done"||t==="evidenced"})}function xn(){const e=new Set(["unknown","none","partial"]);return Ge().filter(t=>e.has(x(t.id)))}function ki(e=[]){const t=new Set(e),s={unknown:0,none:1,partial:2};return xn().filter(n=>!t.has(n.id)).sort((n,a)=>(s[x(n.id)]??9)-(s[x(a.id)]??9)||String(n.id).localeCompare(String(a.id)))}function Oe(){return Lt(Ge())}function vs(e=null){const t=xn().sort((a,r)=>Ce(a.id,r.id));if(!t.length)return null;if(!e)return t[0].id;const s=t.findIndex(a=>a.id===e);return s>=0&&s+1<t.length?t[s+1].id:t.find(a=>Ce(a.id,e)>0)?.id||t[0].id}function rt(){return Ge().slice().sort((e,t)=>Ce(e.id,t.id)).map(e=>e.id)}function Mt(e,t=1){const s=rt();if(!s.length)return null;const n=s.indexOf(e);if(n<0)return t>0?s[0]:s[s.length-1];const a=n+t;return a<0||a>=s.length?null:s[a]}const hs={critical:"심각도 매우 높음",high:"심각도 높음",medium:"심각도 보통"},ys=[{min:80,key:"ready",label:"준비 완료",hint:"핵심 영역이 준비 완료 구간에 들어왔습니다."},{min:55,key:"rising",label:"안정화",hint:"핵심 영역이 안정화되고 있습니다. 남은 보완 항목을 이어서 확인하세요."},{min:25,key:"warming",label:"점검 중",hint:"진단이 진행 중입니다. 다음 통제를 점검하면 온도가 올라갑니다."},{min:0,key:"cold",label:"초기 단계",hint:"아직 점검 초반입니다. 미점검 통제부터 이어서 확인하세요."}];function Ci(e={}){const t=Object.values(e).filter(Array.isArray);return{itemCount:t.reduce((s,n)=>s+n.length,0),controlCount:t.filter(s=>s.length>0).length}}function Ai(e){return e==="done"||e==="evidenced"?1:e==="partial"?.5:0}function ie(e){const t=Number(e);return Number.isFinite(t)?Math.max(0,Math.min(100,Math.round(t))):0}function Ln({done:e=0,partial:t=0,applicable:s=0}={}){return s<=0?0:ie((Number(e)+Number(t)*.5)/s*100)}function Ei({done:e=0,partial:t=0,none:s=0,applicable:n=0}={}){const a=Math.max(0,Number(e)+Number(t)+Number(s)),r=Math.max(0,Number(n)),o=r?ie(a/r*100):0,l=a?ie((Number(e)+Number(t)*.5)/a*100):null;return{reviewed:a,total:r,coverage:o,confirmedReadiness:l,confidence:o>=80?"high":o>=40?"medium":"low"}}function Yt(e){const t=ie(e);return ys.find(s=>t>=s.min)||ys.at(-1)}function xi(e=[],t=()=>"unknown"){const s=new Map;return e.forEach(n=>{const a=String(n.areaId||n.categoryId?.split(".")[0]||"0");s.has(a)||s.set(a,{areaId:a,label:Y[a]||n.areaName||`영역 ${a}`,controls:[]}),s.get(a).controls.push(...n.controls||[])}),Array.from(s.values()).sort((n,a)=>String(n.areaId).localeCompare(String(a.areaId),"en",{numeric:!0})).map(n=>{const a=n.controls.length,r=n.controls.filter(f=>{const m=t(f.id);return m!=="unknown"&&m!=="na"}).length,o=n.controls.reduce((f,m)=>f+Ai(t(m.id)),0),l=a?ie(o/a*100):0,d=r?ie(o/r*100):null,u=n.controls.find(f=>["unknown","none","partial"].includes(t(f.id)));return{areaId:n.areaId,label:n.label,temperature:l,confirmedReadiness:d,coverage:a?ie(r/a*100):0,band:Yt(l),reviewed:r,total:a,nextControlId:u?.id||""}})}function Li(e={}){const t=[];e.scenarioRelevant&&t.push("선택 시나리오 직접 관련"),e.level==="none"?t.push("미이행 우선"):e.level==="partial"&&t.push("부분 이행 보완 필요"),hs[e.severity]&&t.push(hs[e.severity]);const s=Array.isArray(e.profileRelevance)?e.profileRelevance[0]:"";return s&&t.push(`조직 조건 반영: ${s}`),t.slice(0,3)}function Ii(e,t=null,s=[]){const n=t||s[0]||null;return e.levelFilter="weak",e.sessionSelectedControlId=n,n}function Ti({analysis:e,controlEvidence:t={},weakControlIds:s=[],stale:n=!1,groups:a=[],getLevel:r=()=>"unknown",nextControls:o=[],done:l=0,partial:d=0,applicable:u=0}={}){const f=Ci(t),m=[...new Set(s.map(String))],g=m.filter(b=>Array.isArray(t[b])&&t[b].length>0).length,h=Math.max(m.length-g,0),w=Ln({done:l,partial:d,applicable:u}),A=Ei({done:l,partial:d,none:m.filter(b=>r(b)==="none").length,applicable:u}),E=Yt(w),y=xi(a,r),L=[...y].sort((b,k)=>b.temperature-k.temperature)[0]||null,v=n?[]:(e?.topGaps||[]).slice(0,3).map((b,k)=>({rank:k+1,controlId:b.controlId||b.id||"",title:b.title||b.controlTitle||"우선 보완 통제",risk:b.riskIfMissing||"미흡 시 영향을 확인하고 보완 계획을 수립하세요.",selectionReasons:Li(b),mode:"gap"})),S=v.length?[]:o.slice(0,3).map((b,k)=>{const I=b.level||r(b.id)||"unknown";return{rank:k+1,controlId:b.id||b.controlId||"",title:b.title||"다음 점검 통제",risk:"이 통제를 진단하면 준비 온도가 올라갑니다.",selectionReasons:[U[I]||"미점검","다음 점검 대상"],mode:"queue",weak:I==="none"||I==="partial"}});return{stale:n,temperature:w,band:E,summary:A,areas:y,coolest:L,queueMode:!v.length,priorities:v.length?v:S,evidence:f,signals:[{label:"증적 미등록",value:h,suffix:"개",help:`보완 대상 ${m.length}개 중 ${g}개 통제에 증적이 등록되어 있습니다.`},{label:"등록 증적",value:f.itemCount,suffix:"건",help:f.itemCount?`${f.controlCount}개 통제에 증적이 연결되어 있습니다.`:"아직 등록된 증적이 없습니다. 판단 근거를 남기면 여기에 모입니다."}],categories:n?[]:(e?.gapClusters||[]).slice(0,4).map(b=>({label:b.theme||"미흡 통제 묶음",gapCount:Number(b.gapCount||0),controlId:String(b.controlIds?.[0]||b.primaryControl?.controlId||"")}))}}const Ri=[{id:"unknown",label:"미확인"},{id:"none",label:"미이행"},{id:"partial",label:"부분 이행"},{id:"done",label:"이행"}];function Pi({remaining:e=0,remediationCount:t=0}={}){return e>0?{title:"아직 진단하지 않은 통제가 있습니다.",help:"미점검 항목을 이어서 진단하면 준비 온도와 보완 대상이 더 정확해집니다.",actionAttr:"data-progress-next",actionLabel:"다음 미점검 통제",recCount:e,recLabel:"미점검 대상",recHelp:"우선순위가 높은 통제부터 현재 운영 상태를 확인하세요.",recItems:["미점검 통제 진단하기","판단 근거가 되는 증적 연결"]}:t>0?{title:"보완이 필요한 통제가 있습니다.",help:"부분 이행 항목을 중심으로 증적과 조치 상태를 우선 검토하세요.",actionAttr:"data-progress-weak",actionLabel:"우선 통제 검토",recCount:t,recLabel:"보완 대상",recHelp:"우선순위가 높은 통제부터 증적과 조치 상태를 확인하세요.",recItems:["부족한 증적 보완","개선 조치 계획 수립"]}:{title:"준비 상태가 안정권에 도달했습니다.",help:"적용 통제 진단을 모두 반영했습니다. 증적과 보고서를 이어서 확인하세요.",actionAttr:"",actionLabel:"",recCount:0,recLabel:"보완 대상 없음",recHelp:"등록한 증적과 보고서를 이어서 확인하세요.",recItems:["등록 증적 점검","진단 보고서 확인"]}}let bs=!1;function Mi(){return i.levelFilter!=="all"||!!i.assessSearch.trim()||i.areaFilter!=="all"}function In(e){const t=i.assessSearch.trim().toLowerCase();return e.map(s=>({...s,controls:s.controls.filter(n=>{if(i.areaFilter!=="all"&&String(n.areaId)!==String(i.areaFilter))return!1;const a=x(n.id);return i.levelFilter==="weak"&&!["none","partial"].includes(a)||!["all","weak"].includes(i.levelFilter)&&a!==i.levelFilter?!1:t?ln(n,i.assessSearch):!0})})).map(s=>({...s,controls:cn(s.controls,i.assessSearch)})).filter(s=>s.controls.length)}function Ni(){document.querySelectorAll("[data-session-level]").forEach(t=>{const s=t.getAttribute("data-session-level")===(i.levelFilter||"all");t.classList.toggle("is-active",s)});const e=p("sessionSearch");e&&e.value!==(i.assessSearch||"")&&(e.value=i.assessSearch||"")}function De(){if(!i.analysis)return;const e=z._hooks||{};Mn(i.analysis,{diagnoseControl:e.diagnoseControl,markAnalysisStale:e.markAnalysisStale})}function Di(){if(bs)return;const e=p("sessionMasterTools");e&&(bs=!0,p("sessionSearch")?.addEventListener("input",t=>{i.assessSearch=t.target.value||"",De()}),e.querySelectorAll("[data-session-level]").forEach(t=>{t.addEventListener("click",()=>{const s=t.getAttribute("data-session-level")||"all";i.levelFilter=s,De()})}),e.querySelectorAll("[data-session-bulk-preset]").forEach(t=>{t.addEventListener("click",()=>{const s=t.getAttribute("data-session-bulk-preset");s&&(pi(s),De(),z._hooks?.markAnalysisStale?.())})}))}function Qt(e=[]){const t=new Map;return e.forEach(s=>{s?.controlId&&(s.slotId||String(s.actionId||"").startsWith("evidence-")||t.has(s.controlId)||t.set(s.controlId,s))}),t}function Tn(e=[]){return e.filter(t=>{if(!t?.controlId||t.slotId||String(t.actionId||"").startsWith("evidence-"))return!1;const s=x(t.controlId);return s!=="done"&&s!=="evidenced"&&s!=="na"}).slice(0,10).map(t=>t.controlId)}function qi(e,t){const s=new Set(t.flatMap(n=>n.controls.map(a=>a.id)));return e&&s.has(e)?e:t[0]?.controls?.[0]?.id||null}function we(e){i.sessionSelectedControlId=e||null,Ue()}function Bi(e,t){i.sessionCollapsedCategories instanceof Set||(i.sessionCollapsedCategories=new Set),!i.sessionCollapsedCategories.size&&t.length&&t.forEach(n=>i.sessionCollapsedCategories.add(n.categoryId));const s=t.find(n=>n.controls.some(a=>a.id===e));s&&i.sessionCollapsedCategories.delete(s.categoryId)}function Oi(e){return e==="done"||e==="evidenced"?"done":e==="none"?"none":e==="partial"?"partial":"unknown"}function ji(e,t,s){const n=p("sessionMasterTree"),a=p("sessionMasterCount");if(!n)return;const r=new Map;e.forEach(u=>{const f=String(u.areaId||u.categoryId?.split(".")[0]||"0");r.has(f)||r.set(f,{areaId:f,areaName:Y[f]||u.areaName||`영역 ${f}`,groups:[]}),r.get(f).groups.push(u)});const o=Array.from(r.values()).sort((u,f)=>Ce(u.areaId,f.areaId)),l=e.reduce((u,f)=>u+f.controls.length,0),d=An().length;a&&(a.textContent=Mi()?`표시 ${l} · 미완료 ${d}`:`미완료 ${d}`),n.innerHTML=o.map(u=>{const f=u.groups.flatMap(g=>g.controls),m=nt(f);return`
      <div class="session-area-block">
        <div class="session-area-label">
          <span>${c(u.areaName)}</span>
          <span>${m.reviewed}/${m.total}</span>
        </div>
        ${u.groups.map(g=>{const h=i.sessionCollapsedCategories.has(g.categoryId),w=nt(g.controls);return`
            <div class="session-cat${h?" is-collapsed":""}" data-session-cat="${c(g.categoryId)}">
              <button type="button" class="session-cat-head" data-toggle-session-cat="${c(g.categoryId)}" aria-expanded="${h?"false":"true"}">
                <span class="session-cat-title">${c(g.categoryId)} ${c(g.categoryName)}</span>
                <span class="session-cat-meta">${w.reviewed}/${w.total}</span>
              </button>
              <div class="session-cat-items">
                ${g.controls.map(A=>{const E=x(A.id),y=Oi(E),L=A.id===t?" is-selected":"",v=s.has(A.id)?" is-priority":"";return`
                    <button type="button" class="session-item tone-${y}${L}${v}" data-select-control="${c(A.id)}">
                      <span class="session-item-status" aria-hidden="true"></span>
                      <span class="session-item-copy">
                        <strong>${c(A.id)}</strong>
                        <span>${c(A.title||"")}</span>
                      </span>
                      ${s.has(A.id)?'<em class="session-item-badge">우선</em>':""}
                    </button>
                  `}).join("")}
              </div>
            </div>
          `}).join("")}
      </div>
    `}).join("")||'<p class="detail-empty">표시할 통제가 없습니다.</p>',n.querySelectorAll("[data-toggle-session-cat]").forEach(u=>{u.addEventListener("click",()=>{const f=u.getAttribute("data-toggle-session-cat");i.sessionCollapsedCategories.has(f)?i.sessionCollapsedCategories.delete(f):i.sessionCollapsedCategories.add(f);const m=n.querySelector(`[data-session-cat="${f}"]`),g=i.sessionCollapsedCategories.has(f);m?.classList.toggle("is-collapsed",g),u.setAttribute("aria-expanded",g?"false":"true")})}),n.querySelectorAll("[data-select-control]").forEach(u=>{u.addEventListener("click",()=>{Rn(u.getAttribute("data-select-control"),{groups:e,prioritySet:s,scrollTree:!0,scrollDetail:!1})})})}function Rn(e,{groups:t,prioritySet:s,scrollTree:n=!1,scrollDetail:a=!1}={}){if(!e)return;const r=t||Oe(),o=Qt(i.analysis?.confirmationActions||[]),l=s||new Set(Tn(i.analysis?.confirmationActions||[]));i.pendingDoneEvidenceControlId&&i.pendingDoneEvidenceControlId!==e&&(i.pendingDoneEvidenceControlId=null),we(e);const d=r.find(f=>f.controls.some(m=>m.id===e));d&&i.sessionCollapsedCategories.delete(d.categoryId),z(e,o,l);const u=p("sessionMasterTree");if(u){if(u.querySelectorAll(".session-item").forEach(f=>{f.classList.toggle("is-selected",f.getAttribute("data-select-control")===e)}),u.querySelectorAll(".session-cat").forEach(f=>{const m=f.getAttribute("data-session-cat");f.classList.toggle("is-collapsed",i.sessionCollapsedCategories.has(m))}),n){const f=u.querySelector(`[data-select-control="${CSS.escape(e)}"]`);if(f){const m=u.getBoundingClientRect(),g=f.getBoundingClientRect();(g.top<m.top||g.bottom>m.bottom)&&(u.scrollTop+=g.top-m.top-u.clientHeight/3)}}a&&window.requestAnimationFrame(()=>{window.requestAnimationFrame(()=>{Fi(e)})})}}function Fi(e){const t=(e?document.querySelector(`.session-detail-card[data-today-control="${CSS.escape(e)}"]`):null)||document.querySelector(".session-detail-card")||p("sessionDetailPane");if(!t)return;(t.querySelector(".today-card-top")||t.querySelector(".today-question")||t).scrollIntoView({behavior:"smooth",block:"start"})}function Pn(e){return i.analysis?.controlSessionDetails?.[e]||null}function ws(e){return(e||[]).map(t=>`<li>${c(t)}</li>`).join("")}function Hi(e,t,s){const n=(i.checklist||[]).find(M=>M.id===e)||{},a=Pn(e),r=x(e),o=t?.title||a?.title||n.title||"",l=t?.question||a?.question||`${o||e} 이행 상태를 확인했나요?`,d=String(t?.whyItMatters||"").trim(),u=String(t?.actionGuide||a?.actionGuide||"").trim(),f=d.length>220?`${d.slice(0,217)}…`:d,m=u.length>180?`${u.slice(0,177)}…`:u,g=V(e),h=Object.keys(K).map(M=>`
    <label class="audit-check" title="${c(e)} ${Bs[M]}">
      <input type="checkbox" data-check-control="${c(e)}" data-check-key="${M}"${g[M]?" checked":""}>
      <span>${K[M]}</span>
    </label>
  `).join(""),w=n.checklistItems||[],A=Vt(e,w),E=w.map((M,Jn)=>{const mt=String(Jn+1),Yn=!!A[mt];return`
      <li class="domain-check-item">
        <label>
          <input type="checkbox" data-domain-control="${c(e)}" data-domain-item="${mt}"${Yn?" checked":""}>
          <span><strong>${mt}.</strong> ${c(M)}</span>
        </label>
      </li>
    `}).join(""),y=zt(e),L=i.pendingDoneEvidenceControlId===e,v=r==="evidenced"?"done":r,S=L?"done":v,b=Ri.map(M=>`
    <button type="button" data-diagnose-control="${c(e)}" data-diagnose-level="${M.id}" class="${S===M.id?"is-active":""}" aria-pressed="${S===M.id?"true":"false"}">${M.label}</button>
  `).join(""),k=ws((n.officialEvidenceExamples||[]).slice(0,8)),I=ws(n.recommendedActions||[]),_=y.length?y.map(M=>`
        <li class="session-evidence-item" data-evidence-id="${c(M.id)}">
          <div class="session-evidence-item-body">
            <strong>${c(M.title)}</strong>
          </div>
          <button type="button" class="ghost session-evidence-remove" data-evidence-remove="${c(e)}" data-evidence-id="${c(M.id)}" aria-label="증적 삭제">삭제</button>
        </li>
      `).join(""):"",C=rt(),T=C.indexOf(e),O=Mt(e,-1),gt=Mt(e,1),We=T>=0?`${T+1} / ${C.length}`:"",j=We?`
      <div class="session-nav" role="navigation" aria-label="통제 이동">
        <button type="button" class="session-nav-btn" data-session-nav="prev" ${O?"":"disabled"} aria-label="이전 통제">이전</button>
        <span class="session-nav-pos">${c(We)}</span>
        <button type="button" class="session-nav-btn session-nav-next" data-session-nav="next" ${gt?"":"disabled"} aria-label="다음 통제">저장하고 다음 <span aria-hidden="true">→</span></button>
      </div>
  `:"",Z=(n.officialEvidenceExamples||[])[0]?`예: ${n.officialEvidenceExamples[0]}`:"예: 출입대장 캡처 / 공유폴더";return`
    <article class="today-card session-detail-card" data-today-control="${c(e)}">
      <div class="today-card-top">
        <div class="today-card-idline">
          ${s.has(e)?'<span class="today-priority">우선</span>':""}
          <span class="today-control-id">${c(e)}</span>
          <span class="today-title">${c(o)}</span>
        </div>
        <span class="status-pill level-${v}">${c(U[v]||v)}</span>
      </div>
      <p class="today-question">${c(l)}</p>
      ${f||m?`<div class="assessment-context">
        ${f?`<p>${c(f)}</p>`:""}
        ${m?`<p>${c(m)}</p>`:""}
      </div>`:""}
      <section class="judgement-criteria" aria-labelledby="judgementCriteriaTitle">
        <div class="judgement-section-head">
          <h3 id="judgementCriteriaTitle">판단 기준</h3>
          <span>해당하는 항목을 확인하세요</span>
        </div>
        <ul class="domain-check-list">${E||"<li class='detail-empty'>제공된 세부 기준이 없습니다.</li>"}</ul>
      </section>
      <div class="diagnosis-decision-head">
        <h3>진단 결과</h3>
        <span>선택하면 즉시 저장됩니다</span>
      </div>
      <div class="today-diagnose" role="group" aria-label="${c(e)} 진단">
        ${b}
      </div>
      ${L?`
        <form class="session-done-evidence" data-done-evidence-form="${c(e)}">
          <p class="session-done-evidence-label">이행으로 저장하려면 증적 한 줄만 남기세요</p>
          <div class="session-done-evidence-row">
            <input type="text" name="line" required maxlength="160" placeholder="${c(Z)}" autocomplete="off">
            <button type="submit" class="primary">이행으로 저장</button>
            <button type="button" class="ghost" data-done-evidence-skip="${c(e)}">나중에</button>
          </div>
        </form>
      `:`
        <p class="session-evidence-hint">이행은 증적 한 줄만 있으면 됩니다. 버튼을 누르면 입력창이 열립니다.</p>
      `}
      ${_?`
        <section class="today-detail session-evidence-block" aria-label="등록된 증적">
          <h3 class="today-detail-title">등록된 증적</h3>
          <ul class="session-evidence-list">${_}</ul>
        </section>
      `:""}
      <section class="evidence-workspace" aria-label="${c(e)} 증적 관리">
        <header class="evidence-workspace-head">
          <div>
            <span>통제 증적</span>
            <h3>${c(e)} ${c(o)}</h3>
            <p>이 통제의 이행을 입증할 문서·기록·캡처를 등록하세요.</p>
          </div>
          <strong>${y.length}<small>건 등록</small></strong>
        </header>
        <form class="evidence-register-form" data-evidence-register-form="${c(e)}">
          <label for="evidenceLine-${c(e)}">증적 제목</label>
          <div>
            <input id="evidenceLine-${c(e)}" type="text" name="line" required maxlength="160" placeholder="${c(Z)}" autocomplete="off">
            <button type="submit" class="primary">증적 등록</button>
          </div>
        </form>
        <div class="evidence-example-line">
          <span>권장 증적</span>
          <p>${c((n.officialEvidenceExamples||[]).slice(0,3).join(" · ")||"정책, 승인 기록, 운영 로그 등")}</p>
        </div>
        <section class="evidence-registered-panel">
          <h4>등록된 증적</h4>
          ${_?`<ul class="session-evidence-list">${_}</ul>`:'<p class="detail-empty">아직 등록된 증적이 없습니다.</p>'}
        </section>
      </section>
      <section class="today-detail session-self-check" aria-label="자체진단 체크">
        <h3 class="today-detail-title">자체진단 체크 <span class="today-detail-badge">선택</span></h3>
        <p class="today-detail-note">필요하면 검토·정책·구현·증적을 세분화하세요. 진단 버튼만으로도 충분합니다.</p>
        <div class="audit-checks" aria-label="${c(e)} 자체진단 체크 항목">
          ${h}
        </div>
      </section>
      <details class="session-optional-block" open>
        <summary>참고자료 · 인증기준 · 법적 근거</summary>
        <div class="session-optional-body">
          <div class="session-guide-grid">
            ${n.officialRequirement?`
              <details class="detail-block session-guide-details" open>
                <summary>인증기준 (안내서)</summary>
                <p>${c(n.officialRequirement)}</p>
              </details>
            `:""}
            <details class="detail-block session-guide-details legal-basis-block" open>
              <summary>법적 근거 및 참고자료</summary>
              <p class="today-detail-note">법령은 바로 확인하고, 법령해석·공식 사례·안내서는 필요할 때 펼쳐보세요.</p>
              <div data-legal-basis="${c(e)}">${Wt(e)}</div>
            </details>
            <details class="detail-block session-guide-details" open>
              <summary>미이행 시 취약점/심사 리스크</summary>
              <p>${c(n.riskIfMissing||"-")}</p>
            </details>
            ${k?`
              <details class="detail-block session-guide-details" open>
                <summary>증거자료 예시 (안내서)</summary>
                <ul>${k}</ul>
              </details>
            `:""}
            ${I?`
              <details class="detail-block session-guide-details" open>
                <summary>권장 조치</summary>
                <ul>${I}</ul>
              </details>
            `:""}
          </div>
        </div>
      </details>
      ${j}
    </article>
  `}function $s(e,{diagnoseControl:t,groups:s,prioritySet:n}={}){const a={...z._hooks||{},diagnoseControl:t||z._hooks?.diagnoseControl||(()=>{})},r=Qt(i.analysis?.confirmationActions||[]);z(e,r,n||new Set,a),window.requestAnimationFrame(()=>{p("sessionDetailPane")?.querySelector("[data-done-evidence-form] input[name='line']")?.focus()})}function zi(e,{diagnoseControl:t,groups:s,prioritySet:n}={}){e.querySelectorAll("[data-diagnose-control]").forEach(a=>{a.addEventListener("click",()=>{const r=a.getAttribute("data-diagnose-control"),o=a.getAttribute("data-diagnose-level");if(!(!r||!o||!t)){if(o==="done"&&!Q(r)){we(r),i.pendingDoneEvidenceControlId=r,$s(r,{diagnoseControl:t,groups:s,prioritySet:n});return}i.pendingDoneEvidenceControlId=null,t(r,o)}})}),e.querySelectorAll("[data-check-control]").forEach(a=>{a.addEventListener("change",()=>{const r=a.getAttribute("data-check-control"),o=a.getAttribute("data-check-key");!r||!o||(we(r),yn(r,o,!!a.checked))})}),e.querySelectorAll("[data-domain-control]").forEach(a=>{a.addEventListener("change",()=>{const r=a.getAttribute("data-domain-control"),o=a.getAttribute("data-domain-item");!r||!o||(vn(r,o,!!a.checked),i.analysis&&typeof z._hooks?.markAnalysisStale=="function"&&z._hooks.markAnalysisStale())})}),e.querySelectorAll("[data-session-nav]").forEach(a=>{a.addEventListener("click",()=>{const r=a.getAttribute("data-session-nav")==="prev"?-1:1,o=i.sessionSelectedControlId,l=Mt(o,r);l&&(i.pendingDoneEvidenceControlId=null,Rn(l,{groups:s||Oe(),prioritySet:n,scrollTree:!0,scrollDetail:!0}))})}),e.querySelectorAll("[data-done-evidence-form]").forEach(a=>{a.addEventListener("submit",r=>{r.preventDefault();const o=a.getAttribute("data-done-evidence-form");if(!o||!t)return;const l=String(new FormData(a).get("line")||"").trim();!l||(i.pendingDoneEvidenceControlId=null,!gs(o,{title:l},{quiet:!0}))||t(o,"done")})}),e.querySelectorAll("[data-evidence-register-form]").forEach(a=>{a.addEventListener("submit",r=>{r.preventDefault();const o=a.getAttribute("data-evidence-register-form"),l=String(new FormData(a).get("line")||"").trim();!o||!l||!gs(o,{title:l},{quiet:!0})||$s(o,{diagnoseControl:t,groups:s,prioritySet:n})})}),e.querySelectorAll("[data-done-evidence-skip]").forEach(a=>{a.addEventListener("click",()=>{const r=a.getAttribute("data-done-evidence-skip");!r||!t||(i.pendingDoneEvidenceControlId=null,t(r,"partial"))})}),e.querySelectorAll("[data-evidence-remove]").forEach(a=>{a.addEventListener("click",()=>{const r=a.getAttribute("data-evidence-remove"),o=a.getAttribute("data-evidence-id");!r||!o||ci(r,o)})})}function z(e,t,s,n){const a=p("sessionDetailPane");if(!a)return;if(!e){a.innerHTML='<p class="detail-empty">왼쪽 지도에서 통제를 선택하세요.</p>';return}const r=t.get(e)||null,o=(i.checklist||[]).find(m=>m.id===e)||{},l=r?.title||Pn(e)?.title||o.title||"",d=p("workspaceContextDetail"),u=p("view-analyze")?.classList.contains("is-assessment")||p("view-analyze")?.classList.contains("is-evidence");d&&u&&(d.textContent=`${e} · ${l}`),n&&(z._hooks=n);const f=n||z._hooks||{diagnoseControl:()=>{}};a.innerHTML=Hi(e,r,s),zi(a,{...f,groups:In(Oe()),prioritySet:s}),at(e)}function Mn(e,{diagnoseControl:t,markAnalysisStale:s}={}){const n={diagnoseControl:t||(()=>{}),markAnalysisStale:s};z._hooks=n,Di(),Ni();const{reviewed:a,applicable:r}=Si(),o=p("assessmentProgressStrip"),l=e?.confirmationActions||[],d=e?.confirmationActionMeta||{};d.mode&&(i.sessionBundleMode=d.mode);const u=Qt(l),f=Tn(l),m=new Set(f),g=An(),h=En().length,w=rt().reduce((C,T)=>{const O=x(T);return(O==="none"||O==="partial")&&(C[O]+=1),C},{none:0,partial:0}),A=In(Oe()),E=Oe(),y=qi(i.sessionSelectedControlId,A);i.sessionSelectedControlId=y,Bi(y,A);const L=Ti({analysis:e,controlEvidence:i.controlEvidence,weakControlIds:rt().filter(C=>["none","partial"].includes(x(C))),stale:i.analysisStale,groups:E,getLevel:x,nextControls:ki().map(C=>({id:C.id,title:C.title,level:x(C.id)})),done:h,partial:w.partial,applicable:r}),v=(C=null,{weak:T=!1}={})=>{T?(Ii(i,C,f),we(i.sessionSelectedControlId)):(i.levelFilter="all",we(C||vs())),ce("assessment"),De(),window.requestAnimationFrame(()=>{p("sessionMasterDetail")?.scrollIntoView({behavior:"smooth",block:"start"})})},S=(C=null)=>v(C,{weak:!0});if(o){const C=L.temperature,T=L.band,O=Z=>r>0?`${(Z/r*100).toFixed(1)}%`:"0%",gt=g.length,We=w.none+w.partial,j=Pi({remaining:gt,remediationCount:We});o.classList.add("is-complete"),o.classList.remove("is-cold","is-warming","is-rising","is-ready"),o.classList.add(`is-${T.key}`),o.innerHTML=`
      <div class="ap-complete-intro">
        <span class="ap-complete-eyebrow"><span aria-hidden="true"></span>자가진단 준비 온도 <b>${a} / ${r}</b></span>
        <div class="ap-complete-body">
          <div class="ap-temperature is-${T.key}" role="img" aria-label="자가진단 준비 온도 ${C}도 ${T.label}" style="--temperature:${C}">
            <span><strong>${C}</strong><sup>°</sup></span>
          </div>
          <div class="ap-complete-copy">
            <strong>${j.title}</strong>
            <p>${j.help}</p>
            ${j.actionAttr?`<div class="ap-progress-actions ap-complete-actions">
              <button type="button" ${j.actionAttr} class="ap-primary">${j.actionLabel} <span aria-hidden="true">→</span></button>
            </div>`:""}
          </div>
        </div>
      </div>
      <div class="ap-kpi-grid" aria-label="자가진단 결과">
        <article class="ap-kpi-card is-primary">
          <span>부분 이행</span>
          <strong>${w.partial}<small>건</small></strong>
          <em>${O(w.partial)}</em>
          <i aria-hidden="true"><b style="width:${O(w.partial)}"></b></i>
        </article>
        <article class="ap-kpi-card is-done">
          <span>이행</span>
          <strong>${h}<small>건</small></strong>
          <em>${O(h)}</em>
          <i aria-hidden="true"><b style="width:${O(h)}"></b></i>
        </article>
        <article class="ap-kpi-card is-none">
          <span>미이행</span>
          <strong>${w.none}<small>건</small></strong>
          <em>${O(w.none)}</em>
          <i aria-hidden="true"><b style="width:${O(w.none)}"></b></i>
        </article>
      </div>
      <aside class="ap-complete-recommendation">
        <span class="ap-complete-section-label">다음 단계 추천</span>
        <strong>${j.recCount?`<b>${j.recCount}개</b> ${j.recLabel}`:j.recLabel}</strong>
        <p>${j.recHelp}</p>
        <ul>
          ${j.recItems.map(Z=>`<li>${Z}</li>`).join("")}
        </ul>
      </aside>
      <div class="ap-complete-footnote">
        <span>※ 비율은 적용 통제 ${r}개 기준입니다.</span>
        <span>자가진단은 인증 적합 판정을 대체하지 않습니다.</span>
      </div>
    `,o.querySelector("[data-progress-next]")?.addEventListener("click",()=>{i.levelFilter="unknown",we(vs()),De(),p("sessionMasterDetail")?.scrollIntoView({behavior:"smooth",block:"start"})}),o.querySelectorAll("[data-progress-weak]").forEach(Z=>Z.addEventListener("click",()=>{S()}))}const b=p("confirmationActionCount");b&&(b.textContent=`진행 ${a}/${r}`),ji(A,y,m),z(y,u,m,n);const k=e?.applicabilityNotes||[],I=p("applicabilityNotesPanel"),_=p("applicabilityNotesList");I&&_&&(k.length?(I.style.display="",_.innerHTML=`<ul>${k.map(C=>`<li><strong>${c(C.controlId)}</strong> — ${c(C.reason||"")}</li>`).join("")}</ul>`):I.style.display="none")}function Ss(e,t,s,n=[]){e&&(e.style.display="",e.classList.toggle("is-empty",!!s),t&&(t.style.display=s?"":"none"),n.forEach(a=>{a&&(a.style.display=s?"none":"")}))}const ks={cluster:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="8" height="7" rx="1.6"/><rect x="13" y="4" width="8" height="7" rx="1.6"/><rect x="8" y="13" width="8" height="7" rx="1.6"/></svg>',link:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/></svg>',ready:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12.4 10.7 15.2 16.2 9"/></svg>'};function Nn(e={}){const t=e.statusCounts||{},s=Number(t.unknown||0),n=Number(t.none||0),a=Number(t.partial||0),r=Number(t.done||0)+Number(t.evidenced||0),o=Number(t.na||0),l=Number(e.applicableControlCount||0),d=Number(e.reviewedControlCount||n+a+r);return{unknown:s,none:n,partial:a,done:r,na:o,applicable:l,reviewed:d,weak:n+a,complete:l>0&&d>=l}}function Dn(e={}){return[{key:"none",label:"미이행",value:e.none||0},{key:"partial",label:"부분 이행",value:e.partial||0},{key:"unknown",label:"미점검",value:e.unknown||0},{key:"done",label:"이행",value:e.done||0}]}function _i(e=[]){return e.length?`<p class="result-empty-meta">${e.map(t=>`<span class="level-${c(t.key||"")}">${c(t.label||"")} <b>${Number(t.value||0)}</b></span>`).join("")}</p>`:""}function $e({tone:e="idle",icon:t="cluster",title:s="",body:n="",stats:a=[],ctaLabel:r="자가진단 이어가기",ctaHref:o=`${H}/assessment`,ctaRoute:l="assessment"}={}){return`
    <article class="result-empty tone-${c(e)}" role="status">
      <div class="result-empty-icon" aria-hidden="true">${ks[t]||ks.cluster}</div>
      <div class="result-empty-copy">
        <strong>${c(s)}</strong>
        <p>${c(n)}</p>
        ${_i(a)}
      </div>
      <a class="result-empty-cta" href="${c(o)}" data-route="${c(l)}">${c(r)}</a>
    </article>
  `}function Ui(e={}){const t=Nn(e),s=Dn(t);return t.complete&&t.weak===0?$e({tone:"ready",icon:"ready",title:"점검한 통제에서 묶을 미흡이 없습니다",body:"미이행·부분 이행이 없어 중분류 보완 묶음을 표시하지 않습니다.",stats:s,ctaLabel:"보고서 보기",ctaHref:`${H}/report`,ctaRoute:"report"}):t.weak>0?$e({tone:"wait",icon:"cluster",title:"같은 중분류에서 함께 보완할 항목이 없습니다",body:`미흡 ${t.weak}개는 확인됐지만, 한 중분류에 2개 이상 모여야 카드가 생깁니다.`,stats:s}):$e({tone:"idle",icon:"cluster",title:"아직 묶을 미흡 통제가 없습니다",body:"같은 중분류에 미이행·부분 이행이 2개 이상일 때 여기에 표시됩니다.",stats:s})}function Gi(e={}){const t=Nn(e),s=Dn(t);return t.complete&&t.weak===0?$e({tone:"ready",icon:"ready",title:"연계할 미흡 통제가 없습니다",body:"미이행·부분 이행이 없어 영향 경로를 띄울 출발점이 없습니다.",stats:s,ctaLabel:"보고서 보기",ctaHref:`${H}/report`,ctaRoute:"report"}):t.weak>0?$e({tone:"wait",icon:"link",title:"확인된 미흡 통제 기준의 연계 경로가 없습니다",body:`미흡 ${t.weak}개는 확인됐지만, 다른 통제로 이어지는 경로는 식별되지 않았습니다.`,stats:s}):$e({tone:"idle",icon:"link",title:"아직 식별된 연계 문제가 없습니다",body:"미흡으로 확인된 통제가 생기면 영향 경로가 여기에 표시됩니다.",stats:s})}function Qe(e){const t=Number(e);return Number.isFinite(t)?Math.max(0,Math.min(100,t)):0}function Cs(e){const t=Qe(e);return Number.isInteger(t)?String(t):t.toFixed(1)}function Se(e){if(e==null||e==="")return"판단 보류";const t=Number(e);return Number.isFinite(t)?t>=80?"양호":t>=60?"보통":t>=35?"보완 필요":"기초 보완 필요":"판단 보류"}function Wi(e){const t=["전체 진행 참고","전체 진행 반영 점수","점검분 이행 참고","점검분만 이행 점수","내부 참고점수","내부 참고 점수","평가분 이행점수","평가분 이행 점수"];let s=e;for(const n of t){const a=n.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");s=s.replace(new RegExp(`${a}\\s*([\\d.]+)\\s*%`,"g"),(r,o)=>`${n.includes("점검")||n.includes("평가분")?"점검분 이행 참고":"전체 진행 참고"} '${Se(o)}'`)}return s=s.replace(/(^|\n)(- [^:\n]+):\s*([\d.]+)%/g,(n,a,r,o)=>`${a}${r}: ${Se(o)}`),s=s.replace(/준비도\s*([\d.]+)%/g,(n,a)=>`참고 구간 '${Se(a)}'`),s}function D(e){const t=String(e??"").replaceAll("내부 참고점수(진행 반영)","전체 진행 참고").replaceAll("내부 참고 점수(진행 반영)","전체 진행 참고").replaceAll("전체 진행 반영 점수","전체 진행 참고").replaceAll("내부 참고점수","전체 진행 참고").replaceAll("내부 참고 점수","전체 진행 참고").replaceAll("점검분만 이행 점수","점검분 이행 참고").replaceAll("평가분 이행점수","점검분 이행 참고").replaceAll("평가분 이행 점수","점검분 이행 참고").replaceAll("점수 가중치:","참고 구간:").replaceAll("상태별 배점:","참고 구간:").replaceAll("미이행 5 · 부분 이행 45 · 이행 80 · 증적 확보 100","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("미이행 5 · 부분 이행 45 · 이행 80","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("미이행 0 · 부분 이행 50 · 이행 100","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("미이행 0 · 부분 이행 45 · 이행 80","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("미이행 5 · 부분 이행 45","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("부분 이행 45 · 이행 80","양호 · 보통 · 보완 필요 · 기초 보완 필요").replaceAll("미이행 5 · 양호","양호").replaceAll("미이행 5 · ","").replaceAll("미이행 5 ·","").replaceAll("미이행 5","").replaceAll(" · 증적 확보 100","").replaceAll("· 증적 확보 100","").replaceAll(" · 이행 80","").replaceAll("· 이행 80","");return Wi(t)}function As(e,t="관련 리스크를 확인하세요."){const s=String(e||"").replace(/\s+/g," ").trim();return s?s.length>110?`${s.slice(0,108)}…`:s:t}function Vi(e,t="unknown"){const s=x(e);return s||t||"unknown"}function Ki(e,t){const s=e||"unknown",n=t||U[s]||s;return`<span class="level-badge level-${c(s)}">${c(n)}</span>`}function Ji(e){return(i.checklist.find(s=>s.id===e)||i.allControls.find(s=>s.id===e))?.title||""}const $t=5;let X=1,ee=null;function Zt(e,t,s=!1){e&&(e.value=String(t||""),e.dataset.userEdited=s?"1":"0",e.dispatchEvent(new CustomEvent("report-editor:set",{detail:{value:e.value,edited:s}})))}function je(){const e=i.lastAiExecutiveReport||i.analysis?.executiveReport||"";return D(e)}function Nt(){return!!String(i.lastAiExecutiveReport||i.analysis?.executiveReport||"").trim()}function Xt(){return p("executiveReportStream")?.dataset.userEdited==="1"?"edited":i.lastAiExecutiveReport?"ai":i.analysis?.executiveReport?"rule":"empty"}function de(e,t=!1){const s=p("reportEditorState");s&&(s.textContent=e,s.classList.toggle("is-dirty",t),s.classList.toggle("is-ai",!t&&Xt()==="ai"))}function qe(){const e=p("reportWordCount"),t=p("executiveReportStream");if(!e||!t||t.dataset.reactEditor==="1")return;const s=String(t.value||"").length;e.textContent=`공백 포함 ${s.toLocaleString("ko-KR")}자`}function Yi(){const e=p("reportComposeOverlay"),t=p("reportPage"),s=p("executiveReportStream");if(!e)return;const n=e.querySelector('[data-overlay-state="empty"]'),a=e.querySelector('[data-overlay-state="writing"]'),r=!!i.aiReportWriting,o=!Nt()&&!r;e.hidden=!(r||o),n&&(n.hidden=!o),a&&(a.hidden=!r),t?.classList.toggle("is-writing",r),t?.setAttribute("aria-busy",r?"true":"false"),s&&(s.readOnly=r)}function es(){const e=Xt(),t=!!i.aiReportWriting,s={basis:!!i.analysis||t,draft:e==="ai"||e==="edited"||t,edit:e==="edited"||e==="ai"&&!t,export:e==="ai"||e==="edited"||e==="rule"},n=t?"draft":e==="edited"||e==="ai"?"edit":e==="rule"?"draft":"basis";document.querySelectorAll("[data-report-flow]").forEach(a=>{const r=a.getAttribute("data-report-flow");a.classList.toggle("is-done",!!s[r]&&r!==n),a.classList.toggle("is-active",r===n)})}function Qi(){const e=p("executiveReportStream");!e||e.dataset.editorBound==="1"||(e.dataset.editorBound="1",e.addEventListener("input",()=>{e.dataset.userEdited="1",de("편집 중",!0),qe(),es();const t=p("reportSourceBadge");t&&(t.textContent="직접 편집"),window.clearTimeout(Number(e.dataset.saveTimer||0));const s=window.setTimeout(()=>{e.dataset.savedValue=e.value,de("편집 내용 유지됨",!1)},450);e.dataset.saveTimer=String(s)}),e.addEventListener("compositionend",qe),e.addEventListener("change",qe),window.addEventListener("report-editor:toast",t=>$(t.detail||"보고서 편집 내용을 확인하세요.")),F())}function Zi(e,t="편집 내용 유지됨"){e.dataset.userEdited="1",e.dataset.savedValue=e.value,de(t,!1),qe(),es();const s=p("reportSourceBadge");s&&(s.textContent="직접 편집")}function se(){ee=null;const e=p("reportRewritePreview");e&&(e.hidden=!0)}function Xi(){const e=p("executiveReportStream"),t=p("reportRewriteBtn"),s=p("reportRewriteAcceptBtn"),n=p("reportRewriteRejectBtn"),a=p("reportRewriteCloseBtn");!e||!t||t.dataset.bound==="1"||(t.dataset.bound="1",t.addEventListener("click",async()=>{if(!await Vs())return;const r=e.selectionStart,o=e.selectionEnd,l=e.value.slice(r,o).trim();if(!l){$("보고서 본문에서 개선할 문장을 먼저 선택하세요."),e.focus();return}if(l.length>8e3){$("선택 문장은 8,000자 이하로 줄여주세요.");return}t.disabled=!0,t.textContent="개선 중…",se();try{const d=await fetch("/controls/report/rewrite",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:l,mode:p("reportRewriteMode")?.value||"professional"})});if(!d.ok){const f=await d.json().catch(()=>({}));throw new Error(f.detail||"문장 개선 요청에 실패했습니다.")}const u=await d.json();ee={start:r,end:o,original:e.value.slice(r,o),suggestion:String(u.suggestion||"")},p("reportRewriteBefore").textContent=ee.original,p("reportRewriteAfter").textContent=ee.suggestion,p("reportRewriteStatus").textContent=u.reason||"개선안을 확인하세요.",p("reportRewritePreview").hidden=!1,s.disabled=!u.applied||ee.suggestion===ee.original,a?.focus()}catch(d){$(`문장 개선 실패: ${d.message}`)}finally{t.disabled=!1,t.textContent="선택 문장 개선"}}),s?.addEventListener("click",()=>{if(!ee)return;const{start:r,end:o,original:l,suggestion:d}=ee;if(e.value.slice(r,o)!==l){$("본문이 변경되어 개선안을 적용할 수 없습니다. 문장을 다시 선택하세요."),se();return}e.value=`${e.value.slice(0,r)}${d}${e.value.slice(o)}`,e.setSelectionRange(r,r+d.length),Zi(e,"개선안 적용됨"),se(),e.focus(),$("선택 문장에 개선안을 적용했습니다.")}),n?.addEventListener("click",()=>{se(),$("개선안을 적용하지 않았습니다.")}),a?.addEventListener("click",se),document.addEventListener("keydown",r=>{r.key==="Escape"&&!p("reportRewritePreview")?.hidden&&(se(),e.focus())}))}function er(){const e=p("executiveReportStream");e&&(Zt(e,je()||"확인 목록을 갱신하면 초안이 여기에 표시됩니다."),e.dataset.sourceValue=e.value,e.dataset.userEdited="0",se(),de("원문 복원됨",!1),F(),$("자동 생성 원문으로 복원했습니다."))}function tr(){if(i.activeSessionId)return i.analysisHistory||[];try{return JSON.parse(localStorage.getItem(tt)||"[]")}catch{return[]}}function F(){const e=!!i.lastAiExecutiveReport,t=!!i.aiReportWriting,s=!!i.analysis&&!i.analysisStale&&!t,n=Xt(),a={empty:"초안 없음",rule:"진단 초안",ai:"AI 초안",edited:"직접 편집"},r=p("reportSourceBadge");r&&(r.textContent=t?"작성 중":a[n]),document.querySelectorAll("[data-write-ai-report]").forEach(u=>{u.disabled=!s,u.id==="writeAiReportBtn"&&(u.textContent=t?"작성 중…":e?"AI로 다시 작성":Nt()?"AI로 재작성":"AI로 초안 작성",u.classList.toggle("primary",!e||t))});const o=p("exportReportDocxBtn");o&&o.classList.toggle("primary",e&&!t);const l=p("resetReportBtn");l&&(l.disabled=t||!Nt()),Yi(),es(),qe();const d=p("aiReportStatus");if(d){if(d.classList.remove("is-ready","is-pending"),t){d.hidden=!0;return}if(i.analysisStale){d.hidden=!1,d.classList.add("is-pending"),d.textContent="진단이 바뀌었습니다. 확인 목록을 먼저 갱신하세요.";return}if(e&&i.aiReportStale){d.hidden=!1,d.classList.add("is-pending"),d.textContent="확인 목록이 바뀌었습니다. 아래는 이전 AI 문장입니다.";return}if(e){d.hidden=!1,d.classList.add("is-ready"),d.textContent="AI 초안입니다. 본문을 직접 고친 뒤 Word로 내보내세요.";return}if(n==="rule"){d.hidden=!1,d.classList.add("is-pending"),d.textContent="지금은 진단 기반 초안입니다. AI로 문장을 재작성할 수 있습니다.";return}d.hidden=!0}}function Fe(e={}){const t=p("executiveReportStream");if(!t)return;const s=p("reportEditorBasis");if(s&&(s.textContent=`현재 진단 ${Number(i.analysis?.reviewedControlCount)||0}/${Number(i.analysis?.applicableControlCount)||0} 기준`),t.classList.contains("typing")||i.aiReportWriting)return;const n=!!e.preferTemplate;if(t.dataset.userEdited==="1"&&!n)return;const a=n?D(i.analysis?.executiveReport||je()):je();t.dataset.historyKey=i.activeSessionId||"default",Zt(t,a),t.dataset.sourceValue=a,t.dataset.userEdited="0",de(a?"초안 준비됨":"초안 대기",!1),F()}async function sr(e){const t=p("executiveReportStream");if(!t)return;const s=i.reportStreamToken=(i.reportStreamToken||0)+1,n=D(e);if(t.dataset.reactEditor==="1"){Zt(t,n),t.dataset.sourceValue=n,de("AI 초안 적용됨",!1),F();return}t.value="",t.dataset.userEdited="0",t.classList.add("typing");const a=3;for(let r=0;r<n.length;r+=a){if(s!==i.reportStreamToken)return;t.value+=n.slice(r,r+a),t.scrollTop=t.scrollHeight,await na(14)}s===i.reportStreamToken&&(t.classList.remove("typing"),t.dataset.sourceValue=n,de("AI 초안 적용됨",!1),F())}function qn(e){const t={ts:Number(e.clientAnalyzedAt||Date.now()),overallReadiness:e.overallReadiness,gapCount:e.gapCount,readinessLabel:e.readinessLabel,scenarioId:i.analyzeScenarioId||null};if(X=1,i.activeSessionId){i.analysisHistory=[t,...i.analysisHistory||[]].slice(0,8),Ue();return}try{const s=JSON.parse(localStorage.getItem(tt)||"[]");s.unshift(t),localStorage.setItem(tt,JSON.stringify(s.slice(0,8)))}catch{}}function nr(e){const t=new Date(e.ts).toLocaleString("ko-KR"),s=c(e.readinessLabel||(Number.isFinite(Number(e.overallReadiness))?Se(e.overallReadiness):"—")),n=Number.isFinite(Number(e.gapCount))?e.gapCount:0;return`
    <article class="analysis-history-item">
      <div class="analysis-history-item__main">
        <strong>${c(t)}</strong>
        <span class="analysis-history-item__label">참고 구간</span>
      </div>
      <div class="analysis-history-item__stats">
        <span>전체 진행 참고 <em>${s}</em></span>
        <span>확인된 미흡 <em>${c(String(n))}건</em></span>
      </div>
    </article>
  `}function ts(){const e=p("analysisHistory"),t=p("analysisHistoryMeta");if(e)try{const s=tr();if(t&&(t.textContent=s.length?`${s.length}건`:"기록 없음"),!s.length){X=1,e.innerHTML=`
        <div class="analysis-history-empty" role="status">
          <strong>아직 저장된 진단 결과가 없습니다</strong>
          <p>확인 목록을 만들면 최근 결과가 여기에 쌓입니다. 인증 심사 자료가 아니라 내부 참고용입니다.</p>
        </div>
      `;return}const n=Math.max(1,Math.ceil(s.length/$t));X=Math.min(Math.max(1,X),n);const a=(X-1)*$t,r=s.slice(a,a+$t),o=n>1?`
        <nav class="analysis-history-pager" aria-label="이전 진단 페이지">
          ${Array.from({length:n},(l,d)=>{const u=d+1,f=u===X;return`
              <button
                type="button"
                class="analysis-history-page${f?" is-active":""}"
                data-history-page="${u}"
                aria-label="${u}페이지"
                aria-current="${f?"page":"false"}"
              >${u}</button>
            `}).join("")}
        </nav>
      `:"";e.innerHTML=`
      <div class="analysis-history-list">
        ${r.map(nr).join("")}
      </div>
      ${o}
    `,e.querySelectorAll("[data-history-page]").forEach(l=>{l.addEventListener("click",()=>{const d=Number(l.getAttribute("data-history-page"));!Number.isFinite(d)||d===X||(X=d,ts(),p("analysisHistoryDetails")?.setAttribute("open",""))})})}catch{t&&(t.textContent="기록 없음"),e.innerHTML=""}}function ar(e){const t=e?.dataset?.insightToggle;if(!t)return;const s=e.closest(".insight-card"),n=e.closest("#problemAnalysisContent")?i.expandedProblemClusters:i.expandedMultigaps,a=!n.has(t);a?n.add(t):n.delete(t),s&&(s.classList.toggle("open",a),e.setAttribute("aria-expanded",a?"true":"false"),e.textContent=a?"▴":"▾")}function ir(){if(!i.analysis){$("먼저 결과 탭에서 목록을 준비하세요.");return}const t=p("executiveReportStream")?.value||je(),s=new Blob([t],{type:"text/markdown;charset=utf-8"}),n=URL.createObjectURL(s),a=document.createElement("a");a.href=n,a.download=`isms-p-analysis-${Date.now()}.md`,a.click(),URL.revokeObjectURL(n),$("Markdown 파일을 저장했습니다.")}async function rr(){if(!i.analysis){$("먼저 진단 결과를 준비하세요.");return}const e=p("executiveReportStream")?.value||je();try{const t=await fetch("/controls/report/docx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:"ISMS-P 자가진단 결과 보고서",content:e})});if(!t.ok)throw new Error("DOCX 생성 실패");const s=await t.blob(),n=URL.createObjectURL(s),a=document.createElement("a");a.href=n,a.download=`isms-p-report-${Date.now()}.docx`,a.click(),URL.revokeObjectURL(n),$("Word 보고서를 저장했습니다.")}catch(t){$(`Word 내보내기 실패: ${t.message}`)}}function ue(e){const s={clusters:"overview",problems:"overview",multigap:"overview",deep:"overview",detail:"overview"}[e]||e||"actions";i.analyzeSection=["actions","overview"].includes(s)?s:"actions",document.querySelectorAll("[data-analyze-panel]").forEach(n=>{n.classList.toggle("active",n.dataset.analyzePanel===i.analyzeSection)})}function or({navigateToControl:e}){const t=p("view-analyze");!t||t.dataset.delegated==="1"||(t.dataset.delegated="1",t.addEventListener("click",s=>{const n=s.target.closest("[data-jump-control]");if(n&&t.contains(n)){s.preventDefault(),s.stopPropagation(),e(n.dataset.jumpControl);return}const a=s.target.closest("[data-insight-toggle]");a&&t.contains(a)&&(s.preventDefault(),s.stopPropagation(),ar(a))}))}function ne(e){return String(e||"").replace(/\s+/g," ").trim()}function He(e){let t=5381;for(const s of e)t=(t<<5)+t^s.charCodeAt(0);return(t>>>0).toString(36)}function lr(e){return e.startsWith("전체 준비도")?"전체 준비도":e.startsWith("가장 취약한 분야")?"취약 분야":e.startsWith("연쇄 리스크")?"연쇄 리스크":e.startsWith("다중 갭")?"다중 갭":e.startsWith("추가 겹침")?"추가 겹침 패턴":e.startsWith("최우선 점검 통제")?"최우선 점검":e.startsWith("상위 갭")?"상위 갭":"확인 항목"}function cr(e){const t=lr(e),s=e.match(/^전체 준비도\s+([\d.]+)%\s*[—\-]\s*(.+?)\.\s*갭\s+(\d+)건\s+중\s+미이행\s+(\d+)건,\s*미점검\s+(\d+)건,\s*부분 이행\s+(\d+)건/);if(s)return{title:t,kind:"readiness",metric:s[1],metricUnit:"%",headline:s[2],question:`현재 준비도 ${s[1]}%와 갭 ${s[3]}건의 구성을 확인했나요?`,explanation:"현재 입력된 통제 상태를 합산한 전체 진단 요약입니다. 수치와 단계가 현재 상황에 맞는지 확인하세요.",stats:[{label:"갭",value:s[3]},{label:"미이행",value:s[4],tone:"danger"},{label:"미점검",value:s[5],tone:"warn"},{label:"부분 이행",value:s[6],tone:"mid"}],body:""};const n=e.match(/^가장 취약한 분야는\s+'([^']+)'\(준비도\s+([\d.]+)%,\s*통제\s+(\d+)개\)입니다\.\s*(.*)$/);if(n)return{title:t,kind:"weak",metric:n[2],metricUnit:"%",headline:n[1],question:`'${n[1]}' 분야를 우선 보완 대상으로 검토할까요?`,explanation:`준비도가 가장 낮은 분야입니다. 관련 통제 ${n[3]}개의 담당자와 증적 보완 순서를 확인하세요.`,stats:[{label:"통제",value:n[3],tone:"warn"}],body:n[4]||e};const a=e.match(/^연쇄 리스크 경로:\s*(.+?)\s*[—\-]\s*(.*)$/);if(a){const l=a[1].split(/\s*→\s*/).map(d=>d.trim()).filter(Boolean);return{title:t,kind:"cascade",path:l,headline:l.length>1?`${l[0]} → ${l[l.length-1]}`:a[1],question:"이 통제 간 연쇄 위험을 실제 대응 범위에 포함할까요?",explanation:"앞 단계의 미흡이 뒤 통제의 운영·심사 위험으로 이어지는 경로입니다. 연결 관계가 실제 환경과 맞는지 확인하세요.",body:a[2]||e}}const r=e.match(/^다중 갭 겹침:\s*'([^']+)'\s*[—\-]\s*(.+?)\.\s*(.*)$/);if(r){const l=[...r[2].matchAll(/\b\d+(?:\.\d+){1,3}\b/g)].map(d=>d[0]);return{title:t,kind:"overlap",headline:r[1],chips:l,question:"동시에 미흡한 통제를 하나의 보완 과제로 묶을까요?",explanation:"개별 조치보다 공통 원인과 증적을 함께 정비할 때 효율적인 복합 갭 후보입니다.",body:`${r[2]}. ${r[3]}`.trim()}}const o=e.match(/^최우선 점검 통제:\s*(\d+(?:\.\d+){1,3})\s+(.+)$/);if(o){const l=o[2].trim(),d=l.match(/^(.+)\(([^()]*)\)\.\s*(.*)$/),u=l.match(/^(.+?)\.\s+(.*)$/),f=(d?.[1]||u?.[1]||l).trim(),m=d?.[2]?.trim()||"",g=(d?.[3]||u?.[2]||"").trim();return{title:t,kind:"priority",chips:[o[1]],headline:f,badge:m,question:`${o[1]} 통제를 최우선 점검 대상으로 확인할까요?`,explanation:"위험도와 연결 영향을 기준으로 먼저 확인할 통제입니다. 담당자·정책·증적 상태를 우선 점검하세요.",body:g}}return{title:t,kind:"generic",headline:e.length>72?`${e.slice(0,70)}…`:e,question:"이 인사이트를 현재 확인 목록에 반영할까요?",explanation:"분석 결과가 실제 조직 상황과 맞는지 검토한 뒤 처리하세요.",body:e}}const dr=["전체 진행 참고는 적용 통제 전체를 본 참고 구간입니다.","· 아직 안 본 통제도 미흡 쪽으로 반영합니다","· 표시: 양호 · 보통 · 보완 필요 · 기초 보완 필요","· 인증 배점·신뢰도가 아닌 점검 진행 참고용입니다"].join(`
`),ur=["점검분 이행 참고는 이미 점검한 통제만 본 참고 구간입니다.","· 미점검은 빼고 봅니다","· 표시: 양호 · 보통 · 보완 필요 · 기초 보완 필요","· 인증 배점·신뢰도가 아닌 이행 수준 참고용입니다"].join(`
`);function ss(e){const t=String(e||"");return t.includes("내부 참고")||t.includes("전체 진행 반영")||t==="전체 진행 참고"||t==="전체 진행 반영 점수"?"전체 진행 참고":t.includes("평가분")||t.includes("점검분만")||t.includes("점검분 이행")||t==="점검분 이행 참고"||t==="점검분만 이행 점수"?"점검분 이행 참고":D(t)}function Bn(e,t){const s=String(e?.label||""),n=ss(s);return n==="전체 진행 참고"||s.includes("내부 참고")||s.includes("전체 진행")?D(String(t?.overallScoreTooltip||dr).trim()):n==="점검분 이행 참고"||s.includes("평가분")||s.includes("점검분")?D(String(t?.assessedScoreTooltip||ur).trim()):D(String(e?.tooltip||"").trim())}function On(e={},t=null){const s=t||re?.analysis||i.analysis,n=new Set(["전체 진행 참고","점검분 이행 참고"]),a=Array.isArray(e.stats)?e.stats.map(u=>{const f=ss(u?.label);let m=u?.value;if(n.has(f)){const g=String(m??""),h=g.match(/([\d.]+)\s*%/);m=h?Se(h[1]):D(g)}return{...u,label:f,value:m,tooltip:Bn({...u,label:f},s)}}):e.stats,r=Array.isArray(e.basis)?e.basis.map(u=>D(u)):e.basis;let o=e.metric,l=e.metricUnit;const d=D(e.metricLabel);if(d==="점검분 이행 참고"||d==="전체 진행 참고"||String(e.metricUnit||"")==="%"){const u=Number(o);Number.isFinite(u)&&(d.includes("참고")||d.includes("점수"))&&(o=Se(u),l="")}return{...e,title:D(e.title),headline:D(e.headline),explanation:D(e.explanation),question:D(e.question),metricLabel:d,metric:o,metricUnit:l,body:D(e.body),nextAction:D(e.nextAction),stats:a,basis:r}}function Es(e=[]){if(!e.length)return"";const t=re?.analysis||i.analysis;return`
    <div class="report-review-stat-pills" aria-label="핵심 수치">
      ${e.map((s,n)=>{const a=ss(s.label),r=Bn({...s,label:a},t),o=`review-stat-tip-${n}-${He(a)}`,l=r?`
            <button
              type="button"
              class="report-review-pill-help"
              aria-describedby="${o}"
              aria-label="${c(a)} 계산 방법"
            >?</button>
            <span role="tooltip" id="${o}" class="report-review-pill-tooltip">${c(r)}</span>
          `:"";return`
        <span class="report-review-pill${s.tone?` is-${s.tone}`:""}${s.secondary?" is-secondary":""}${r?" has-tooltip":""}">
          <em>${c(a)}</em>
          <strong>${c(String(s.value))}</strong>
          ${l}
        </span>
      `}).join("")}
    </div>
  `}function pr(e){if(!Number.isFinite(Number(e)))return"";const t=Math.max(0,Math.min(100,Number(e)));return`
    <div class="report-review-coverage" aria-label="분야 점검 완료율 ${t}%">
      <span>분야 점검 완료율 <strong>${c(String(t))}%</strong></span>
      <div class="report-review-coverage-track" role="progressbar" aria-valuenow="${t}" aria-valuemin="0" aria-valuemax="100">
        <i style="width:${t}%"></i>
      </div>
    </div>
  `}function Te(e,t="근거 데이터"){return`
    <section class="report-review-evidence" aria-label="${c(t)}">
      <span class="report-review-evidence-label">${c(t)}</span>
      ${e}
    </section>
  `}function fr(e=[],t=[],s=""){return t.length?`
      <div class="report-review-path-map" aria-label="통제 영향 관계">
        ${t.map((n,a)=>`
          ${a?`
            <div class="report-review-path-connector" aria-label="${c(s||"영향 연결")}">
              <span>${c(s||"영향 연결")}</span>
              <i aria-hidden="true"></i>
            </div>
          `:""}
          <button
            type="button"
            class="report-review-path-card"
            data-review-open-control="${c(n.controlId||"")}"
            aria-label="${c(`${n.controlId||""} ${n.title||""} 지금 진단에서 열기`)}"
          >
            <span class="report-review-path-role">${c(n.role||"관련 통제")}</span>
            <strong>${c(n.title||n.controlId||"")}</strong>
            <div class="report-review-path-meta">
              <code>${c(n.controlId||"")}</code>
              <span class="report-review-node-status is-${c(n.level||"unknown")}">
                ${c(n.levelLabel||"미점검")}
              </span>
            </div>
          </button>
        `).join("")}
      </div>
    `:e.length?`
    <div class="report-review-path" aria-label="연쇄 경로">
      ${e.map((n,a)=>`
        ${a?'<span class="report-review-path-sep" aria-hidden="true"></span>':""}
        <span class="report-review-path-node">${c(n)}</span>
      `).join("")}
    </div>
  `:""}function jn(e,t={}){const s=String(e||"").trim(),n=(i.checklist||[]).find(m=>m.id===s)||(i.allControls||[]).find(m=>m.id===s),a=(i.analysis?.topGaps||i.analysis?.criticalGaps||[]).find(m=>m.controlId===s),r=Vi(s,t.level||a?.level||"unknown"),o=String(t.title||n?.title||a?.title||Ji(s)||"").trim(),l=o&&o!==s?o:o||s,d=String(n?.areaName||t.areaName||a?.areaName||Y[s.split(".")[0]]||"").trim(),u=String(n?.categoryName||t.categoryName||a?.categoryName||"").trim(),f=String(t.tip||a?.detailNarrativeTip||a?.organicAnalysis||a?.problem||"").replace(/\s+/g," ").trim();return{controlId:s,title:l,role:String(t.role||"").trim(),areaName:d,categoryName:u,tip:f.length>96?`${f.slice(0,94)}…`:f,level:r,levelLabel:U[r]||t.levelLabel||a?.levelLabel||r}}function Fn(e={}){const t=[],s=new Set,n=a=>{const r=String(a?.controlId||a||"").trim();!r||s.has(r)||(s.add(r),t.push(jn(r,typeof a=="object"?a:{})))};return[...e.controlNodes||[],...e.pathNodes||[]].forEach(n),(e.chips||[]).forEach(a=>n({controlId:a})),!t.length&&e.action?.controlId&&n({controlId:e.action.controlId}),t}function gr(e=[]){return e.length?`
    <div class="report-review-related-list" aria-label="지금 진단에서 열 통제">
      ${e.map(t=>{const s=[t.areaName,t.categoryName].filter(Boolean).join(" / ");return`
        <div class="report-review-related-row level-${c(t.level)}" data-review-open-control="${c(t.controlId)}">
          <div class="report-review-related-main">
            <div class="report-review-related-title">
              <code>${c(t.controlId)}</code>
              <strong>${c(t.title)}</strong>
              ${Ki(t.level,t.levelLabel)}
            </div>
            ${s?`<span class="report-review-related-meta">${c(s)}</span>`:""}
            ${t.tip?`<span class="report-review-related-tip">${c(t.tip)}</span>`:""}
            ${t.role&&t.role!==s?`<span class="report-review-related-role">${c(t.role)}</span>`:""}
          </div>
          <button type="button" class="report-review-open-btn" data-review-open-control="${c(t.controlId)}">
            지금 진단에서 열기
          </button>
        </div>
      `}).join("")}
    </div>
  `:'<p class="detail-empty">연결할 통제가 없습니다.</p>'}function mr(e=[]){return e.length?`
    <div class="report-review-control-list" aria-label="관련 통제 목록">
      ${e.map(t=>{const s=jn(t.controlId,t);return`
        <div class="report-review-control-row level-${c(s.level)}">
          <code>${c(s.controlId||"")}</code>
          <div class="report-review-control-copy">
            <strong>${c(s.title)}</strong>
            ${s.tip?`<span>${c(s.tip)}</span>`:""}
          </div>
          <span class="report-review-node-status is-${c(s.level)}">${c(s.levelLabel)}</span>
        </div>
      `}).join("")}
    </div>
  `:""}function vr(e=[]){return e.length?`
    <div class="report-review-chips">
      ${e.map(t=>`<span class="report-review-chip">${c(t)}</span>`).join("")}
    </div>
  `:""}function Re(e){const t=Array.isArray(e.basis)?e.basis.filter(Boolean):[],s={fact:"입력 사실",verified_finding:"확인된 판정",hypothesis:"확인 전 분석",action_required:"추가 진단 필요"}[e.classification]||"분석 참고";return`
    <aside class="report-review-guidance">
      <div class="report-review-trust-row">
        <span class="report-review-guidance-label">${c(s)}</span>
        <span class="report-review-confidence is-${c(e.confidenceLevel||"medium")}">
          ${c(e.confidenceLabel||"근거 확인 필요")}
        </span>
      </div>
      <strong>${c(e.question||"이 분석 결과를 확인했나요?")}</strong>
      <p>${c(e.explanation||"실제 조직 상황과 분석 결과가 일치하는지 확인하세요.")}</p>
      ${t.length?`
        <div class="report-review-basis">
          <span>판단 근거</span>
          <ul>${t.map(n=>`<li>${c(n)}</li>`).join("")}</ul>
        </div>
      `:""}
    </aside>
  `}function hr(e){const t=e.body?`<p class="report-review-body">${c(e.body)}</p>`:"";if(["readiness","coverage","finding","unreviewed","weak"].includes(e.kind)){const s=`
      <div class="report-review-hero">
        <div class="report-review-metric-block">
          <span class="report-review-metric-label">${c(e.metricLabel||e.title)}</span>
          <strong class="report-review-metric-value">
            ${c(String(e.metric??""))}<small>${c(e.metricUnit||"")}</small>
          </strong>
          ${e.kind==="weak"?'<span class="report-review-metric-hint">분야 점검 진행</span>':""}
        </div>
        <div class="report-review-hero-copy">
          <span>${c(e.kind==="weak"?"취약 분야":"분석 대상")}</span>
          <p class="report-review-headline">${c(e.headline||"")}</p>
          ${t}
        </div>
      </div>
      ${e.kind==="weak"?pr(e.coveragePercent):""}
      ${Es(e.stats)}
    `;return`
      <div class="report-review-main report-review-main--decide">
        ${Re(e)}
        ${Te(s)}
      </div>
    `}if(e.kind==="cascade"){const s=`
      <span class="report-review-route-label">${c(e.routeLabel||"통제 간 영향 경로")}</span>
      ${fr(e.path,e.pathNodes,e.relationLabel)}
      <div class="report-review-cascade-summary">
        <span>이 관계의 의미</span>
        <strong>${c(e.headline||"")}</strong>
        ${e.nextAction?`<p><b>다음 행동</b>${c(e.nextAction)}</p>`:""}
      </div>
      ${t}
    `;return`
      <div class="report-review-main report-review-main--decide">
        ${Re(e)}
        ${Te(s,"연결 근거")}
      </div>
    `}if(e.kind==="overlap"){const s=`
      <p class="report-review-headline">${c(e.headline||"")}</p>
      ${Es(e.stats)}
      ${mr(e.controlNodes)}
      ${t}
    `;return`
      <div class="report-review-main report-review-main--decide">
        ${Re(e)}
        ${Te(s,"관련 통제")}
      </div>
    `}if(e.kind==="priority"){const s=`
      <p class="report-review-headline">
        ${c(e.headline||"")}
        ${e.badge?`<span class="report-review-inline-badge">${c(e.badge)}</span>`:""}
      </p>
      ${vr(e.chips)}
      ${t}
    `;return`
      <div class="report-review-main report-review-main--decide">
        ${Re(e)}
        ${Te(s)}
      </div>
    `}return`
    <div class="report-review-main report-review-main--decide">
      ${Re(e)}
      ${Te(t||`<p class="report-review-body">${c(e.headline||"")}</p>`)}
    </div>
  `}function yr(e){if(Object.prototype.hasOwnProperty.call(e||{},"reviewItems")&&Array.isArray(e?.reviewItems))return e.reviewItems.map((n,a)=>{const r=ne(n?.id)||`structured-${a}`,o=On({...n,title:ne(n?.title)||"확인 항목",kind:ne(n?.kind)||"generic",headline:ne(n?.headline),explanation:ne(n?.explanation),question:ne(n?.question)},e);return{id:He(r),title:o.title,text:o.headline,card:o}});const s={title:"분석 데이터 갱신 필요",kind:"compatibility",classification:"action_required",headline:"실행 중인 서버가 최신 확인 목록 형식을 제공하지 않습니다.",question:"서버를 최신 코드로 재시작한 뒤 확인 목록을 다시 만들까요?",explanation:"구형 문장 분석은 잘못된 갭 수와 카드 제목을 만들 수 있어 표시하지 않았습니다.",basis:["필수 응답 필드 reviewItems 누락","구형 서버와 최신 프론트엔드의 버전 불일치"],confidenceLevel:"high",confidenceLabel:"버전 불일치",body:""};return[{id:He("analysis-contract-mismatch"),title:s.title,text:s.headline,card:s}]}function br(e,t){const s=Number(e?.overallReadiness),n=[Number.isFinite(s)?s.toFixed(1):"na",Number(e?.gapCount)||0,...t.map(a=>`${a.id}:${He(JSON.stringify(a.card||{}))}`)].join("|");return`report-${He(n)}`}function Hn(e){return i.reportReview[e]||(i.reportReview[e]={confirmed:[],ignored:[]}),i.reportReview[e]}let re=null;function wr(e,t,s){const n=Hn(e);n.confirmed=n.confirmed.filter(r=>r!==t),n.ignored=n.ignored.filter(r=>r!==t),n[s].push(t);const a=Object.keys(i.reportReview);a.slice(0,Math.max(0,a.length-8)).forEach(r=>{delete i.reportReview[r]})}function $r(e){const t=re;if(!e||!t)return;const s=t.active?.card||{},n=Fn(s).find(r=>r.controlId===e);i.reportReturn={itemId:t.active?.id||"",itemTitle:s.title||t.active?.title||"확인 항목",controlId:e,controlTitle:n?.title||""};const a=p("analyzeContent");a&&(a.style.display=""),ue("actions"),wn(),$n(e),$(`${e} 지금 진단으로 이동했습니다.`)}function Sr(e){if(e.dataset.reviewBound==="1")return;e.dataset.reviewBound="1";const t=(s=null)=>{e.querySelectorAll(".report-review-pill.is-tip-open").forEach(n=>{s&&n===s||n.classList.remove("is-tip-open")})};e.addEventListener("pointerover",s=>{const n=s.target;if(!(n instanceof Element))return;const a=n.closest(".report-review-pill.has-tooltip");!a||!e.contains(a)||a.classList.contains("is-tip-open")||(t(a),a.classList.add("is-tip-open"))}),e.addEventListener("pointerout",s=>{const n=s.target;if(!(n instanceof Element))return;const a=n.closest(".report-review-pill.has-tooltip");if(!a||!e.contains(a))return;const r=s.relatedTarget instanceof Element?s.relatedTarget:null;r&&a.contains(r)||a.classList.remove("is-tip-open")}),e.addEventListener("click",s=>{const n=s.target;if(!(n instanceof Element))return;const a=n.closest("[data-jump-actions]");if(a&&e.contains(a)){const m=p("analyzeContent");m&&(m.style.display=""),ue("actions"),p("sessionMasterDetail")?.scrollIntoView({behavior:"smooth",block:"start"});return}const r=re;if(!r)return;if(n.closest(".report-review-pill-help")){s.preventDefault(),s.stopPropagation();const m=n.closest(".report-review-pill.has-tooltip");if(m){const g=!m.classList.contains("is-tip-open");t(g?m:null),m.classList.toggle("is-tip-open",g)}return}t();const o=n.closest("[data-review-related-toggle]");if(o&&e.contains(o)){s.preventDefault(),s.stopPropagation();const g=o.closest("[data-review-item-id]")?.querySelector("[data-review-related-panel]");if(!g)return;const h=g.hidden;g.hidden=!h,o.setAttribute("aria-expanded",h?"true":"false"),o.textContent=h?"관련 통제 접기":"관련 통제 펼치기",h&&g.scrollIntoView({behavior:"smooth",block:"nearest"});return}const l=n.closest("[data-review-open-control]");if(l&&e.contains(l)){s.preventDefault(),s.stopPropagation(),$r(l.dataset.reviewOpenControl||"");return}const d=n.closest("[data-review-decision]");if(d&&e.contains(d)&&r.active?.id){wr(r.fingerprint,r.active.id,d.dataset.reviewDecision),oe(r.analysis);return}const u=n.closest("[data-review-restore]");if(u&&e.contains(u)){r.current.ignored=[],oe(r.analysis);return}const f=n.closest("[data-review-reset]");if(f&&e.contains(f)){r.current.confirmed=[],r.current.ignored=[],oe(r.analysis);return}})}function kr(e){const t=Math.max(0,Number(e?.applicableControlCount)||0),s=Math.max(0,Number(e?.reviewedControlCount)||0),n=Math.max(0,Number(e?.unreviewedControlCount)||Math.max(0,t-s)),a=t?Math.round(s/t*100):0,r=e?.statusCounts||{},o=Math.max(0,Number(r.done)||0)+Math.max(0,Number(r.evidenced)||0),l=(Array.isArray(e?.categoryCoverage)?e.categoryCoverage:[]).map(u=>({name:ne(u?.category)||"미점검 분야",remaining:Math.max(0,(Number(u?.totalCount)||0)-(Number(u?.reviewedCount)||0))})).filter(u=>u.remaining>0).sort((u,f)=>f.remaining-u.remaining).slice(0,3),d=l.length?l.map(u=>`<li><span>${c(u.name)}</span><strong>${u.remaining}개 남음</strong></li>`).join(""):`<li><span>남은 통제</span><strong>${n}개</strong></li>`;return`<article class="report-review-empty report-review-empty--overview" role="status">
    <header class="report-review-empty-head">
      <div><span>진단 진행 현황</span><strong>${s} / ${t}개 점검 완료</strong></div>
      <em>${a}%</em>
    </header>
    <div class="report-review-empty-track" aria-label="진단 진행률 ${a}%"><i style="width:${a}%"></i></div>
    <div class="report-review-empty-sections">
      <section>
        <span>현재 확인 결과</span>
        <strong>점검한 ${s}개에서 확인된 미흡 없음</strong>
        <p>이행으로 기록된 통제는 ${o}개입니다. 이 결과는 전체가 아니라 현재까지 점검한 범위에 한정됩니다.</p>
      </section>
      <section>
        <span>다음 검토 대상</span>
        <ul>${d}</ul>
        <p>미점검 ${n}개는 아직 판단되지 않았으며 취약점으로 집계하지 않습니다.</p>
      </section>
    </div>
    <footer>
      <p>진단을 이어가면 확인된 미이행·부분 이행과 참고용 연계 분석이 이곳에 추가됩니다.</p>
      <button type="button" class="primary" data-jump-actions>자가진단 이어가기</button>
    </footer>
  </article>`}function Cr(e){return e.dataset.shell==="active"?{step:e.querySelector("[data-review-step]"),label:e.querySelector("[data-review-label]"),track:e.querySelector("[data-review-track-fill]"),host:e.querySelector("[data-review-card-host]")}:(e.dataset.shell="active",e.innerHTML=`
    <div class="report-review-progress" aria-label="확인 목록 검토 진행">
      <div class="report-review-progress-meta">
        <span class="report-review-step" data-review-step></span>
        <span class="report-review-progress-label" data-review-label></span>
      </div>
      <div class="report-review-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-label="검토 완료율">
        <i data-review-track-fill></i>
      </div>
    </div>
    <div class="report-review-card-host" data-review-card-host></div>
  `,{step:e.querySelector("[data-review-step]"),label:e.querySelector("[data-review-label]"),track:e.querySelector("[data-review-track-fill]"),host:e.querySelector("[data-review-card-host]")})}function Ar(e,t,s){const n=Fn(e);return`
    <article class="report-review-card is-${c(e.kind)}" data-review-item-id="${c(t.id)}">
      <header class="report-review-card-head">
        <span class="report-review-kicker">${c(e.title)}</span>
        <div class="report-review-head-actions">
          <span class="report-review-remain">남은 ${s}건</span>
        </div>
      </header>
      ${hr(e)}
      <footer class="report-review-card-footer">
        <p class="report-review-hint" title="이 확인은 참고 항목의 읽음 상태만 기록합니다. 실제 판정은 통제 점검에서 변경하세요.">
          참고 분석의 읽음 상태만 기록합니다. 실제 판정은 통제 점검에서 변경하세요.
        </p>
        <div class="report-review-actions">
          <button type="button" class="ghost" data-review-decision="ignored">이 참고 항목 숨기기</button>
          ${n.length?'<button type="button" data-review-related-toggle aria-expanded="false">관련 통제 펼치기</button>':""}
          <button type="button" class="primary" data-review-decision="confirmed">확인 완료</button>
        </div>
        ${n.length?`
          <div class="report-review-related" data-review-related-panel hidden>
            <div class="report-review-related-head">
              <h4>관련 통제 ${n.length}개</h4>
              <p>점검할 통제를 고르면 「지금 진단」으로 이동합니다. 확인 목록으로 언제든 돌아올 수 있습니다.</p>
            </div>
            ${gr(n)}
          </div>
        `:""}
      </footer>
    </article>
  `}function oe(e){const t=p("reportReviewQueue");if(!t)return;Sr(t);const s=yr(e);if(!s.length){t.dataset.shell="empty",re=null,t.innerHTML=kr(e);return}const n=br(e,s),a=Hn(n),r=new Set(a.confirmed),o=new Set(a.ignored),l=s.filter(w=>!r.has(w.id)&&!o.has(w.id)),d=s.length-l.length,u=l[0],f=s.length?Math.round(d/s.length*100):0,m=Math.min(d+1,s.length);if(!u){t.dataset.shell="complete",re={analysis:e,fingerprint:n,current:a,active:null},t.innerHTML=`
      <div class="report-review-progress" aria-label="확인 목록 검토 진행">
        <div class="report-review-progress-meta">
          <span class="report-review-step">완료 ${s.length}<em> / ${s.length}</em></span>
          <span class="report-review-progress-label">검토 완료 · 완료율 100%</span>
        </div>
        <div class="report-review-track" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" aria-label="검토 완료율">
          <i style="width:100%"></i>
        </div>
      </div>
      <div class="report-review-card-host">
        <article class="report-review-card is-complete" role="status">
          <header class="report-review-card-head">
            <span class="report-review-kicker">검토 완료</span>
            <div class="report-review-head-actions">
              <span class="report-review-remain">남은 0건</span>
            </div>
          </header>
          <div class="report-review-main report-review-main--decide">
            <aside class="report-review-guidance">
              <div class="report-review-trust-row">
                <span class="report-review-guidance-label">입력 사실</span>
                <span class="report-review-confidence is-high">검토 종료</span>
              </div>
              <strong>확인 목록 검토를 마쳤습니다</strong>
              <p>판정 숫자와 통제 ID는 그대로입니다. 다음 통제 진단으로 이어가세요.</p>
              <div class="report-review-basis">
                <span>검토 결과</span>
                <ul>
                  <li>전체 ${s.length}건</li>
                  <li>내용 확인 ${r.size}건</li>
                  <li>무시 ${o.size}건</li>
                </ul>
              </div>
            </aside>
            <section class="report-review-evidence" aria-label="근거 데이터">
              <span class="report-review-evidence-label">근거 데이터</span>
              <div class="report-review-stat-pills" aria-label="핵심 수치">
                <span class="report-review-pill">
                  <em>전체</em><strong>${s.length}</strong>
                </span>
                <span class="report-review-pill is-ok">
                  <em>내용 확인</em><strong>${r.size}</strong>
                </span>
                <span class="report-review-pill${o.size?" is-warn":""}">
                  <em>무시</em><strong>${o.size}</strong>
                </span>
              </div>
              <p class="report-review-headline">확인 목록 검토는 읽음 기록입니다. 실제 보완은 지금 진단에서 이어가세요.</p>
            </section>
          </div>
          <footer class="report-review-card-footer">
            <p class="report-review-hint">내용 확인은 읽음 기록만 남깁니다. 판정 변경은 통제 점검에서 하세요.</p>
            <div class="report-review-actions">
              ${o.size?'<button type="button" class="ghost" data-review-restore>무시한 항목 다시 보기</button>':'<button type="button" class="ghost" data-review-reset>처음부터 다시 검토</button>'}
              <button type="button" class="primary" data-jump-actions>지금 진단으로 이동</button>
            </div>
          </footer>
        </article>
      </div>
    `;return}const g=On(u.card||cr(u.text),e);re={analysis:e,fingerprint:n,current:a,active:{...u,card:g}};const h=Cr(t);if(h.step&&(h.step.innerHTML=`완료 ${d}<em> / ${s.length}</em>`),h.label&&(h.label.textContent=`지금 ${m}번째 · 완료율 ${f}%`),h.track){const w=h.track.parentElement;w&&w.setAttribute("aria-valuenow",String(f)),h.track.style.width=`${f}%`}if(h.host){const w=!!h.host.querySelector("[data-review-related-panel]:not([hidden])");if(h.host.innerHTML=Ar(g,u,l.length),w){const A=h.host.querySelector("[data-review-related-panel]"),E=h.host.querySelector("[data-review-related-toggle]");A&&(A.hidden=!1),E&&(E.setAttribute("aria-expanded","true"),E.textContent="관련 통제 접기")}}}let ve=null,Ze=null,he=null,Xe=null;function zn(e){return{assessments:i.assessments,scenarioId:i.analyzeScenarioId||null,sessionBundleMode:i.sessionBundleMode||"chain",controlChecks:i.controlChecks,domainChecks:e(),questChecks:i.questChecks||{},inputConfidence:i.inputConfidence||{},organizationProfile:i.organizationProfile,view:"full"}}function Er(e,t={},s){if(ve)return $("확인 목록을 이미 갱신하고 있습니다."),ve;Ze=new AbortController;const a=Ir(e,t,s,Ze.signal).finally(()=>{ve===a&&(ve=null,Ze=null)});return ve=a,ve}function _n(){Ze?.abort(),Xe?.abort(),i.reportStreamToken=(i.reportStreamToken||0)+1,i.aiReportWriting=!1,F()}function xr(e={}){if(he)return $("AI 리포트를 이미 진행하고 있습니다."),he;if(!i.analysis||!i.organizationProfile)return $("먼저 확인 목록을 갱신한 뒤 보고서를 작성하세요."),Promise.resolve();if(i.analysisStale)return $("진단이 변경되었습니다. 확인 목록을 먼저 갱신하세요."),Promise.resolve();Xe=new AbortController;const s=Lr(e,Xe.signal).finally(()=>{he===s&&(he=null,Xe=null)});return he=s,he}async function Lr({domainChecksPayload:e,renderAnalyzeView:t},s){const n=i.activeSessionId,a=()=>!s.aborted&&i.activeSessionId===n;i.aiReportWriting=!0,F();const r=p("executiveReportStream");r&&(r.dataset.userEdited="0");try{const o=await ke("/controls/report",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(zn(e)),signal:s});if(!a())return;o.clientAnalyzedAt=Date.now(),i.analysis=o,i.lastAiExecutiveReport=o.executiveReport||"",i.aiReportStale=!1,i.analysisStale=!1,[p("analysisStaleNoticeInline")].filter(Boolean).forEach(l=>{l.hidden=!0}),qn(o),t?.(!0),ts(),oe(o),o.verbalizeMeta,i.aiReportWriting=!1,F(),o.executiveReport?await sr(o.executiveReport):Fe(),$("AI 리포트를 마쳤습니다.")}catch(o){if(o.name==="AbortError"||!a())return;console.warn(o),Fe(),F(),$(`AI 리포트 실패: ${o.message}`)}finally{a()&&(i.aiReportWriting=!1,F())}}async function Ir(e,t={},{showProfileWizard:s,switchView:n,domainChecksPayload:a,renderProfileContext:r,renderStats:o,syncAssessmentsFromApplicability:l,renderAnalyzeView:d},u){if(!i.organizationProfile){s(),$("먼저 점검 범위를 적용한 뒤 확인 목록을 만드세요.");return}const f=i.activeSessionId,m=()=>!u.aborted&&i.activeSessionId===f,g=p("analysisReportPanel"),h=p("analyzeContent"),w=p("workspaceLoadingSkeleton"),A=p("view-analyze");e!==!1&&(n("analyze",{skipAutoAnalyze:!0}),h.style.display="none",g&&(g.style.display="none"),w&&(w.hidden=!1,w.dataset.analysisLoading="true",w.dataset.loadingSessionId=f||""),A?.classList.add("is-workspace-loading"),A?.setAttribute("aria-busy","true"));try{const E=await ke("/controls/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(zn(a)),signal:u});if(!m())return;const y=!!i.lastAiExecutiveReport;if(E.clientAnalyzedAt=Date.now(),i.analysis=E,i.reportReview={},i.analysisStale=!1,i.aiReportStale=y,[p("analysisStaleNoticeInline")].filter(Boolean).forEach(L=>{L.hidden=!0}),i.scopeDraft=E.scopeDraft||i.scopeDraft,r(),l(E),me(),o(),i.analyzeSection="actions",ue("actions"),h&&(h.style.display="",h.classList.add("analyze-content-fade")),d(!0),!m()||(qn(E),ts(),g&&(g.style.display="",oe(E),E.verbalizeMeta,Fe({preferTemplate:!y}),F()),!m()))return;e!==!1&&n("analyze",{skipAutoAnalyze:!0}),t.successToast&&$(t.successToast)}catch(E){if(E.name==="AbortError"||!m())return;h&&(h.style.display=""),g&&(g.style.display="none"),$("확인 목록 생성 실패: "+E.message)}finally{w?.dataset.loadingSessionId===(f||"")&&(w.hidden=!0,delete w.dataset.analysisLoading,delete w.dataset.loadingSessionId,A?.classList.remove("is-workspace-loading"),A?.removeAttribute("aria-busy"))}}function Tr(){let e=document.getElementById("defectEvidenceDialog");return e||(e=document.createElement("dialog"),e.id="defectEvidenceDialog",e.className="app-modal defect-evidence-dialog",e.setAttribute("aria-labelledby","defectEvidenceTitle"),e.innerHTML='<div class="app-modal-shell defect-dialog-shell"><header class="app-modal-header"><div><span class="app-modal-eyebrow">우선순위 산정 근거</span><h3 id="defectEvidenceTitle"></h3><p>선정 근거와 참고 사례를 구분해 확인하세요.</p></div><button type="button" class="app-modal-close" data-close-defect-dialog aria-label="우선순위 근거 창 닫기">×</button></header><div id="defectEvidenceBody" class="app-modal-scroll defect-dialog-body"></div></div>',document.body.appendChild(e),e.querySelector("[data-close-defect-dialog]")?.addEventListener("click",()=>e.close()),e.addEventListener("click",t=>{t.target===e&&e.close()}),e)}function Rr(e){const t=e?.defectEvidence;if(!t)return;const s=Tr(),n=s.querySelector("#defectEvidenceTitle"),a=s.querySelector("#defectEvidenceBody");n&&(n.textContent=`${e.controlId} ${e.title}`),a&&(a.innerHTML=`
    <section><h4>과거 결함현황 매핑</h4><p>현행 통제에 연결된 과거 결함 <strong>${t.defectCount||0}건</strong>${t.caseCount?` · 사례집 결함 유형 ${t.caseCount}건`:""}</p>
      ${(t.mappedSources||[]).length?`<ul>${t.mappedSources.map(r=>`<li>${c(r)}</li>`).join("")}</ul>`:""}
    </section>
    <section><h4>공식 안내서 결함 사례</h4>
      ${(t.examples||[]).length?`<ol>${t.examples.map(r=>`<li>${c(r)}</li>`).join("")}</ol>`:'<p class="detail-empty">이 통제에 수록된 결함 사례 문구가 없습니다.</p>'}
      ${t.sourceDoc?`<p class="defect-dialog-source">출처: ${c(t.sourceDoc)}${(t.pages||[]).length?` · ${t.pages.map(r=>`${r}쪽`).join(", ")}`:""}</p>`:""}
    </section>
    <p class="defect-dialog-caution">과거 결함 빈도는 점검 순서를 정하기 위한 참고 근거입니다. 현재 조직에서 같은 결함이 발생했다는 판정은 아닙니다.</p>`),s.showModal()}function Pr(e){const t=p("gapClustersPanel"),s=p("gapClusters"),n=p("gapClustersEmpty"),a=p("gapClustersCount");if(!(!t||!s)){if(a&&(a.textContent=`${(e||[]).length}개 묶음`),!e||!e.length){Ss(t,n,!0,[s]),n&&(n.innerHTML=Ui(i.analysis||{})),s.innerHTML="";return}Ss(t,n,!1,[s]),s.innerHTML=e.map(r=>{const o=r.controls||[],l=r.primaryControl||o[0]||null,d=o.filter(u=>u.controlId!==l?.controlId);return`
      <article class="gap-cluster-card">
        <h4>${c(r.theme)} <span class="severity-badge ${c(r.severity||"medium")}">미흡 ${r.gapCount}개</span></h4>
        <div class="gap-cluster-status" aria-label="미흡 상태 구성">
          ${r.noneCount?`<span class="level-none">미이행 ${r.noneCount}개</span>`:""}
          ${r.partialCount?`<span class="level-partial">부분 이행 ${r.partialCount}개</span>`:""}
        </div>
        ${l?`
          <div class="gap-cluster-primary">
            <span>우선 보완</span>
            <strong>${c(l.controlId)} ${c(l.title)}</strong>
            <div class="gap-cluster-basis">
              <b>선정 근거</b>
              <ul>${(l.selectionReasons||[]).map(u=>`<li>${c(u)}</li>`).join("")||"<li>현재 상태와 통제 우선순위를 기준으로 선정했습니다.</li>"}</ul>
            </div>
            ${l.riskIfMissing?`<p class="gap-cluster-risk"><b>미흡 시 영향</b>${c(l.riskIfMissing)}</p>`:""}
            <p class="gap-cluster-next"><b>다음 조치</b>${c(l.nextAction||"진단 상태와 필요한 증적을 확인하세요.")}</p>
            <div class="gap-cluster-actions">
              ${l.defectEvidence?`<button type="button" class="gap-evidence-button" data-open-defect-evidence="${c(l.controlId)}">매핑 근거·사례 보기</button>`:""}
              <button type="button" class="gap-check-button" data-jump-control="${c(l.controlId)}">이 통제 점검하기</button>
            </div>
          </div>
        `:`<p>${c(r.summary)}</p>`}
        ${d.length?`
          <div class="gap-cluster-related">
            <span>함께 확인</span>
            <div class="related-chips">
              ${d.map(u=>{const f=`${u.controlId} ${u.title} · ${u.levelLabel}. ${u.nextAction||"클릭하면 해당 통제로 이동합니다."}`;return`<button type="button" class="related-chip ui-tip" data-jump-control="${c(u.controlId)}" data-tip="${c(As(f))}" title="${c(As(f))}">${c(u.controlId)}</button>`}).join("")}
            </div>
          </div>
        `:""}
      </article>
    `}).join(""),s.querySelectorAll("[data-open-defect-evidence]").forEach(r=>{r.addEventListener("click",()=>{const o=e.find(l=>l.primaryControl?.controlId===r.dataset.openDefectEvidence)?.primaryControl;Rr(o)})})}}function Mr(e,{renderConfirmationActions:t}){const s=i.analysis;if(!s)return;if(!e){p("analyzeContent").style.display="";const v=p("analysisReportPanel");v&&(s.executiveReport||i.lastAiExecutiveReport)&&(v.style.display="",Fe(),oe(s))}const n=s.areaCoverage||{},a=(s.categoryCoverage||s.weakCategories||[]).map(v=>{const S=Number(v.reviewedCount??0),b=Number(v.totalCount??v.count??0),k=Number.isFinite(Number(v.coveragePercent))?Number(v.coveragePercent):b>0?S/b*100:0,I=Qe(k);return{...v,reviewed:S,total:b,pct:I}}),r=a.reduce((v,S)=>v+S.reviewed,0),o=a.reduce((v,S)=>v+S.total,0),l=Qe(o>0?r/o*100:0),d=o>0&&r>=o,u=p("categoryCoverageSummary"),f=p("categoryCoverageList"),m=p("categoryListCount");if(m&&(m.textContent=`중분류 ${a.length}개 · 스크롤하여 전체 보기`),u&&(u.classList.toggle("is-complete",d),u.innerHTML=o?`
      <div class="category-summary-copy" role="status">
        <strong>${d?`적용 통제 ${o}개 점검 완료`:`통제 ${r}/${o}개 점검 완료`}</strong>
        <span>전체 점검 진행률 ${Cs(l)}%</span>
        <span class="category-summary-progress" role="progressbar" aria-label="전체 통제 점검 진행률" aria-valuenow="${l}" aria-valuemin="0" aria-valuemax="100"><i style="width:${l}%"></i></span>
      </div>
    `:""),f){const v=new Map;a.forEach(S=>{const b=S.areaId||S.areaName||String(S.categoryId||"기타").split(".")[0];if(!v.has(b)){const k=S.areaName||"기타";v.set(b,{areaName:k,coverage:n[k]||null,items:[]})}v.get(b).items.push(S)}),f.hidden=a.length===0,f.innerHTML=Array.from(v.values()).map(S=>{const b=S.items.sort((C,T)=>String(C.categoryId||"").localeCompare(String(T.categoryId||""),void 0,{numeric:!0})),k=Number(S.coverage?.reviewedCount??b.reduce((C,T)=>C+T.reviewed,0)),I=Number(S.coverage?.totalCount??b.reduce((C,T)=>C+T.total,0)),_=Qe(S.coverage?.coveragePercent??(I?k/I*100:0));return`
        <details class="category-area-group" open>
          <summary>
            <strong>${c(S.areaName)}</strong>
            <span class="category-area-progress" role="progressbar" aria-label="${c(S.areaName)} 점검 완료율" aria-valuenow="${_}" aria-valuemin="0" aria-valuemax="100"><i style="width:${_}%"></i></span>
            <span>${k}/${I} · ${Cs(_)}%</span>
          </summary>
          <div class="category-coverage-rows">
            ${b.map(C=>{const T=C.reviewed>=C.total?"done":C.reviewed>0?"progress":"idle",O=T==="done"?"완료":T==="progress"?"진행 중":"미점검";return`
                <div class="category-coverage-row ${C.pct<100?"is-pending":"is-complete"}">
                  <span class="category-coverage-id">${c(C.categoryId||"-")}</span>
                  <strong>${c(C.category)}</strong>
                  <span class="category-coverage-progress" role="progressbar" aria-label="${c(C.category)} 점검 완료율" aria-valuenow="${C.pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${C.pct}%"></i></span>
                  <span class="category-coverage-count">${C.reviewed}/${C.total}</span>
                  <span class="category-coverage-state is-${T}">${O}</span>
                </div>
              `}).join("")}
          </div>
        </details>
      `}).join("")||'<p class="detail-empty">분류별 점검 정보 없음</p>',p("categoryViewActions")?.querySelectorAll("[data-category-view]").forEach(S=>{S.onclick=()=>{const b=S.dataset.categoryView==="expand";f.querySelectorAll(".category-area-group").forEach(k=>{k.open=b})}})}const g=p("statusBreakdown");if(g){const v=s.statusCounts||{},S={unknown:v.unknown||0,none:v.none||0,partial:v.partial||0,done:(v.done||0)+(v.evidenced||0),na:v.na||0},b=["unknown","none","partial","done","na"];g.innerHTML=b.map(k=>`
      <div class="status-breakdown-item">
        <span class="level-${k}">${U[k]}</span>
        <strong>${S[k]||0}</strong>
      </div>
    `).join("")}t(s);const h=s.cascadeChains||[],w=p("linkedProblemsCount");w&&(w.textContent=`${h.length}건`);const A=p("linkedProblemsSummary"),E=()=>{let v=document.getElementById("linkEvidenceDialog");return v||(v=document.createElement("dialog"),v.id="linkEvidenceDialog",v.className="app-modal link-evidence-dialog",v.setAttribute("aria-labelledby","linkEvidenceTitle"),v.innerHTML='<div class="app-modal-shell link-dialog-shell"><header class="app-modal-header"><div><span class="app-modal-eyebrow">통제 간 연계 점검</span><h3 id="linkEvidenceTitle"></h3><p>연계 가설과 실제 확인 항목을 분리해 검토하세요.</p></div><button type="button" class="app-modal-close" data-close-link-dialog aria-label="연계 근거 창 닫기">×</button></header><div id="linkEvidenceBody" class="app-modal-scroll link-dialog-body"></div></div>',document.body.appendChild(v),v.querySelector("[data-close-link-dialog]")?.addEventListener("click",()=>v.close()),v.addEventListener("click",S=>{S.target===v&&v.close()}),v)},y=v=>{const S=E(),b=(v.relationEvidence||[]).flatMap(k=>(k.refs||[]).filter(I=>I.snippet).map(I=>({type:k.type,...I})));S.querySelector("#linkEvidenceTitle").textContent=`${v.originControlId} ${v.originTitle||""} → ${v.targetControlId} ${v.targetTitle||""}`,S.querySelector("#linkEvidenceBody").innerHTML=`
      <section class="link-dialog-summary"><h4>왜 같이 확인하나요?</h4><p><b>${c(v.originControlId)} ${c(v.originTitle||"선행 통제")}에서 결정한 내용이 ${c(v.targetControlId)} ${c(v.targetTitle||"후속 통제")}의 실행계획에 빠짐없이 반영됐는지 확인합니다.</b></p><p>${c(v.connectionReason||"")}</p><span class="link-grounding-level">${c(v.evidenceLabel||"실무 관계 가설")}</span></section>
      <section><h4>1. 준비할 자료</h4><div class="link-artifact-grid"><div><b>${c(v.originControlId)} ${c(v.originTitle||"")}</b><ul>${(v.sourceArtifacts||[]).map(k=>`<li>${c(k)}</li>`).join("")||"<li>선행 판단·승인 문서</li>"}</ul></div><div><b>${c(v.targetControlId)} ${c(v.targetTitle||"")}</b><ul>${(v.targetArtifacts||[]).map(k=>`<li>${c(k)}</li>`).join("")||"<li>후속 실행·점검 기록</li>"}</ul></div></div></section>
      <section><h4>2. 표본 3~5건을 이렇게 대조하세요</h4><div class="link-compare-table"><div class="link-compare-head"><b>대조 키</b><b>선행 자료</b><b>후속 자료</b><b>결함 신호</b></div>${(v.comparisonRows||[]).map(k=>`<div><b>${c(k.key)}</b><span>${c(k.source)}</span><span>${c(k.target)}</span><em>${c(k.fail)}</em></div>`).join("")}</div></section>
      <section class="link-result-guide"><h4>3. 대조 결과는 이렇게 해석하세요</h4><div><span class="is-problem">문제 있음</span><p>${c(v.decisionRule||"선행 결정과 후속 실행을 동일 표본으로 추적할 수 없는 경우")}</p></div><div><span class="is-clear">문제 없음</span><p>${c(`${v.originControlId} ${v.originTitle||"선행 통제"}의 대상과 결정이 ${v.targetControlId} ${v.targetTitle||"후속 통제"} 자료에 빠짐없이 반영되고, 표본별 담당자·시점·결과까지 이어지는 경우`)}</p></div></section>
      ${b.length?`<details class="link-direct-evidence"><summary>직접 연결을 뒷받침하는 사례집 문구</summary>${b.map(k=>`<blockquote>${c(k.snippet)}</blockquote><small>${c(k.doc||"")}${k.ref?` · ${c(k.ref)}`:""}</small>`).join("")}</details>`:'<p class="link-dialog-caution">이 경로에는 직접 인용 근거가 없습니다. 공식 결함 사례는 연계를 증명하지 않으므로 표시하지 않았습니다. 반드시 위 표본 대조 결과로만 연계 문제를 판정하세요.</p>'}`,S.showModal()},L=p("linkedProblemsPanel");L&&L.classList.toggle("is-empty",!h.length),A&&(A.classList.toggle("is-empty",!h.length),A.innerHTML=h.length?h.map(v=>`
        <article class="linked-problem-card severity-${c(v.severity||"medium")}">
          <header>
            <span class="linked-problem-kind">통제 간 영향 경로</span>
            <span class="linked-problem-severity">${c(v.severity==="critical"?"높은 영향":"영향 가능성")}</span>
          </header>
          <div class="linked-problem-route">
            <div class="linked-problem-node">
              <span>확인된 약점</span>
              <strong>${c(v.originControlId)} ${c(v.originTitle||"")}</strong>
              <em class="level-${c(v.originLevel||"unknown")}">${c(v.originLevelLabel||"미점검")}</em>
            </div>
            <span class="linked-problem-arrow" aria-hidden="true">→</span>
            <div class="linked-problem-node">
              <span>영향 통제</span>
              <strong>${c(v.targetControlId)} ${c(v.targetTitle||"")}</strong>
              <em class="level-${c(v.targetLevel||"unknown")}">${c(v.targetLevelLabel||"미점검")}</em>
            </div>
          </div>
          <div class="linked-problem-body">
            <section>
              <h4>왜 연결되는가</h4>
              <ol class="linked-problem-logic">
                ${((v.logicSteps||[]).length?v.logicSteps:[v.connectionReason||"두 통제의 운영 및 증적이 서로 의존하는 경로입니다."]).map(S=>`<li>${c(S)}</li>`).join("")}
              </ol>
            </section>
            <section>
              <h4>함께 확인할 증거</h4>
              <ul class="linked-problem-evidence">
                ${((v.evidenceToCheck||[]).length?v.evidenceToCheck:["양쪽 통제의 기준·승인 기록과 실제 운영 기록을 함께 대조해야 합니다."]).map(S=>`<li>${c(S)}</li>`).join("")}
              </ul>
            </section>
            <section>
              <h4>예상 영향</h4>
              <div class="linked-problem-impact">
                <p><b>운영</b>${c(v.operationalImpact||v.impact||"선행 통제의 미흡이 후속 통제의 운영 범위와 일관성에 영향을 줄 수 있습니다.")}</p>
                <p><b>심사</b>${c(v.auditImpact||"선행 판단과 후속 실행의 증적이 연결되지 않으면 추가 소명이나 보완 요구로 이어질 수 있습니다.")}</p>
              </div>
            </section>
            <footer>
              <div><span>${c(v.evidenceLabel||"해석형 연결")}</span><p>${c(v.groundingNote||"통제 간 관계는 참고 가설이며 실제 조직의 업무 흐름과 증적으로 확인해야 합니다.")}</p></div>
              <button type="button" data-link-evidence="${c(v.originControlId)}::${c(v.targetControlId)}">연계 근거 상세</button>
            </footer>
          </div>
        </article>
      `).join(""):Gi(s),A.querySelectorAll("[data-link-evidence]").forEach(v=>{v.addEventListener("click",()=>{const[S,b]=v.dataset.linkEvidence.split("::"),k=h.find(I=>I.originControlId===S&&I.targetControlId===b);k&&y(k)})})),Pr(s.gapClusters||[])}const Nr=4;let ze=1,Dt=null;function Un(){ze=1}function Dr(e,t,s=Nr){const n=Array.isArray(e)?e:[],a=Math.max(1,Math.ceil(n.length/s)||1),r=Math.min(Math.max(1,Number(t)||1),a),o=(r-1)*s;return{current:r,pageCount:a,total:n.length,items:n.slice(o,o+s)}}function qr(e,t){const s=Math.max(1,t),n=Math.min(Math.max(1,e),s);if(s<=7)return Array.from({length:s},(r,o)=>o+1);const a=new Set([1,s,n-1,n,n+1]);return n<=3&&[2,3,4].forEach(r=>a.add(r)),n>=s-2&&[s-3,s-2,s-1].forEach(r=>a.add(r)),[...a].filter(r=>r>=1&&r<=s).sort((r,o)=>r-o)}function Br(e){const t=new Date(e);return Number.isNaN(t.getTime())?"수정 시간 없음":new Intl.DateTimeFormat("ko-KR",{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(t)}function Or(e){const t=Qs(e,i.checklist?.length||101),s=t.percent>=100?{className:"is-complete",label:"완료",action:"결과 보기",icon:'<svg viewBox="0 0 24 24"><path d="m6.5 12.5 3.5 3.5 7.5-8"/></svg>'}:t.percent>0?{className:"is-active",label:"진행 중",action:"이어하기",icon:'<svg viewBox="0 0 24 24"><path d="m9 7 7 5-7 5V7Z"/></svg>'}:{className:"is-new",label:"시작 전",action:"시작하기",icon:'<svg viewBox="0 0 24 24"><path d="M12 7v10M7 12h10"/></svg>'};return`
    <article class="diagnosis-session-card ${s.className}" data-session-id="${c(e.id)}">
      <span class="diagnosis-session-state" aria-hidden="true">${s.icon}</span>
      <div class="diagnosis-session-copy">
        <div class="diagnosis-session-heading">
          <strong class="diagnosis-session-name">${c(e.name)}</strong>
          <button type="button" class="diagnosis-session-rename-btn" data-session-rename aria-label="${c(e.name)} 이름 변경">
            <svg aria-hidden="true" viewBox="0 0 20 20"><path d="M12.4 4.1 15.9 7.6 7.5 16H4v-3.5L12.4 4.1Z"/><path d="M11.2 5.3 14.7 8.8"/></svg>
          </button>
          <span class="diagnosis-session-badge">${s.label}</span>
        </div>
        <span>마지막 수정 ${c(Br(e.updatedAt))}</span>
        <code title="진단 ID">진단 ID · ${c(e.id.slice(0,8))}</code>
      </div>
      <div class="diagnosis-session-progress" aria-label="진단 진행률 ${t.percent}%">
        <div>
          <span>진행률</span>
          <strong>${t.percent}% · ${t.reviewed}/${t.applicable}</strong>
        </div>
        <div class="diagnosis-session-track" role="progressbar" aria-valuenow="${t.percent}" aria-valuemin="0" aria-valuemax="100">
          <i style="width:${t.percent}%"></i>
        </div>
      </div>
      <div class="diagnosis-session-actions">
        <button type="button" class="primary" data-session-open>${s.action} <svg aria-hidden="true" viewBox="0 0 20 20"><path d="M4 10h11M11 6l4 4-4 4"/></svg></button>
        <div class="diagnosis-session-secondary">
          <button type="button" data-session-rename>이름 변경</button>
          <button type="button" data-session-duplicate>복제</button>
          <button type="button" data-session-export>내보내기</button>
          <button type="button" class="danger" data-session-delete>삭제</button>
        </div>
      </div>
    </article>
  `}function jr(e,t){if(!e||e.classList.contains("is-renaming")||typeof t!="function")return;const s=e.querySelector(".diagnosis-session-name");if(!s)return;const n=s.textContent||"",a=document.createElement("input");a.type="text",a.className="diagnosis-session-name-input",a.value=n,a.maxLength=Js,a.setAttribute("aria-label","진단 이름"),a.autocomplete="off",a.spellcheck=!1,e.classList.add("is-renaming"),s.replaceWith(a),a.focus(),a.select();let r=!1;const o=()=>{a.isConnected&&(a.replaceWith(s),e.classList.remove("is-renaming"))},l=d=>{if(r)return;r=!0;const u=a.value.replace(/\s+/g," ").trim();if(!d){o();return}if(!u){o(),$("진단 이름을 입력해 주세요.",{tone:"warning"});return}t(e.dataset.sessionId,u)};a.addEventListener("keydown",d=>{d.key==="Enter"&&(d.preventDefault(),a.blur(),l(!0)),d.key==="Escape"&&(d.preventDefault(),l(!1))}),a.addEventListener("blur",()=>l(!0))}function St(e,t,s={}){const n=s.current?' aria-current="page"':"",a=s.disabled?" disabled":"",r=s.ariaLabel?` aria-label="${c(s.ariaLabel)}"`:"";return`<button type="button" data-session-page="${e}"${n}${a}${r}>${t}</button>`}function Fr(e,t,s){if(!e)return;if(s<=1){e.hidden=!0,e.innerHTML="";return}e.hidden=!1;const n=qr(t,s),a=[St(t-1,'<svg aria-hidden="true" viewBox="0 0 20 20"><path d="M12 5 7 10l5 5"/></svg>',{disabled:t<=1,ariaLabel:"이전 페이지"})];let r=0;n.forEach(o=>{r&&o>r+1&&a.push('<span class="diagnosis-session-pager-gap" aria-hidden="true">...</span>'),a.push(St(o,String(o),{current:o===t,ariaLabel:`${o}페이지`})),r=o}),a.push(St(t+1,'<svg aria-hidden="true" viewBox="0 0 20 20"><path d="m8 5 5 5-5 5"/></svg>',{disabled:t>=s,ariaLabel:"다음 페이지"})),e.innerHTML=a.join(""),e.querySelectorAll("[data-session-page]").forEach(o=>{o.addEventListener("click",()=>{const l=Number(o.dataset.sessionPage);!Number.isInteger(l)||l===ze||(ze=l,Dt&&Gn(Dt))})})}function Gn({onOpen:e,onCreate:t,onDuplicate:s,onRename:n,onExport:a,onImport:r,onDelete:o}){const l=p("diagnosisSessionList");if(!l)return;Dt={onOpen:e,onCreate:t,onDuplicate:s,onRename:n,onExport:a,onImport:r,onDelete:o};const d=[...i.diagnosisSessions].sort((h,w)=>new Date(w.updatedAt).getTime()-new Date(h.updatedAt).getTime()),u=Dr(d,ze);ze=u.current,l.innerHTML=u.total?u.items.map(Or).join(""):`
      <section class="diagnosis-session-empty" role="status">
        <strong>저장된 진단이 없습니다</strong>
        <p>새 진단을 만들면 현재 브라우저에 독립된 진단 프로젝트로 저장됩니다.</p>
      </section>
    `,Fr(p("diagnosisSessionPager"),u.current,u.total?u.pageCount:0),l.querySelectorAll("[data-session-open]").forEach(h=>{h.addEventListener("click",()=>{e(h.closest("[data-session-id]")?.dataset.sessionId)})}),l.querySelectorAll("[data-session-rename]").forEach(h=>{h.addEventListener("click",()=>{jr(h.closest("[data-session-id]"),n)})}),l.querySelectorAll("[data-session-duplicate]").forEach(h=>{h.addEventListener("click",()=>{s(h.closest("[data-session-id]")?.dataset.sessionId)})}),l.querySelectorAll("[data-session-delete]").forEach(h=>{h.addEventListener("click",()=>{o(h.closest("[data-session-id]")?.dataset.sessionId)})}),l.querySelectorAll("[data-session-export]").forEach(h=>{h.addEventListener("click",()=>{a(h.closest("[data-session-id]")?.dataset.sessionId)})});const f=p("createDiagnosisSessionBtn");f&&(f.onclick=t);const m=p("importDiagnosisSessionBtn"),g=p("importDiagnosisSessionInput");m&&g&&(m.onclick=()=>g.click(),g.onchange=async()=>{const h=g.files?.[0];g.value="",h&&await r(h)})}function ot(){const e=p("sessionPicker"),t=p("appMain");e&&(e.hidden=!1),t&&(t.hidden=!0)}function ns(){const e=p("sessionPicker"),t=p("appMain");e&&(e.hidden=!0),t&&(t.hidden=!1)}let et=!1,kt=!1,Ct=null;function Hr(){if(!Ct){if(!document.querySelector("link[data-report-editor-style]")){const t=document.createElement("link");t.rel="stylesheet",t.href="/controls/map/assets/react-dist/report-editor.css?v=20260820-1",t.dataset.reportEditorStyle="1",document.head.append(t)}Ct=import("/controls/map/assets/react-dist/report-editor.js?v=20260820-1")}return Ct}let le=null;async function zr(e,{toastMessage:t,runAnalyzeAfter:s=!0,switchToAnalyze:n=!0}={}){La(e),i.analyzeScenarioId=null,i.sessionBundleMode=i.sessionBundleMode||"chain",i.pendingProfile=null,i.analysis=null,Cn(),Jt(),Be(),s?await ft(n,{successToast:t||!1,loadingMode:"priority"}):t&&$(t)}function _r(){ce("scope")}function Ur(e={}){return i.analysis||!i.organizationProfile?null:ft(!0,{loadingMode:e.loadingMode||"priority",successToast:e.successToast||!1})}function Wn(){if(!i.analysis)return;i.analysisStale=!0,i.lastAiExecutiveReport&&(i.aiReportStale=!0);const e=p("analysisStaleNoticeInline");e&&(e.hidden=!1);const t=p("reportReturnStatus");i.reportReturn&&t&&(t.textContent="진단이 변경되었습니다. 돌아간 뒤 확인 목록을 갱신하세요."),F()}function Gr(){const e=i.reportReturn;i.reportReturn=null;const t=p("reportReturnBar");t&&(t.hidden=!0),ce("report",{replace:!0});const s=p("analyzeContent");s&&(s.style.display="");const n=p("analysisReportPanel");n&&(n.style.display=""),i.analysis&&oe(i.analysis),window.requestAnimationFrame(()=>{const a=p("reportReviewQueue"),r=[...a?.querySelectorAll("[data-review-item-id]")||[]].find(l=>l.dataset.reviewItemId===e?.itemId);if(r){const l=r.querySelector("[data-review-related-toggle]"),d=r.querySelector("[data-review-related-panel]");l&&d&&(d.hidden=!1,l.setAttribute("aria-expanded","true"),l.textContent="관련 통제 접기"),e?.controlId&&r.querySelector(`[data-review-open-control="${CSS.escape(e.controlId)}"]`)?.classList.add("is-return-focus")}(r||a||n)?.scrollIntoView({behavior:"smooth",block:"center"}),r&&(r.setAttribute("tabindex","-1"),r.focus({preventScroll:!0}))})}function xs(e){const t=Le[e]?e:"assess",s=p("pageKicker"),n=p("pageTitle"),a=p("heroLede");s&&(s.textContent=os[t]||os.assess),n&&(n.textContent=Le[t]||Le.assess),a&&(a.textContent=rs[t]||rs.assess),p("workspaceContextTitle")&&(p("workspaceContextTitle").textContent=Le[t]||Le.assess),p("workspaceContextDetail")&&(p("workspaceContextDetail").textContent=t==="assess"?"진단 환경 설정":"통제 진단 현황")}function ut(e="assessment"){const t=p("view-analyze");if(!t)return;const s=["assessment","results","evidence","report"],n=s.includes(e)?e:"assessment";n==="report"&&Hr(),s.forEach(f=>t.classList.toggle(`is-${f}`,f===n));const a={assessment:["진단","자가진단","통제별 판단 기준을 확인하고 진단 결과를 저장하세요."],results:["진단","진단 결과","확인된 미흡과 연계 리스크, 보완 우선순위를 확인하세요."],evidence:["관리","증적 관리","통제별 증적 등록 상태를 확인하고 부족한 근거를 보완하세요."],report:["관리","보고서","진단 초안을 검토한 뒤 본문을 수정하고 내보내세요."]},[r,o,l]=a[n];p("pageKicker")&&(p("pageKicker").textContent=r),p("pageTitle")&&(p("pageTitle").textContent=o),p("heroLede")&&(p("heroLede").textContent=l),p("workspaceContextTitle")&&(p("workspaceContextTitle").textContent=o);const d={assessment:"통제별 진단 및 판단",results:"보완 우선순위와 진단 결과",evidence:"통제별 증적 등록 현황",report:"진단 결과 보고서"};p("workspaceContextDetail")&&(p("workspaceContextDetail").textContent=d[n]),n==="assessment"||n==="evidence"?ue("actions"):n==="results"&&ue("overview"),n==="report"&&(Fe(),F());const u=p("workspaceLoadingSkeleton");u&&u.setAttribute("aria-label",n==="report"?"보고서를 불러오는 중":"진단 항목을 불러오는 중"),window.scrollTo({top:0,behavior:"auto"})}function pt(){const e=un(),t=pn(),s=p("pageHeadStatus");if(!s)return;const n=i.currentView==="analyze"&&!!i.organizationProfile;if(s.hidden=!n,!n)return;const a=t>0&&e>=t,r=En().length,o=(i.checklist||[]).filter(m=>x(m.id)==="partial").length,l=Ln({done:r,partial:o,applicable:t}),d=Yt(l);s.classList.toggle("is-complete",a),s.classList.toggle("is-temperature",!0),s.classList.remove("is-cold","is-warming","is-rising","is-ready"),s.classList.add(`is-${d.key}`);const u=p("pageHeadStatusLabel"),f=p("pageHeadStatusMeta");u&&(u.textContent=`${l}°`),f&&(f.textContent=d.label)}function pe(e,t={}){if(!t.skipProfileGate&&(e==="assess"||e==="analyze")&&!i.organizationProfile){i.currentView="assess",document.querySelectorAll(".view-panel").forEach(s=>{const n=s.id==="view-assess";s.classList.toggle("active",n),s.hidden=!n}),xs("assess"),Pt(),$("먼저 점검 범위를 적용하세요.");return}if(i.currentView=e,document.querySelectorAll(".view-panel").forEach(s=>{const n=s.id===`view-${e}`;s.classList.toggle("active",n),s.hidden=!n}),xs(e),e==="assess"&&i.organizationProfile&&Pt({focus:!1}),e==="analyze"){const s=p("view-analyze"),n=["assessment","results","evidence","report"].find(a=>s?.classList.contains(`is-${a}`));if(ut(n||"assessment"),ue(i.analyzeSection||"actions"),i.analysis){as(!0);const a=p("analyzeContent"),r=p("analysisReportPanel");a&&(a.style.display=""),r&&(r.style.display="")}else t.skipAutoAnalyze||Ur()}pt()}function Vn(e){Mn(e,{diagnoseControl:yi,markAnalysisStale:Wn})}function Wr(){return xr({domainChecksPayload:hn,renderAnalyzeView:as})}function ft(e,t={}){return Er(e,{loadingMode:"priority",...t},{showProfileWizard:_r,switchView:pe,domainChecksPayload:hn,renderProfileContext:Jt,renderStats:pt,syncAssessmentsFromApplicability:si,renderAnalyzeView:as})}function as(e){Mr(e,{renderConfirmationActions:Vn})}function fe(){Gn({onOpen:is,onCreate:Zr,onDuplicate:Xr,onRename:eo,onExport:so,onImport:no,onDelete:ao})}function Vr(){ce("sessions")}function Kr(e){document.title="ONDO°"}function Jr(e){document.querySelectorAll(".sidebar-nav a[data-route]").forEach(t=>{const s=t.dataset.route===e;t.classList.toggle("is-active",s),s?t.setAttribute("aria-current","page"):t.removeAttribute("aria-current")})}function Yr(e,{replace:t=!1,skipHistory:s=!1}={}){const n=G[e]||G.sessions;if(s)return;const a=ct(window.location.pathname);if(a?.id===n.id&&!t)return;const r=t||!a?"replaceState":"pushState";window.history[r]({routeId:n.id},"",n.path)}function Qr(){const e=ct(window.location.pathname);return e&&e.id!=="sessions"?e.id:i.organizationProfile?"assessment":"scope"}function _e(e,t={}){const s=G[e]||G.sessions;if(Yr(s.id,t),Kr(s.id),Jr(s.id),s.id==="sessions"){le=null,_n(),fe(),ot(),window.scrollTo({top:0,behavior:"auto"});return}if(!i.activeSessionId){le=s.id,fe(),ot(),window.scrollTo({top:0,behavior:"auto"});return}if(le=null,ns(),s.id==="scope"){pe("assess",{skipProfileGate:!0}),Pt(),window.scrollTo({top:0,behavior:"auto"});return}if(!i.organizationProfile){$("먼저 점검 범위를 적용하세요."),_e("scope",{replace:!0});return}ut(s.workspace||"assessment"),pe("analyze")}async function is(e){if(kt)return;if(_n(),!Ut(e)){$("선택한 진단을 찾을 수 없습니다."),fe();return}kt=!0;const s=p("workspaceLoadingSkeleton");try{ns(),Be(),Cn();const n=le&&le!=="sessions"?le:Qr();if(i.organizationProfile&&n!=="scope"){const a=G[n]||G.assessment;ut(a.workspace||"assessment"),pe("analyze",{skipAutoAnalyze:!0}),!et&&s&&(s.hidden=!1,p("view-analyze")?.classList.add("is-workspace-loading"),p("view-analyze")?.setAttribute("aria-busy","true"))}if(!et){const[a,r]=await Promise.all([ke("/controls/dashboard"),ke("/controls/checklist?compact=true")]);i.dashboard=a,i.allControls=r.controls,await hi(r),et=!0}Jt(),pt(),_e(n,{replace:!0}),window.scrollTo({top:0,behavior:"auto"})}catch(n){Vr(),$(`진단을 불러오지 못했습니다: ${n.message}`)}finally{s?.dataset.analysisLoading!=="true"&&(s.hidden=!0,p("view-analyze")?.classList.remove("is-workspace-loading"),p("view-analyze")?.removeAttribute("aria-busy")),kt=!1}}function Zr(){const e=$a();is(e.id)}function Xr(e){Sa(e)&&(Un(),fe())}function eo(e,t){const s=i.diagnosisSessions.find(a=>a.id===e);if(!s)return!1;const n=ka(e,t);return n?(fe(),n.name!==s.name&&$(`진단 이름을 “${n.name}”(으)로 바꿨습니다.`),!0):!1}function to(e){return`${String(e||"진단").replace(/[\\/:*?"<>|]/g,"-").replace(/\s+/g," ").trim().slice(0,60)||"진단"}-백업.json`}function so(e){try{const t=Ca(e),s=new Blob([JSON.stringify(t,null,2)],{type:"application/json"}),n=URL.createObjectURL(s),a=document.createElement("a");a.href=n,a.download=to(t.session.name),document.body.appendChild(a),a.click(),a.remove(),URL.revokeObjectURL(n),$("진단 백업을 저장했습니다. 다른 브라우저에서 ‘백업 가져오기’를 사용하세요.")}catch(t){$(`백업을 만들지 못했습니다: ${t.message}`)}}async function no(e){if(e.size>5*1024*1024){$("백업 파일은 5MB 이하만 가져올 수 있습니다.");return}try{const t=Aa(await e.text());if(!await Ft({title:`“${t.name}” 진단을 가져올까요?`,message:`점검 ${t.progress.reviewed}/${t.progress.applicable}개가 포함되어 있습니다. 기존 진단은 유지되고 새 진단으로 추가됩니다.`,confirmLabel:"새 진단으로 가져오기"}))return;const n=Ea(t);Un(),fe(),$(`${n.name}을(를) 가져왔습니다.`)}catch(t){$(`백업을 가져오지 못했습니다: ${t.message}`)}}async function ao(e){const t=i.diagnosisSessions.find(n=>n.id===e);!t||!await Ft({title:`${t.name} 진단을 삭제할까요?`,message:"진단 상태와 증적 정보가 함께 삭제되며 되돌릴 수 없습니다.",confirmLabel:"진단 삭제",tone:"danger"})||(xa(e),fe(),$("진단을 삭제했습니다."))}function io(){Qi(),Xi(),document.addEventListener("click",e=>{const t=e.target.closest("a[data-route]");t&&(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||e.button!==0||(e.preventDefault(),ce(t.dataset.route)))}),document.addEventListener("click",e=>{e.target.closest("[data-run-analysis]")&&ft(!0,{loadingMode:"priority",successToast:"확인 목록을 갱신했습니다."})}),document.querySelectorAll("[data-write-ai-report]").forEach(e=>{e.addEventListener("click",async()=>{!await Vs()||p("executiveReportStream")?.dataset.userEdited==="1"&&!await Ft({title:"AI 초안으로 바꿀까요?",message:"직접 고친 본문이 AI 초안으로 대체됩니다.",confirmLabel:"다시 작성",cancelLabel:"편집 유지"})||Wr()})}),p("profileForm").addEventListener("submit",async e=>{if(e.preventDefault(),!it()){$("클라우드 또는 자체 인프라를 하나 이상 선택하세요."),p("profileCloud")?.focus();return}const t=p("applyProfileBtn");t&&(t.disabled=!0);try{await zr(dt(),{runAnalyzeAfter:!0,switchToAnalyze:!0}),ce("assessment",{replace:!0})}catch(s){$("환경 적용 실패: "+s.message)}finally{t&&(t.disabled=!it())}}),["profileCloud","profileOnPrem"].forEach(e=>{p(e)?.addEventListener("change",kn)}),p("returnToReportBtn")?.addEventListener("click",Gr),or({navigateToControl:$n}),p("exportReportBtn")?.addEventListener("click",ir),p("exportReportDocxBtn")?.addEventListener("click",rr),p("resetReportBtn")?.addEventListener("click",er),window.addEventListener("popstate",()=>{const e=ct(window.location.pathname);_e(e?.id||"sessions",{skipHistory:!0})})}function ro(e){if(!i.activeSessionId||e==="sessions"||!Ut(i.activeSessionId))return ot(),!1;if(le=e,ns(),e==="scope"||!i.organizationProfile)return pe("assess",{skipProfileGate:!0}),!0;const s=G[e]||G.assessment;ut(s.workspace||"assessment"),pe("analyze",{skipAutoAnalyze:!0});const n=p("workspaceLoadingSkeleton");return!et&&n&&(n.hidden=!1,p("view-analyze")?.classList.add("is-workspace-loading"),p("view-analyze")?.setAttribute("aria-busy","true")),!0}async function oo(){li({markAnalysisStale:Wn,renderConfirmationActions:Vn,renderStats:pt,runAnalysis:ft,switchView:pe,switchAnalyzeSection:ue}),Xa(_e),wa(),sa(),io();const t=ct(window.location.pathname)?.id||"sessions",s=ro(t);if(await ta(),s&&i.activeSessionId){await is(i.activeSessionId);return}_e(t,{replace:!0})}const Kn="ondo.narrowWorkspaceContinue",At="is-narrow-workspace-ok",lo="(max-width: 860px), (max-height: 520px) and (pointer: coarse)";function co(){try{return sessionStorage.getItem(Kn)==="1"}catch{return!1}}function uo(){try{sessionStorage.setItem(Kn,"1")}catch{}}function po(e){const t=document.getElementById("desktopWorkspaceGate");Array.from(document.body.children).forEach(s=>{s!==t&&(e?s.setAttribute("inert",""):s.removeAttribute("inert"))})}async function fo(e){if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(e);return}const t=document.createElement("textarea");t.value=e,t.setAttribute("readonly",""),t.style.position="fixed",t.style.left="-9999px",document.body.appendChild(t),t.select(),document.execCommand("copy"),t.remove()}function go(){const e=document.getElementById("desktopWorkspaceGate");if(!e)return;const t=window.matchMedia(lo),s=document.getElementById("desktopWorkspaceGateUrl"),n=document.getElementById("desktopWorkspaceGateCopy"),a=document.getElementById("desktopWorkspaceGateContinue"),r=document.getElementById("desktopWorkspaceGateTitle");function o(){co()&&document.documentElement.classList.add(At);const l=t.matches&&!document.documentElement.classList.contains(At);e.setAttribute("aria-hidden",l?"false":"true"),s&&(s.textContent=window.location.href),po(l),l&&r&&document.activeElement===document.body&&r.focus()}n?.addEventListener("click",async()=>{const l=window.location.href;try{await fo(l);const d=n.textContent;n.textContent="복사됨",window.setTimeout(()=>{n.textContent=d},1600)}catch{n.textContent="아래 주소를 길게 누르세요"}}),a?.addEventListener("click",()=>{uo(),document.documentElement.classList.add(At),o()}),typeof t.addEventListener=="function"?t.addEventListener("change",o):typeof t.addListener=="function"&&t.addListener(o),window.addEventListener("popstate",o),o()}function Ls(){go(),oo()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Ls):Ls();
