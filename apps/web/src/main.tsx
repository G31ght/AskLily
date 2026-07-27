import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiFailure, ChatResult, Conversation, ConversationMessage, Health, LocalIdentity, OpticHealthQuery, PresentationModule, Session, platformApi } from "./api";
import "./styles.css";

const HEALTH_LABELS: Record<Health, string> = { healthy: "正常", critical: "严重", warning: "告警", recovered: "已恢复", unknown: "数据缺失" };

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
  const [welcomeStage, setWelcomeStage] = useState<"portrait" | "questions">("portrait");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => void Promise.all([platformApi.session(), platformApi.opticHealth(), platformApi.capabilities()])
    .then(([nextSession, result]) => { setSession(nextSession); setOpticHealth(result.query); if (nextSession.identity.authenticated) void refreshHistory(); })
    .catch(showError).finally(() => setLoading(false));
  useEffect(refresh, []);
  useEffect(() => { const timer = window.setInterval(() => setWelcomeStage((stage) => stage === "portrait" ? "questions" : "portrait"), 7500); return () => window.clearInterval(timer); }, []);

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

  return <main className={workMode ? "shell work" : "shell"}>
    <aside className="rail">
      <div className="brand"><span>◉</span> AskLily</div>
      <button className="new" onClick={newChat}>＋ 新建对话</button>
      <p className="rail-title">最近对话</p>
      <div className="history">{conversations.length ? conversations.map((item) => <button className={conversationId === item.conversation_id ? "history-item active" : "history-item"} key={item.conversation_id} onClick={() => openConversation(item.conversation_id)}><span>{item.title}</span><small>{new Date(item.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></button>) : <p className="muted">暂无已保存对话</p>}</div>
      <div className="account"><span className="avatar">{(identity?.display_name ?? session.identity.display_name).slice(0, 1).toUpperCase()}</span><span>{identity?.display_name ?? session.identity.display_name}<small>{session.identity.role} · 本地账号</small></span><button onClick={signOut}>退出</button></div>
    </aside>
    <section className="conversation">
      <header><span className="eyebrow">ASKLILY · {session.profile.toUpperCase()} · FIXTURE L0/L1</span>{session.profile === "developer" && <button className="debug" onClick={() => setWorkMode((value) => !value)}>调试：{workMode ? "Chat" : "Work"}</button>}</header>
      {error && <p className="error" role="alert">请求未完成：{error}</p>}
      {!chat && !savedMessages.length ? <Welcome stage={welcomeStage} onAsk={ask} /> : chat ? <article className="answer"><p className="bubble">{chat.question_acknowledged}</p><p>{chat.message}</p><p className="meta">来源：{chat.sources.join("、")} · 限制：{chat.limitations.join("、")}</p></article> : <SavedConversation messages={savedMessages} />}
      <form className="composer" onSubmit={submitChat}><textarea aria-label="向 AskLily 提问" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="向 AskLily 提问…"/><button type="submit">↑</button></form>
    </section>
    {workMode && opticHealth && <section className="workbench" aria-label="Work Mode"><header><span>工作台 / Work Mode</span><span className="badge">严格只读 · Fixture</span></header><WorkspaceModules modules={chat?.presentation.modules ?? [{ module_id: "optic-health-overview", view_id: "optic_health" }]} query={opticHealth} /></section>}
  </main>;
}

function LoginForm({ error, onSubmit }: { error: string | null; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <main className="login"><section><p className="orb">✦</p><h1>AskLily</h1><p>本地账号仅保存 Fixture 对话，不连接真实系统。</p>{error && <p className="error">{error}</p>}<form onSubmit={onSubmit}><label>账号<input required name="username" minLength={3} /></label><label>密码<input required name="password" type="password" minLength={12} /></label><label>显示名称（注册时可选）<input name="displayName" /></label><div><button name="action" value="login">登录</button><button name="action" value="register">注册本地账号</button></div></form></section></main>; }

function Welcome({ stage, onAsk }: { stage: "portrait" | "questions"; onAsk: (question: string) => void }) { return <div className={`welcome ${stage}`}><div className="lily-visual" aria-hidden="true"><span className="particle-field" /><span className="lily-head" /><span className="lily-body" /></div><div className="welcome-copy">{stage === "portrait" ? <><p className="orb">✦</p><h1>从一个宽泛问题开始</h1><p>AskLily 会先给出可追溯的 Fixture 结论；你可以继续自然地追问。</p></> : <><p className="orb">关注提示</p><h1>有些信号值得先看一眼</h1><div className="suggestions"><button onClick={() => onAsk("查看当前光模块健康异常")}>哪些光模块需要关注？</button><button onClick={() => onAsk("哪些设备数据缺失？")}>哪些设备数据缺失？</button></div></>}</div></div>; }

function OpticModule({ query }: { query: OpticHealthQuery }) { return <article className="module"><h2>光模块健康概览</h2><p className="meta">{query.source} · 规则 {query.rule_version}</p><div className="summary">{Object.entries(query.summary).map(([key, value]) => <span key={key}>{HEALTH_LABELS[key as Health]} <b>{value}</b></span>)}</div><table><thead><tr><th>资源</th><th>站点</th><th>健康</th><th>原因</th></tr></thead><tbody>{query.records.map((record) => <tr key={record.resource.resource_id}><td>{record.resource.display_name}</td><td>{record.resource.site_id}</td><td>{HEALTH_LABELS[record.assessment.health]}</td><td>{record.assessment.reason_codes.join("、") || "-"}</td></tr>)}</tbody></table></article>; }

function WorkspaceModules({ modules, query }: { modules: PresentationModule[]; query: OpticHealthQuery }) { return <>{modules.map((module) => module.module_id === "optic-health-overview" && module.view_id === "optic_health" ? <OpticModule key={module.module_id} query={query} /> : <article className="module" key={module.module_id}><h2>未注册展示模块</h2><p className="meta">{module.module_id}</p></article>)}</>; }

function SavedConversation({ messages }: { messages: ConversationMessage[] }) { return <article className="answer saved-conversation">{messages.map((message, index) => <section key={`${message.created_at}-${index}`}><p className={message.author === "user" ? "bubble" : ""}>{message.body}</p>{message.author === "assistant" && <p className="meta">来源：{message.source_label ?? "-"} · 限制：{message.limitation_label ?? "-"}</p>}</section>)}</article>; }

createRoot(document.getElementById("root")!).render(<App />);
