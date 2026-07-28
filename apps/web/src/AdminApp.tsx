import { FormEvent, useEffect, useState } from "react";
import { AdminAccount, AdminOverview, AdminSystem, ApiFailure, AuditEvent, Capability, Session, platformApi } from "./api";
import "./admin.css";

type AdminPanel = "overview" | "capabilities" | "accounts" | "audit" | "system";

const NAVIGATION: { id: AdminPanel; icon: string; label: string }[] = [
  { id: "overview", icon: "◇", label: "概览" },
  { id: "capabilities", icon: "✦", label: "能力管理" },
  { id: "accounts", icon: "◉", label: "账号管理" },
  { id: "audit", icon: "◫", label: "审计日志" },
  { id: "system", icon: "⌘", label: "系统设置" },
];

function errorCode(error: unknown) { return error instanceof ApiFailure ? error.code : "api_unavailable"; }
function displayTime(value: string) { return new Date(value).toLocaleString([], { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }

export function AdminApp() {
  const [session, setSession] = useState<Session | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [system, setSystem] = useState<AdminSystem | null>(null);
  const [panel, setPanel] = useState<AdminPanel>("overview");
  const [loading, setLoading] = useState(true);
  const [redirectToFront, setRedirectToFront] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditFilter, setAuditFilter] = useState("");

  const refresh = (action = auditFilter) => void platformApi.session().then(async (nextSession) => {
    setSession(nextSession);
    if (!nextSession.identity.authenticated) return;
    if (nextSession.identity.role !== "project-admin") return;
    const [nextOverview, nextCapabilities, nextAccounts, nextAudit, nextSystem] = await Promise.all([
      platformApi.adminOverview(), platformApi.adminCapabilities(), platformApi.adminAccounts(), platformApi.adminAudit(action || undefined), platformApi.adminSystem(),
    ]);
    setOverview(nextOverview); setCapabilities(nextCapabilities.capabilities); setAccounts(nextAccounts.accounts); setAudit(nextAudit.events); setSystem(nextSystem);
  }).catch((reason) => {
    if (reason instanceof ApiFailure && reason.status === 401) {
      setRedirectToFront(true); setError(null); return;
    }
    setError(errorCode(reason));
  }).finally(() => setLoading(false));

  useEffect(() => { refresh(); }, []);
  useEffect(() => { if (!loading && (redirectToFront || (session && !session.identity.authenticated))) window.location.replace("/"); }, [loading, redirectToFront, session]);

  function signOut() { void platformApi.logout().finally(() => window.location.assign("/")); }
  function updateCapability(item: Capability) { void platformApi.setCapabilityState(item.capability_id, !item.enabled).then(() => refresh()).catch((reason) => setError(errorCode(reason))); }
  function updateAccount(item: AdminAccount) { const status = item.status === "active" ? "disabled" : "active"; void platformApi.setAccountState(item.account_id, status).then(() => refresh()).catch((reason) => setError(errorCode(reason))); }
  function revokeSessions(item: AdminAccount) { void platformApi.revokeAccountSessions(item.account_id).then(() => refresh()).catch((reason) => setError(errorCode(reason))); }
  function createAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const password = String(data.get("password") || "");
    if (password !== String(data.get("confirmation") || "")) { setError("local_password_confirmation_mismatch"); return; }
    const siteIds = data.getAll("site_ids").map(String);
    if (!siteIds.length) { setError("local_operator_scope_invalid"); return; }
    setError(null);
    void platformApi.createAdminAccount(String(data.get("username") || ""), password, siteIds, String(data.get("displayName") || ""))
      .then(() => { form.reset(); refresh(); }).catch((reason) => setError(errorCode(reason)));
  }

  if (loading) return <main className="admin-loading">正在验证本地管理权限…</main>;
  if (!session?.identity.authenticated) return <main className="admin-loading">正在返回前台登录…</main>;
  if (session.identity.role !== "project-admin") return <main className="admin-loading"><section className="admin-denied"><p className="admin-mark">◇</p><h1>管理权限受限</h1><p>当前账号不是 project-admin，不能进入管理控制面。</p><button onClick={() => window.location.assign("/")}>返回前台</button></section></main>;

  return <main className="admin-shell">
    <aside className="admin-rail">
      <a className="admin-brand" href="/"><span>◉</span><b>AskLily</b></a>
      <p className="admin-rail-label">管理控制面</p>
      <nav>{NAVIGATION.map((item) => <button className={panel === item.id ? "active" : ""} key={item.id} onClick={() => setPanel(item.id)}><span>{item.icon}</span>{item.label}</button>)}</nav>
      <div className="admin-identity"><span>{session.identity.display_name.slice(0, 1).toUpperCase()}</span><div><b>{session.identity.display_name}</b><small>本地项目管理员</small></div><button aria-label="退出后台" onClick={signOut}>↗</button></div>
    </aside>
    <section className="admin-main">
      <header className="admin-header"><div><p className="admin-kicker">ASKLILY · LOCAL CONTROL PLANE</p><h1>{NAVIGATION.find((item) => item.id === panel)?.label}</h1><p>仅管理已注册的本地能力；严格只读边界保持生效。</p></div><div className="admin-profile"><span className="status-dot"/> {session.profile} · Fixture L0/L1</div></header>
      {error && <p className="admin-error" role="alert">操作未完成：{error}</p>}
      {panel === "overview" && <Overview overview={overview} capabilities={capabilities} audit={audit} />}
      {panel === "capabilities" && <Capabilities capabilities={capabilities} onToggle={updateCapability} />}
      {panel === "accounts" && <Accounts accounts={accounts} availableSiteIds={session.scope.site_ids} onCreate={createAccount} onToggle={updateAccount} onRevoke={revokeSessions} />}
      {panel === "audit" && <Audit audit={audit} value={auditFilter} onChange={setAuditFilter} onApply={() => refresh(auditFilter)} />}
      {panel === "system" && <System system={system} />}
    </section>
  </main>;
}

