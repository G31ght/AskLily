import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiFailure, Capability, ChatResult, Scope, platformApi } from "./api";
import "./styles.css";

type Panel = "chat" | "workspace" | "capabilities";

function App() {
  const [panel, setPanel] = useState<Panel>("chat");
  const [scope, setScope] = useState<Scope | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [workspaceNotice, setWorkspaceNotice] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([platformApi.session(), platformApi.capabilities()])
      .then(([session, catalog]) => {
        setScope(session.scope);
        setCapabilities(catalog.capabilities);
      })
      .catch(showError)
      .finally(() => setLoading(false));
  }, []);

  function showError(reason: unknown) {
    if (reason instanceof ApiFailure) {
      setError(`${reason.code}${reason.requestId ? ` · ${reason.requestId}` : ""}`);
      return;
    }
    setError("api_unavailable");
  }

  function submitChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    setError(null);
    void platformApi
      .chat(question)
      .then(setChat)
      .catch(showError);
  }

  function validateWorkspace() {
    if (!scope) return;
    setError(null);
    setWorkspaceNotice(null);
    void platformApi
      .validatePlatformView(scope)
      .then((response) => setWorkspaceNotice(
        `已验证 ${response.view_context.view_id}；仅允许当前服务端签发的 read Scope。`
      ))
      .catch(showError);
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">ASKLILY · DEVELOPER PROFILE</p>
          <h1>P1 平台骨架</h1>
        </div>
        <span className="badge">无业务能力 · 无真实数据 · 严格只读</span>
      </header>
      <nav aria-label="平台区域">
        {(["chat", "workspace", "capabilities"] as Panel[]).map((item) => (
          <button className={panel === item ? "active" : ""} key={item} onClick={() => setPanel(item)}>
            {{ chat: "Chat", workspace: "Workspace", capabilities: "Capability Center" }[item]}
          </button>
        ))}
      </nav>
      {error && <p className="error" role="alert">服务端未接受该请求：{error}</p>}
      {loading && <p>正在读取开发身份与平台目录…</p>}
      {!loading && panel === "chat" && (
        <section>
          <h2>Chat</h2>
          <p>该对话只确认平台骨架状态；不会生成业务结论。</p>
          <form onSubmit={submitChat}>
            <label htmlFor="question">问题</label>
            <textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} />
            <button type="submit">发送只读请求</button>
          </form>
          {chat && <article><p>{chat.message}</p><p>限制：{chat.limitations.join("、")}</p></article>}
        </section>
      )}
      {!loading && panel === "workspace" && (
        <section>
          <h2>Workspace</h2>
          <p>唯一注册 View：<code>platform_status</code></p>
          <pre>{JSON.stringify(scope, null, 2)}</pre>
          <button onClick={validateWorkspace}>验证受限 ViewContext</button>
          {workspaceNotice && <p role="status">{workspaceNotice}</p>}
        </section>
      )}
      {!loading && panel === "capabilities" && (
        <section>
          <h2>Capability Center</h2>
          {capabilities.map((capability) => (
            <article key={capability.capability_id}>
              <h3>{capability.capability_id}</h3>
              <p>{capability.status} · {capability.profile}</p>
              <p>限制：{capability.limitations.join("、")}</p>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
