import { FormEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => void Promise.all([platformApi.session(), platformApi.opticHealth(), platformApi.capabilities()])
    .then(([nextSession, result]) => { setSession(nextSession); setOpticHealth(result.query); if (nextSession.identity.authenticated) void refreshHistory(); })
    .catch(showError).finally(() => setLoading(false));
  useEffect(refresh, []);
  useEffect(() => {
    const timer = window.setTimeout(() => setWelcomeStage(welcomeStage === "portrait" ? "questions" : "portrait"), 8000);
    return () => window.clearTimeout(timer);
  }, [welcomeStage]);

  function showError(reason: unknown) { setError(reason instanceof ApiFailure ? reason.code : "api_unavailable"); }
  function refreshHistory() { void platformApi.conversations().then((value) => setConversations(value.conversations)).catch(showError); }

  function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const username = String(data.get("username") || ""); const password = String(data.get("password") || "");
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const action = submitter?.value === "register" ? "register" : "login"; setError(null);
    const call = action === "register" ? platformApi.register(username, password, String(data.get("displayName") || "")) : platformApi.login(username, password);
    void call.then((result) => { setIdentity(result.identity); refresh(); }).catch(showError);
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

  if (loading) return <main className="loading">正在准备受限 Fixture 工作台…</main>;
  if (!session) return <main className="loading" role="alert">服务不可用：{error ?? "unknown"}</main>;
  if (!session.identity.authenticated && !identity) return <LoginForm error={error} onSubmit={authenticate} />;

  return <main className={["shell", workMode && "work", railCollapsed ? "rail-collapsed" : "rail-expanded"].filter(Boolean).join(" ")}>
    <aside className="rail">
      <div className="rail-top"><div className="brand"><span>◉</span><span className="rail-copy">AskLily</span></div><button className="rail-toggle" type="button" aria-label={railCollapsed ? "展开工具栏" : "收起工具栏"} aria-pressed={railCollapsed} onClick={() => setRailCollapsed((value) => !value)}>{railCollapsed ? "›" : "‹"}</button></div>
      <button className="new" onClick={newChat}><span aria-hidden="true">＋</span><span className="new-label rail-copy">新建对话</span></button>
      <p className="rail-title">最近对话</p>
      <div className="history">{conversations.length ? conversations.map((item) => <button className={conversationId === item.conversation_id ? "history-item active" : "history-item"} key={item.conversation_id} onClick={() => openConversation(item.conversation_id)}><span className="history-icon" aria-hidden="true">◫</span><span className="history-title rail-copy">{item.title}</span><small className="history-time rail-copy">{new Date(item.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></button>) : <p className="muted rail-copy">暂无已保存对话</p>}</div>
      <div className="account"><span className="avatar">{(identity?.display_name ?? session.identity.display_name).slice(0, 1).toUpperCase()}</span><span className="account-details rail-copy">{identity?.display_name ?? session.identity.display_name}<small>{session.identity.role} · 本地账号</small></span><button className="sign-out rail-copy" onClick={signOut}>退出</button></div>
    </aside>
    <section className={!chat && !savedMessages.length ? "conversation idle" : "conversation"}>
      <header><span className="eyebrow">ASKLILY · {session.profile.toUpperCase()} · FIXTURE L0/L1</span>{session.profile === "developer" && <button className="debug" onClick={() => setWorkMode((value) => !value)}>调试：{workMode ? "Chat" : "Work"}</button>}</header>
      {error && <p className="error" role="alert">请求未完成：{error}</p>}
      {!chat && !savedMessages.length ? <Welcome stage={welcomeStage} onAsk={ask} /> : chat ? <article className="answer"><p className="bubble">{chat.question_acknowledged}</p><p>{chat.message}</p><p className="meta">来源：{chat.sources.join("、")} · 限制：{chat.limitations.join("、")}</p></article> : <SavedConversation messages={savedMessages} />}
      <form className="composer" onSubmit={submitChat}><textarea aria-label="向 AskLily 提问" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="向 AskLily 提问…"/><button type="submit">↑</button></form>
    </section>
    {opticHealth && <section className="workbench" aria-label="Work Mode" aria-hidden={!workMode}><header><span>工作台 / Work Mode</span><span className="badge">严格只读 · Fixture</span></header><WorkspaceModules modules={chat?.presentation.modules ?? [{ module_id: "optic-health-overview", view_id: "optic_health" }]} query={opticHealth} /></section>}
  </main>;
}

function LoginForm({ error, onSubmit }: { error: string | null; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <main className="login"><section><p className="orb">✦</p><h1>AskLily</h1><p>本地账号仅保存 Fixture 对话，不连接真实系统。</p>{error && <p className="error">{error}</p>}<form onSubmit={onSubmit}><label>账号<input required name="username" minLength={3} /></label><label>密码<input required name="password" type="password" minLength={12} /></label><label>显示名称（注册时可选）<input name="displayName" /></label><div><button name="action" value="login">登录</button><button name="action" value="register">注册本地账号</button></div></form></section></main>; }

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
  context.strokeStyle = "#ffffff"; context.fillStyle = "#ffffff"; context.lineWidth = Math.max(1.2, width / 720);
  const centerX = width * .57; const top = height * .16;
  context.globalAlpha = .34;
  context.beginPath(); context.ellipse(centerX - width * .055, top + height * .28, width * .09, height * .19, -.18, 0, Math.PI * 2); context.fill();
  context.beginPath(); context.moveTo(centerX - width * .11, top + height * .58); context.quadraticCurveTo(centerX - width * .18, top + height * .78, centerX - width * .27, top + height * .86); context.quadraticCurveTo(centerX + width * .08, top + height * .75, centerX + width * .2, top + height * .94); context.lineTo(centerX + width * .08, top + height * .7); context.closePath(); context.fill();
  context.globalAlpha = 1;
  context.beginPath();
  context.moveTo(centerX, top); context.bezierCurveTo(centerX - width * .13, top + height * .02, centerX - width * .15, top + height * .23, centerX - width * .08, top + height * .35);
  context.bezierCurveTo(centerX - width * .025, top + height * .42, centerX - width * .02, top + height * .55, centerX - width * .09, top + height * .69); context.stroke();
  context.beginPath();
  context.moveTo(centerX, top); context.bezierCurveTo(centerX + width * .12, top + height * .12, centerX + width * .12, top + height * .38, centerX + width * .28, top + height * .72); context.stroke();
  context.beginPath();
  context.moveTo(centerX - width * .07, top + height * .3); context.lineTo(centerX + width * .02, top + height * .29); context.lineTo(centerX - width * .04, top + height * .34); context.lineTo(centerX + width * .02, top + height * .38); context.stroke();
  for (let index = 0; index < 15; index += 1) {
    const offset = seeded(index, 8) * width * .23; const vertical = top + seeded(index, 9) * height * .58;
    context.beginPath(); context.moveTo(centerX + width * .03, top + height * .08 + index * height * .026); context.quadraticCurveTo(centerX + width * .12 + offset, vertical, centerX + width * (.2 + seeded(index, 10) * .3), vertical + height * .1); context.stroke();
  }
  context.beginPath(); context.moveTo(centerX - width * .1, top + height * .68); context.quadraticCurveTo(centerX - width * .18, top + height * .78, centerX - width * .27, top + height * .86); context.quadraticCurveTo(centerX + width * .08, top + height * .75, centerX + width * .2, top + height * .94); context.stroke();
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

createRoot(document.getElementById("root")!).render(<App />);