function Overview({ overview, capabilities, audit }: { overview: AdminOverview | null; capabilities: Capability[]; audit: AuditEvent[] }) {
  const metrics = overview?.metrics;
  return <><section className="metric-grid"><Metric label="已注册能力" value={metrics?.capability_total ?? 0} note="来自 Capability Registry"/><Metric label="运行中能力" value={metrics?.capability_enabled ?? 0} note={`已停用 ${metrics?.capability_disabled ?? 0}`}/><Metric label="本地账号" value={metrics?.account_total ?? 0} note={`活动账号 ${metrics?.account_active ?? 0}`}/><Metric label="持久化审计" value={metrics?.audit_event_total ?? 0} note="最小审计元数据"/></section><section className="admin-grid"><article className="admin-card"><header><h2>能力状态</h2><span>真实注册信息</span></header><div className="state-list">{capabilities.map((item) => <div key={item.capability_id}><span className={item.enabled ? "state enabled" : "state disabled"}/><div><b>{item.capability_id}</b><small>{item.owner} · {item.version}</small></div><em>{item.enabled ? "运行中" : "已停用"}</em></div>)}</div></article><article className="admin-card"><header><h2>最近审计</h2><span>不含对话正文</span></header><div className="audit-preview">{audit.slice(0, 6).map((event) => <p key={event.event_id}><span className={event.outcome}>{event.outcome === "allowed" ? "●" : "●"}</span><b>{event.action}</b><small>{event.actor_id} · {displayTime(event.occurred_at)}</small></p>) || <p className="admin-muted">暂无本地审计事件</p>}</div></article></section></>;
}

function Metric({ label, value, note }: { label: string; value: number; note: string }) { return <article className="metric-card"><p>{label}</p><b>{value}</b><small>{note}</small></article>; }

function Capabilities({ capabilities, onToggle }: { capabilities: Capability[]; onToggle: (item: Capability) => void }) { return <section className="admin-card admin-table-card"><header><div><h2>已注册能力</h2><p>停用会由服务端拒绝执行，不会修改契约或数据边界。</p></div><span>{capabilities.length} 项</span></header><table><thead><tr><th>能力</th><th>版本</th><th>来源与限制</th><th>运行状态</th><th>操作</th></tr></thead><tbody>{capabilities.map((item) => <tr key={item.capability_id}><td><b>{item.capability_id}</b><small>{item.owner}</small></td><td>{item.version}</td><td><small>{item.limitations.join(" · ")}</small></td><td><span className={item.enabled ? "tag enabled" : "tag disabled"}>{item.enabled ? "运行中" : "已停用"}</span></td><td>{item.manageable ? <button className={item.enabled ? "admin-action danger" : "admin-action"} onClick={() => onToggle(item)}>{item.enabled ? "停用" : "恢复"}</button> : <small className="admin-muted">平台保护</small>}</td></tr>)}</tbody></table></section>; }

