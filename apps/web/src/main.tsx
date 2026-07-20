import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiFailure,
  Capability,
  ChatResult,
  Health,
  OpticHealthQuery,
  Scope,
  platformApi
} from "./api";
import "./styles.css";

type Panel = "chat" | "workspace" | "capabilities";
const HEALTH_LABELS: Record<Health, string> = {
  healthy: "正常",
  critical: "严重",
  warning: "告警",
  recovered: "已恢复",
  unknown: "数据缺失"
};

function App() {
  const [panel, setPanel] = useState<Panel>("chat");
  const [scope, setScope] = useState<Scope | null>(null);
  const [runtimeProfile, setRuntimeProfile] = useState<"developer" | "standalone">("developer");
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [opticHealth, setOpticHealth] = useState<OpticHealthQuery | null>(null);
  const [workspaceNotice, setWorkspaceNotice] = useState<string | null>(null);
  const [question, setQuestion] = useState("查看当前光模块健康异常");
  const [healthFilter, setHealthFilter] = useState<Health | "">("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([platformApi.session(), platformApi.capabilities(), platformApi.opticHealth()])
      .then(([session, catalog, response]) => {
        setScope(session.scope);
        setRuntimeProfile(session.profile);
        setCapabilities(catalog.capabilities);
        setOpticHealth(response.query);
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
    void platformApi.chat(question).then((response) => {
      setChat(response);
      setOpticHealth(response.optic_health);
      setHealthFilter("");
      setSearch("");
    }).catch(showError);
  }

  function loadWorkspace(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setError(null);
    void platformApi.opticHealth({ health: healthFilter || undefined, search: search || undefined })
      .then((response) => setOpticHealth(response.query))
      .catch(showError);
  }

  function validateWorkspace() {
    if (!scope || !opticHealth) return;
    setError(null);
    setWorkspaceNotice(null);
    void platformApi.validateOpticView(scope, {
      health: healthFilter ? [healthFilter] : [],
      time_range: { from: opticHealth.observed_from, to: opticHealth.observed_to },
      source: opticHealth.source
    }).then((response) => setWorkspaceNotice(
      `已验证 ${response.view_context.view_id}；仅允许当前服务端签发的 read Scope。`
    )).catch(showError);
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">ASKLILY · {runtimeProfile.toUpperCase()} PROFILE · P2</p>
          <h1>光模块健康 Demo</h1>
        </div>
        <span className="badge">Fixture L0/L1 · 严格只读 · 非生产阈值</span>
      </header>
      <nav aria-label="平台区域">
        {(["chat", "workspace", "capabilities"] as Panel[]).map((item) => (
          <button className={panel === item ? "active" : ""} key={item} onClick={() => setPanel(item)}>
            {{ chat: "Chat", workspace: "Workspace", capabilities: "Capability Center" }[item]}
          </button>
        ))}
      </nav>
      {error && <p className="error" role="alert">服务端未接受该请求：{error}</p>}
      {loading && <p>正在读取受限光模块 Fixture…</p>}
      {!loading && panel === "chat" && (
        <section>
          <h2>Chat</h2>
          <p>问题将调用受授权的只读 <code>optic_health.query</code>；结论只基于 Fixture。</p>
          <form onSubmit={submitChat}>
            <label htmlFor="question">问题</label>
            <textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} />
            <button type="submit">查询光模块健康</button>
          </form>
          {chat && (
            <article>
              <p>{chat.message}</p>
              <p>来源：{chat.sources.join("、") || "无"}</p>
              <p>限制：{chat.limitations.join("、")}</p>
              <button onClick={() => setPanel("workspace")}>在 Workspace 查看结果</button>
            </article>
          )}
        </section>
      )}
      {!loading && panel === "workspace" && opticHealth && (
        <section>
          <h2>Workspace · optic_health</h2>
          <p className="hint">来源：{opticHealth.source} · 规则：{opticHealth.rule_version} · 非真实数据</p>
          <form className="filters" onSubmit={loadWorkspace}>
            <label>健康状态
              <select value={healthFilter} onChange={(event) => setHealthFilter(event.target.value as Health | "")}>
                <option value="">全部</option>
                {Object.entries(HEALTH_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>资源搜索
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="例如 leaf-a02" />
            </label>
            <button type="submit">应用受限筛选</button>
          </form>
          <div className="summary" aria-label="健康汇总">
            {Object.entries(opticHealth.summary).map(([health, count]) => <span key={health}>{HEALTH_LABELS[health as Health]} {count}</span>)}
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>资源</th><th>站点</th><th>健康</th><th>原因</th><th>观测时间</th></tr></thead>
              <tbody>{opticHealth.records.map((record) => (
                <tr key={record.resource.resource_id}>
                  <td>{record.resource.display_name}</td><td>{record.resource.site_id}</td>
                  <td><span className={`health ${record.assessment.health}`}>{HEALTH_LABELS[record.assessment.health]}</span></td>
                  <td>{record.assessment.reason_codes.join("、") || "-"}</td><td>{record.latest_observation.observed_at}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
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
