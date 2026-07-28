import { FormEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { AdminApp } from "./AdminApp";
import { ADMIN_PATH, isAdminPath } from "./routes";
import { ApiFailure, ChatResult, Conversation, ConversationMessage, Health, LocalIdentity, OpticHealthQuery, PresentationModule, Session, platformApi } from "./api";
import "./styles.css";

const HEALTH_LABELS: Record<Health, string> = { healthy: "正常", critical: "严重", warning: "告警", recovered: "已恢复", unknown: "数据缺失" };
const PARTICLE_QUESTION = "哪些光模块需要关注？";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [identity, setIdentity] = useState<LocalIdentity | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [savedMessages, setSavedMessages] = useState<ConversationMessage[]>([]);
  const [opticHealth, setOpticHealth] = useState<OpticHealthQuery | null>(null);
  const [question, setQuestion] = useState("查看当前光模块健康异常");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [workMode, setWorkMode] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [welcomeStage, setWelcomeStage] = useState<"portrait" | "questions">("portrait");
  const [bootstrapRequired, setBootstrapRequired] = useState(false);
  const [frontAuthRequired, setFrontAuthRequired] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [conversationMenuId, setConversationMenuId] = useState<string | null>(null);
  const [conversationPendingDeletion, setConversationPendingDeletion] = useState<Conversation | null>(null);
  const [deletingConversation, setDeletingConversation] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const historyMenuRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => void Promise.all([platformApi.session(), platformApi.opticHealth(), platformApi.capabilities()])
    .then(async ([nextSession, result]) => {
      setSession(nextSession); setOpticHealth(result.query);
      if (nextSession.identity.authenticated) {
        setFrontAuthRequired(false); setBootstrapRequired(false); void refreshHistory();
      } else {
        setFrontAuthRequired(true);
        setBootstrapRequired((await platformApi.adminBootstrapStatus()).bootstrap_required);
      }
    })
    .catch(async (reason) => {
      if (reason instanceof ApiFailure && reason.status === 401) {
        try {
          setFrontAuthRequired(true);
          setBootstrapRequired((await platformApi.adminBootstrapStatus()).bootstrap_required);
          setError(null);
          return;
        } catch (fallbackError) { showError(fallbackError); return; }
      }
      showError(reason);
    }).finally(() => setLoading(false));
  useEffect(refresh, []);
  useEffect(() => {
    const timer = window.setTimeout(() => setWelcomeStage(welcomeStage === "portrait" ? "questions" : "portrait"), 8000);
    return () => window.clearTimeout(timer);
  }, [welcomeStage]);
  useEffect(() => {
    if (!accountMenuOpen && !conversationMenuId) return;
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (accountMenuRef.current?.contains(target) || historyMenuRef.current?.contains(target)) return;
      setAccountMenuOpen(false); setConversationMenuId(null);
    };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { setAccountMenuOpen(false); setConversationMenuId(null); } };
    window.addEventListener("mousedown", close); window.addEventListener("keydown", escape);
    return () => { window.removeEventListener("mousedown", close); window.removeEventListener("keydown", escape); };
  }, [accountMenuOpen, conversationMenuId]);
  useEffect(() => {
    if (!conversationPendingDeletion || deletingConversation) return;
    const dismiss = (event: KeyboardEvent) => { if (event.key === "Escape") setConversationPendingDeletion(null); };
    window.addEventListener("keydown", dismiss);
    return () => window.removeEventListener("keydown", dismiss);
  }, [conversationPendingDeletion, deletingConversation]);

  function showError(reason: unknown) { setError(reason instanceof ApiFailure ? reason.code : "api_unavailable"); }
  function refreshHistory() { void platformApi.conversations().then((value) => setConversations(value.conversations)).catch(showError); }

  function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const username = String(data.get("username") || ""); const password = String(data.get("password") || "");
    setError(null);
    void platformApi.login(username, password).then((result) => { setIdentity(result.identity); refresh(); }).catch(showError);
  }
  function bootstrapProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const password = String(data.get("password") || "");
    if (password !== String(data.get("confirmation") || "")) { setError("local_password_confirmation_mismatch"); return; }
    setError(null);
    void platformApi.bootstrapAdmin(String(data.get("username") || ""), password, String(data.get("displayName") || ""))
      .then((result) => { setIdentity(result.identity); refresh(); }).catch(showError);
  }

  function ask(nextQuestion: string) {
    if (!nextQuestion.trim()) return;
    setError(null);
    void platformApi.chat(nextQuestion, conversationId).then((result) => {
      setChat(result); setSavedMessages([]); setOpticHealth(result.optic_health); setWorkMode(result.presentation.mode === "work"); setConversationId(result.conversation_id); setQuestion("");
      if (result.conversation_id) refreshHistory();
    }).catch(showError);
  }

  function submitChat(event: FormEvent<HTMLFormElement>) { event.preventDefault(); ask(question); }

  function signOut() { void platformApi.logout().then(() => { setIdentity(null); setConversations([]); setConversationId(undefined); setChat(null); setSavedMessages([]); refresh(); }).catch(showError); }
  function newChat() { setConversationId(undefined); setChat(null); setSavedMessages([]); setQuestion(""); setWorkMode(false); }
  function openConversation(nextConversationId: string) {
    setError(null);
    void platformApi.conversation(nextConversationId).then(({ conversation }) => {
      setConversationId(conversation.conversation_id); setChat(null); setSavedMessages(conversation.messages); setQuestion(""); setWorkMode(false);
    }).catch(showError);
  }
  function requestConversationDeletion(item: Conversation) {
    setConversationMenuId(null); setConversationPendingDeletion(item);
  }
  function deleteConversation() {
    const target = conversationPendingDeletion;
    if (!target || deletingConversation) return;
    setDeletingConversation(true); setError(null);
    void platformApi.deleteConversation(target.conversation_id).then(() => {
      setConversations((current) => current.filter((item) => item.conversation_id !== target.conversation_id));
      if (conversationId === target.conversation_id) newChat();
      setConversationPendingDeletion(null);
    }).catch(showError).finally(() => setDeletingConversation(false));
  }

  if (loading) return <main className="loading">正在准备受限 Fixture 工作台…</main>;
  if (frontAuthRequired && !identity) return <LoginForm bootstrapRequired={bootstrapRequired} error={error} onBootstrap={bootstrapProject} onSubmit={authenticate} />;
  if (!session) return <main className="loading" role="alert">服务不可用：{error ?? "unknown"}</main>;

  const compactRail = workMode || railCollapsed;
  return <main className={["shell", workMode && "work", railCollapsed ? "rail-collapsed" : "rail-expanded", compactRail && "rail-compact"].filter(Boolean).join(" ")}>
    <aside className="rail">
      <div className="rail-top"><div className="brand"><span>◉</span><span className="rail-copy">AskLily</span></div><button className="rail-toggle" type="button" aria-label={compactRail ? "展开工具栏" : "收起工具栏"} aria-pressed={compactRail} onClick={() => setRailCollapsed((value) => !value)}>{compactRail ? "›" : "‹"}</button></div>
      <button className="new" onClick={newChat}><span aria-hidden="true">+</span><span className="new-label rail-copy">新建对话</span></button>
      <p className="rail-title">最近对话</p>
      <div className="history">{conversations.length ? conversations.map((item) => <div className="history-entry" key={item.conversation_id} ref={conversationMenuId === item.conversation_id ? historyMenuRef : null}><button className={conversationId === item.conversation_id ? "history-item active" : "history-item"} onClick={() => openConversation(item.conversation_id)} onContextMenu={(event) => { event.preventDefault(); setAccountMenuOpen(false); setConversationMenuId(item.conversation_id); }}><span className="history-icon" aria-hidden="true">◫</span><span className="history-title rail-copy">{item.title}</span><small className="history-time rail-copy">{new Date(item.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></button>{conversationMenuId === item.conversation_id && <div className="history-menu" role="menu" aria-label="对话操作"><button role="menuitem" onClick={() => requestConversationDeletion(item)}>删除对话</button></div>}</div>) : <p className="muted rail-copy">暂无已保存对话</p>}</div>
      <div className="account" ref={accountMenuRef}><button className="account-menu-trigger" type="button" aria-haspopup="menu" aria-expanded={accountMenuOpen} onClick={() => setAccountMenuOpen((open) => !open)} onContextMenu={(event) => { event.preventDefault(); setAccountMenuOpen(true); }}><span className="avatar">{(identity?.display_name ?? session.identity.display_name).slice(0, 1).toUpperCase()}</span><span className="account-details rail-copy">{identity?.display_name ?? session.identity.display_name}<small>{session.identity.role} · 本地账号</small></span></button>{accountMenuOpen && <div className="account-menu" role="menu">{session.identity.role === "project-admin" && ADMIN_PATH && <button role="menuitem" onClick={() => { if (ADMIN_PATH) window.location.assign(ADMIN_PATH); }}>管理后台</button>}<button role="menuitem" onClick={() => { setAccountMenuOpen(false); signOut(); }}>退出</button></div>}</div>
    </aside>
    <section className={!chat && !savedMessages.length ? "conversation idle" : "conversation"}>
      <header><span className="eyebrow">ASKLILY · {session.runtime.declared_environment.toUpperCase()} · {session.runtime.data_sources.map((item) => `${item.kind} ${item.data_level}`).join(" / ") || "SOURCE NOT CONFIGURED"}</span></header>
      {error && <p className="error" role="alert">请求未完成：{error}</p>}
      {!chat && !savedMessages.length ? <Welcome stage={welcomeStage} onAsk={ask} /> : chat ? <article className="answer"><p className="bubble">{chat.question_acknowledged}</p><p>{chat.message}</p><p className="meta">来源：{chat.sources.join("、")} · 限制：{chat.limitations.join("、")}</p></article> : <SavedConversation messages={savedMessages} />}
      <form className="composer" onSubmit={submitChat}><textarea aria-label="向 AskLily 提问" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="向 AskLily 提问…"/><button type="submit">↑</button></form>
    </section>
    {opticHealth && <section className="workbench" aria-label="Work Mode" aria-hidden={!workMode}><header><span>工作台 / Work Mode</span><span className="badge">严格只读 · Fixture</span></header><WorkspaceModules modules={chat?.presentation.modules ?? [{ module_id: "optic-health-overview", view_id: "optic_health" }]} query={opticHealth} /></section>}
    {conversationPendingDeletion && <div className="confirm-backdrop" role="presentation"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-conversation-title"><p className="eyebrow">对话操作</p><h2 id="delete-conversation-title">删除这段对话？</h2><p>“{conversationPendingDeletion.title}”及其消息将从当前账号的本地记录中移除，且无法恢复。</p><div className="confirm-actions"><button type="button" disabled={deletingConversation} onClick={() => setConversationPendingDeletion(null)}>取消</button><button className="danger" type="button" disabled={deletingConversation} onClick={deleteConversation}>{deletingConversation ? "正在删除…" : "确认删除"}</button></div></section></div>}
  </main>;
}

function LoginForm({ bootstrapRequired, error, onBootstrap, onSubmit }: { bootstrapRequired: boolean; error: string | null; onBootstrap: (event: FormEvent<HTMLFormElement>) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <main className="login"><section><p className="orb">✦</p><h1>{bootstrapRequired ? "初始化 AskLily" : "AskLily"}</h1><p>{bootstrapRequired ? "请在本机设置首位项目管理员。创建成功后，所有账号均从此处登录。" : "本地账号由项目管理员在后台分配；不提供自助注册。"}</p>{error && <p className="error">{error}</p>}{bootstrapRequired ? <form onSubmit={onBootstrap}><label>管理员账号<input required name="username" minLength={3} /></label><label>显示名称（可留空）<input name="displayName" /></label><label>管理员密码<input required name="password" type="password" minLength={12} /></label><label>确认密码<input required name="confirmation" type="password" minLength={12} /></label><div><button>创建项目管理员</button></div></form> : <form onSubmit={onSubmit}><label>账号<input required name="username" minLength={3} /></label><label>密码<input required name="password" type="password" minLength={12} /></label><div><button>登录</button></div></form>}</section></main>; }

function Welcome({ stage, onAsk }: { stage: "portrait" | "questions"; onAsk: (question: string) => void }) {
  return <div className={`welcome ${stage}`}>
    <ParticleCanvas stage={stage} question={PARTICLE_QUESTION} />
    {stage === "questions" && <button className="particle-question-action" onClick={() => onAsk("查看当前光模块健康异常")}>{PARTICLE_QUESTION}</button>}
    <p className="sr-only">{stage === "portrait" ? "AskLily 待机视觉" : `系统建议关注：${PARTICLE_QUESTION}`}</p>
    <p className="reduced-motion-message">AskLily 待机中 · 系统建议关注：{PARTICLE_QUESTION}</p>
  </div>;
}

type Particle = { x: number; y: number; targetX: number; targetY: number; phase: number; radius: number };

function ParticleCanvas({ stage, question }: { stage: "portrait" | "questions"; question: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef(stage);
  stageRef.current = stage;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let width = 0;
    let height = 0;
    let currentStage = stageRef.current;
    let particles: Particle[] = [];

    const updateTargets = () => {
      const targets = currentStage === "portrait" ? portraitTargets(width, height) : textTargets(width, height, question);
      particles.forEach((particle, index) => {
        const target = targets[Math.floor(index * targets.length / particles.length)];
        particle.targetX = target.x;
        particle.targetY = target.y;
      });
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      canvas.width = Math.floor(width * pixelRatio);
      canvas.height = Math.floor(height * pixelRatio);
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      const targets = currentStage === "portrait" ? portraitTargets(width, height) : textTargets(width, height, question);
      const particleCount = Math.min(2600, Math.max(1000, Math.floor(width * height / 250)));
      particles = Array.from({ length: particleCount }, (_, index) => {
        const target = targets[Math.floor(index * targets.length / particleCount)];
        const startX = width * (.12 + seeded(index, 1) * .76);
        const startY = height * (.08 + seeded(index, 2) * .8);
        return { x: reducedMotion ? target.x : startX, y: reducedMotion ? target.y : startY, targetX: target.x, targetY: target.y, phase: seeded(index, 3) * Math.PI * 2, radius: .7 + seeded(index, 4) * 1.5 };
      });
    };

    const draw = (time: number) => {
      if (stageRef.current !== currentStage) { currentStage = stageRef.current; updateTargets(); }
      const background = context.createRadialGradient(width * .32, height * .35, 0, width * .55, height * .55, Math.max(width, height));
      background.addColorStop(0, "#6671d4");
      background.addColorStop(.48, "#263b87");
      background.addColorStop(1, "#0d1c58");
      context.fillStyle = background;
      context.fillRect(0, 0, width, height);
      context.globalCompositeOperation = "screen";
      for (let index = 0; index < 150; index += 1) {
        const drift = reducedMotion ? 0 : Math.sin(time * .00035 + index) * 8;
        context.fillStyle = `rgba(204, 192, 255, ${.12 + seeded(index, 14) * .22})`;
        context.beginPath(); context.arc(width * seeded(index, 15) + drift, height * seeded(index, 16), .45 + seeded(index, 17) * 1.4, 0, Math.PI * 2); context.fill();
      }
      particles.forEach((particle) => {
        if (!reducedMotion) {
          particle.x += (particle.targetX - particle.x) * .073;
          particle.y += (particle.targetY - particle.y) * .073;
        }
        const isQuestion = currentStage === "questions";
        const shimmer = isQuestion ? .82 + Math.sin(time * .002 + particle.phase) * .16 : .62 + Math.sin(time * .002 + particle.phase) * .28;
        context.fillStyle = `rgba(236, 225, 255, ${shimmer})`;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.radius + (isQuestion ? .35 : 0), 0, Math.PI * 2);
        context.fill();
      });
      context.globalCompositeOperation = "source-over";
      if (!reducedMotion) frame = window.requestAnimationFrame(draw);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    frame = window.requestAnimationFrame(draw);
    return () => { observer.disconnect(); window.cancelAnimationFrame(frame); };
  }, [question]);

  return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />;
}

function portraitTargets(width: number, height: number) {
  const source = document.createElement("canvas");
  source.width = Math.max(1, Math.floor(width)); source.height = Math.max(1, Math.floor(height));
  const context = source.getContext("2d")!;
  context.strokeStyle = "#ffffff"; context.fillStyle = "#ffffff"; context.lineCap = "round"; context.lineJoin = "round";
  context.lineWidth = Math.max(1.1, width / 880);
  const centerX = width * .55; const top = height * .105;

  // A softly filled head-and-shoulders silhouette gives the particles a legible
  // human form, while the fine strokes below preserve the airy particle look.
  context.globalAlpha = .22;
  context.beginPath();
  context.moveTo(centerX + width * .055, top + height * .01);
  context.bezierCurveTo(centerX - width * .075, top - height * .025, centerX - width * .17, top + height * .08, centerX - width * .13, top + height * .22);
  context.bezierCurveTo(centerX - width * .145, top + height * .27, centerX - width * .16, top + height * .31, centerX - width * .19, top + height * .35);
  context.bezierCurveTo(centerX - width * .155, top + height * .37, centerX - width * .172, top + height * .395, centerX - width * .192, top + height * .42);
  context.bezierCurveTo(centerX - width * .16, top + height * .432, centerX - width * .178, top + height * .46, centerX - width * .16, top + height * .49);
  context.bezierCurveTo(centerX - width * .13, top + height * .53, centerX - width * .09, top + height * .555, centerX - width * .055, top + height * .575);
  context.bezierCurveTo(centerX - width * .04, top + height * .655, centerX - width * .13, top + height * .72, centerX - width * .205, top + height * .84);
  context.bezierCurveTo(centerX - width * .075, top + height * .815, centerX + width * .035, top + height * .75, centerX + width * .13, top + height * .92);
  context.bezierCurveTo(centerX + width * .19, top + height * .72, centerX + width * .13, top + height * .57, centerX + width * .09, top + height * .45);
  context.bezierCurveTo(centerX + width * .12, top + height * .24, centerX + width * .12, top + height * .08, centerX + width * .055, top + height * .01);
  context.closePath(); context.fill();

  context.globalAlpha = 1;
  // Profile contour: crown, forehead, nose, lips, chin, throat and shoulder.
  context.beginPath();
  context.moveTo(centerX + width * .052, top + height * .012);
  context.bezierCurveTo(centerX - width * .07, top - height * .02, centerX - width * .15, top + height * .09, centerX - width * .125, top + height * .22);
  context.bezierCurveTo(centerX - width * .14, top + height * .275, centerX - width * .16, top + height * .315, centerX - width * .19, top + height * .35);
  context.bezierCurveTo(centerX - width * .15, top + height * .37, centerX - width * .176, top + height * .4, centerX - width * .192, top + height * .423);
  context.bezierCurveTo(centerX - width * .155, top + height * .432, centerX - width * .176, top + height * .462, centerX - width * .158, top + height * .49);
  context.bezierCurveTo(centerX - width * .122, top + height * .535, centerX - width * .08, top + height * .558, centerX - width * .055, top + height * .575);
  context.bezierCurveTo(centerX - width * .04, top + height * .66, centerX - width * .125, top + height * .73, centerX - width * .205, top + height * .84);
  context.bezierCurveTo(centerX - width * .07, top + height * .81, centerX + width * .04, top + height * .75, centerX + width * .13, top + height * .92);
  context.stroke();

  // Facial landmarks make the profile recognizable without becoming photorealistic.
  context.lineWidth *= .82;
  context.beginPath(); context.moveTo(centerX - width * .135, top + height * .277); context.quadraticCurveTo(centerX - width * .103, top + height * .258, centerX - width * .075, top + height * .279); context.stroke();
  context.beginPath(); context.moveTo(centerX - width * .128, top + height * .305); context.quadraticCurveTo(centerX - width * .104, top + height * .322, centerX - width * .082, top + height * .304); context.stroke();
  context.beginPath(); context.moveTo(centerX - width * .16, top + height * .378); context.quadraticCurveTo(centerX - width * .122, top + height * .39, centerX - width * .148, top + height * .407); context.stroke();
  context.beginPath(); context.moveTo(centerX - width * .064, top + height * .36); context.quadraticCurveTo(centerX - width * .035, top + height * .392, centerX - width * .055, top + height * .435); context.stroke();
  context.beginPath(); context.ellipse(centerX - width * .028, top + height * .39, width * .024, height * .036, .15, 0, Math.PI * 2); context.stroke();
  context.beginPath(); context.moveTo(centerX - width * .052, top + height * .575); context.quadraticCurveTo(centerX + width * .025, top + height * .625, centerX + width * .005, top + height * .715); context.stroke();

  // Hair is deliberately directional: it makes the silhouette read as a woman
  // and connects the portrait to the surrounding flowing particle field.
  context.lineWidth = Math.max(.8, width / 1200);
  for (let index = 0; index < 34; index += 1) {
    const startY = top + height * (.03 + index * .016);
    const lift = seeded(index, 18) * height * .18 - height * .05;
    const endX = centerX + width * (.12 + seeded(index, 19) * .33);
    const endY = top + height * (.17 + seeded(index, 20) * .66);
    context.globalAlpha = .48 + seeded(index, 21) * .42;
    context.beginPath();
    context.moveTo(centerX + width * (.02 + seeded(index, 22) * .055), startY);
    context.bezierCurveTo(centerX + width * (.08 + seeded(index, 23) * .12), startY + lift, endX - width * .07, endY - height * .06, endX, endY);
    context.stroke();
  }
  context.globalAlpha = 1;
  context.beginPath(); context.moveTo(centerX + width * .04, top + height * .015); context.bezierCurveTo(centerX + width * .16, top + height * .18, centerX + width * .14, top + height * .43, centerX + width * .26, top + height * .7); context.stroke();
  return sampleTargets(context, source.width, source.height, 4);
}

function textTargets(width: number, height: number, question: string) {
  const source = document.createElement("canvas");
  source.width = Math.max(1, Math.floor(width)); source.height = Math.max(1, Math.floor(height));
  const context = source.getContext("2d")!;
  const fontSize = Math.max(28, Math.min(width / Math.max(question.length * 1.12, 8), 62));
  context.font = `700 ${fontSize}px system-ui, sans-serif`; context.textAlign = "center"; context.textBaseline = "middle"; context.fillStyle = "#ffffff";
  context.fillText(question, width / 2, height * .5);
  return sampleTargets(context, source.width, source.height, 2);
}

function sampleTargets(context: CanvasRenderingContext2D, width: number, height: number, step: number) {
  const pixels = context.getImageData(0, 0, width, height).data;
  const targets: { x: number; y: number }[] = [];
  for (let y = 0; y < height; y += step) for (let x = 0; x < width; x += step) if (pixels[(y * width + x) * 4 + 3] > 40) targets.push({ x, y });
  return targets.length ? targets : [{ x: width / 2, y: height / 2 }];
}

function seeded(index: number, salt: number) { const value = Math.sin(index * 9283.47 + salt * 497.11) * 10000; return value - Math.floor(value); }

function OpticModule({ query }: { query: OpticHealthQuery }) { return <article className="module"><h2>光模块健康概览</h2><p className="meta">{query.source} · 规则 {query.rule_version}</p><div className="summary">{Object.entries(query.summary).map(([key, value]) => <span key={key}>{HEALTH_LABELS[key as Health]} <b>{value}</b></span>)}</div><table><thead><tr><th>资源</th><th>站点</th><th>健康</th><th>原因</th></tr></thead><tbody>{query.records.map((record) => <tr key={record.resource.resource_id}><td>{record.resource.display_name}</td><td>{record.resource.site_id}</td><td>{HEALTH_LABELS[record.assessment.health]}</td><td>{record.assessment.reason_codes.join("、") || "-"}</td></tr>)}</tbody></table></article>; }

function WorkspaceModules({ modules, query }: { modules: PresentationModule[]; query: OpticHealthQuery }) { return <>{modules.map((module) => module.module_id === "optic-health-overview" && module.view_id === "optic_health" ? <OpticModule key={module.module_id} query={query} /> : <article className="module" key={module.module_id}><h2>未注册展示模块</h2><p className="meta">{module.module_id}</p></article>)}</>; }

function SavedConversation({ messages }: { messages: ConversationMessage[] }) { return <article className="answer saved-conversation">{messages.map((message, index) => <section key={`${message.created_at}-${index}`}><p className={message.author === "user" ? "bubble" : ""}>{message.body}</p>{message.author === "assistant" && <p className="meta">来源：{message.source_label ?? "-"} · 限制：{message.limitation_label ?? "-"}</p>}</section>)}</article>; }

createRoot(document.getElementById("root")!).render(isAdminPath(window.location.pathname) ? <AdminApp /> : <App />);