function Accounts({ accounts, availableSiteIds, onCreate, onToggle, onRevoke }: { accounts: AdminAccount[]; availableSiteIds: string[]; onCreate: (event: FormEvent<HTMLFormElement>) => void; onToggle: (item: AdminAccount) => void; onRevoke: (item: AdminAccount) => void }) { return <section className="admin-card admin-table-card"><header><div><h2>本地账号</h2><p>仅项目管理员可创建账号；所有账号都固定为只读 operator，并且只能获得你的站点范围子集。</p></div><span>{accounts.length} 个</span></header><form className="admin-account-create" onSubmit={onCreate}><label>账号<input required name="username" minLength={3}/></label><label>显示名称（可留空）<input name="displayName"/></label><label>初始密码<input required name="password" type="password" minLength={12}/></label><label>确认密码<input required name="confirmation" type="password" minLength={12}/></label><fieldset><legend>只读站点权限</legend>{availableSiteIds.map((siteId) => <label key={siteId}><input name="site_ids" type="checkbox" value={siteId}/>{siteId}</label>)}</fieldset><button className="admin-action" type="submit">创建 operator 账号</button></form><table><thead><tr><th>账号</th><th>角色 / Scope</th><th>创建时间</th><th>状态</th><th>操作</th></tr></thead><tbody>{accounts.map((item) => <tr key={item.account_id}><td><b>{item.display_name}</b><small>{item.username}</small></td><td><b>{item.role}</b><small>{item.project_id} · {item.site_ids.join(", ")}</small></td><td>{displayTime(item.created_at)}</td><td><span className={`tag ${item.status === "active" ? "enabled" : "disabled"}`}>{item.status === "active" ? "活动" : "已停用"}</span></td><td className="account-actions">{item.role === "project-admin" ? <small className="admin-muted">管理员保护</small> : <><button className="admin-action" onClick={() => onRevoke(item)}>撤销会话</button><button className={item.status === "active" ? "admin-action danger" : "admin-action"} onClick={() => onToggle(item)}>{item.status === "active" ? "停用" : "恢复"}</button></>}</td></tr>)}</tbody></table></section>; }

function Audit({ audit, value, onChange, onApply }: { audit: AuditEvent[]; value: string; onChange: (value: string) => void; onApply: () => void }) { return <section className="admin-card admin-table-card audit-card"><header><div><h2>持久化审计日志</h2><p>只记录最小控制面元数据；不包含密码、Token 或对话正文。</p></div><form className="audit-filter" onSubmit={(event) => { event.preventDefault(); onApply(); }}><input aria-label="按动作筛选" value={value} onChange={(event) => onChange(event.target.value)} placeholder="按动作精确筛选"/><button>筛选</button></form></header><div className="audit-log-scroll"><table><thead><tr><th>时间</th><th>动作</th><th>操作者</th><th>结果</th><th>原因 / Tool</th></tr></thead><tbody>{audit.map((event) => <tr key={event.event_id}><td>{displayTime(event.occurred_at)}</td><td><b>{event.action}</b><small>{event.request_id}</small></td><td>{event.actor_id}<small>{event.scope_project_id}</small></td><td><span className={`tag ${event.outcome === "allowed" ? "enabled" : "disabled"}`}>{event.outcome}</span></td><td><small>{event.reason_code ?? event.tool_id ?? "-"}</small></td></tr>)}</tbody></table></div>{!audit.length && <p className="admin-muted">没有匹配的本地审计事件。</p>}</section>; }

function System({ system }: { system: AdminSystem | null }) { return <section className="admin-grid system-grid"><article className="admin-card"><header><h2>运行边界</h2><span>只读</span></header><dl><dt>运行 Profile</dt><dd>{system?.profile ?? "-"}</dd><dt>数据等级</dt><dd>{system?.data_level ?? "-"}</dd><dt>业务配置 Schema</dt><dd>{system?.configuration_schema ?? "-"}</dd><dt>写操作</dt><dd>{system?.read_only ? "已禁止" : "-"}</dd></dl></article><article className="admin-card"><header><h2>当前限制</h2><span>不可由后台解除</span></header><ul>{system?.limitations.map((item) => <li key={item}>{item}</li>) ?? <li>正在读取系统状态</li>}</ul><p className="admin-muted">未来能力只有在注册版本化配置 Schema 后，才会在这里出现可编辑参数。</p></article></section>; }
