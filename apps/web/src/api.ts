export type Scope = {
  project_id: string;
  site_ids: string[];
  cluster_ids: string[];
  resource_types: string[];
  actions: string[];
};

export type DataSourceState = {
  source_id: string;
  kind: "fixture" | "zabbix" | "prometheus";
  enabled: boolean;
  read_only: boolean;
  data_level: "L0_L1" | "unverified";
  declared_environment: "fixture" | "test" | "production";
  visible_site_ids: string[];
  connection_state: "ready" | "disabled" | "unavailable";
  reason_code: string | null;
  last_checked_at: string | null;
  config_revision: string;
};

export type RuntimeContext = {
  schema_version: string;
  declared_environment: "fixture" | "test" | "production";
  data_sources: DataSourceState[];
};

export type Session = {
  request_id: string;
  identity: { role: string; display_name: string; authenticated: boolean };
  scope: Scope;
  runtime: RuntimeContext;
};

export type Capability = {
  capability_id: string;
  version: string;
  owner: string;
  status: string;
  data_source_ids: string[];
  tool_ids: string[];
  view_ids: string[];
  limitations: string[];
  enabled: boolean;
  manageable: boolean;
};

export type ViewContext = {
  view_id: string;
  version: string;
  scope: Scope;
  filters: Record<string, unknown>;
  focus_resource_id: string | null;
  query_id: string | null;
};

export type PresentationModule = { module_id: string; view_id: string };
export type PresentationDirective = { mode: "chat" | "work"; modules: PresentationModule[] };

export type CapabilityStatus = {
  code: "ready" | "not_configured" | "unavailable" | "disabled" | "scope_not_allowed";
  reason_code: string | null;
};

export type CapabilityCatalogItem = {
  capability_id: string;
  display_name: string;
  summary: string;
  category: string;
  status: CapabilityStatus;
  data_sources: DataSourceState[];
  verification_level: string;
  read_only: boolean;
  limitations: string[];
  next_actions: Array<{ kind: "chat"; question: string }>;
};

export type CapabilityCatalog = {
  declared_environment: "fixture" | "test" | "production";
  capabilities: CapabilityCatalogItem[];
};

export type CapabilityCatalogPayload = {
  catalog: CapabilityCatalog;
  presentation: PresentationDirective;
  view_context: ViewContext;
};

export type CapabilityCatalogResponse = { request_id: string; catalog_version: string } & CapabilityCatalogPayload;

type ChatResultBase = {
  request_id: string;
  message: string;
  question_acknowledged: string;
  sources: string[];
  view_context: ViewContext;
  limitations: string[];
  presentation: PresentationDirective;
  conversation_id?: string;
};

export type OpticHealthChatResult = ChatResultBase & {
  response_kind: "optic_health";
  optic_health: OpticHealthQuery;
};

export type CapabilityCatalogChatResult = ChatResultBase & CapabilityCatalogPayload & {
  response_kind: "capability_catalog";
};

export type ChatResult = OpticHealthChatResult | CapabilityCatalogChatResult;
export type Conversation = { conversation_id: string; title: string; updated_at: string };
export type ConversationMessage = { author: "user" | "assistant"; body: string; source_label: string | null; limitation_label: string | null; created_at: string };
export type ConversationDetail = Conversation & { messages: ConversationMessage[] };
export type LocalIdentity = { account_id: string; username: string; display_name: string; role: string; scope: Scope };
export type AdminOverview = { metrics: { capability_total: number; capability_enabled: number; capability_disabled: number; account_total: number; account_active: number; audit_event_total: number } };
export type AdminAccount = { account_id: string; username: string; display_name: string; role: string; project_id: string; site_ids: string[]; status: "active" | "disabled"; created_at: string };
export type AuditEvent = { event_id: string; occurred_at: string; actor_id: string; action: string; outcome: string; request_id: string; query_id: string | null; scope_project_id: string; tool_id: string | null; reason_code: string | null };
export type MonitoringSourceReadiness = { source_id: string; source_kind: "zabbix" | "prometheus"; status: "ready" | "blocked"; blockers: string[]; allowed_operations: string[] };
export type AdminSystem = { runtime: RuntimeContext; persisted_data_source_status: Array<Omit<DataSourceState, "enabled" | "read_only" | "visible_site_ids" | "last_checked_at"> & { observed_at: string }>; monitoring_source_readiness: MonitoringSourceReadiness[]; read_only: boolean; configuration_schema: string; limitations: string[] };
export type AdminBootstrapStatus = { bootstrap_required: boolean };

export type Health = "healthy" | "critical" | "warning" | "recovered" | "unknown";

export type OpticHealthRecord = {
  resource: { resource_id: string; display_name: string; site_id: string | null; resource_type: string };
  latest_observation: {
    observed_at: string;
    source: string;
    quality: string;
    values: { rx_dbm: number | null; tx_dbm: number | null; temperature_c: number | null };
  };
  assessment: { health: Health; reason_codes: string[]; evaluated_at: string; rule_version: string };
  event: { fingerprint: string; status: string } | null;
};

export type OpticHealthQuery = {
  summary: Partial<Record<Health, number>>;
  source: string;
  observed_from: string;
  observed_to: string;
  rule_version: string;
  records: OpticHealthRecord[];
};

export class ApiFailure extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message);
    this.name = "ApiFailure";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  const body = (await response.json()) as T | { detail?: { code?: string; request_id?: string } };
  if (!response.ok) {
    const detail = body as { detail?: { code?: string; request_id?: string } };
    throw new ApiFailure(
      response.status,
      detail.detail?.code ?? "api_request_failed",
      `服务端拒绝或不可用（HTTP ${response.status}）`,
      detail.detail?.request_id
    );
  }
  return body as T;
}

export const platformApi = {
  session: () => request<Session>("/v1/session"),
  capabilityCatalog: () => request<CapabilityCatalogResponse>("/v1/capability-catalog"),
  validateOpticView: (scope: Scope, filters: Record<string, unknown>) =>
    request<{ request_id: string; view_context: ViewContext }>("/v1/views/context", {
      method: "POST",
      body: JSON.stringify({ view_id: "optic_health", scope, filters })
    }),
  login: (username: string, password: string) => request<{ identity: LocalIdentity }>("/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request<{ status: string }>("/v1/auth/logout", { method: "POST" }),
  adminBootstrapStatus: () => request<AdminBootstrapStatus>("/v1/admin/bootstrap-status"),
  bootstrapAdmin: (username: string, password: string, displayName?: string) => request<{ identity: LocalIdentity }>("/v1/admin/bootstrap", { method: "POST", body: JSON.stringify({ username, password, display_name: displayName || undefined }) }),
  conversations: () => request<{ conversations: Conversation[] }>("/v1/conversations"),
  conversation: (conversationId: string) => request<{ conversation: ConversationDetail }>(`/v1/conversations/${conversationId}`),
  deleteConversation: (conversationId: string) => request<{ status: string }>(`/v1/conversations/${conversationId}`, { method: "DELETE" }),
  chat: (question: string, conversationId?: string) =>
    request<ChatResult>("/v1/chat", { method: "POST", body: JSON.stringify({ question, conversation_id: conversationId }) }),
  opticHealth: (filters: { health?: Health; search?: string } = {}) => {
    const parameters = new URLSearchParams();
    if (filters.health) parameters.set("health", filters.health);
    if (filters.search) parameters.set("search", filters.search);
    const suffix = parameters.size ? `?${parameters.toString()}` : "";
    return request<{ request_id: string; query: OpticHealthQuery }>(`/v1/optic-health${suffix}`);
  },
  adminOverview: () => request<AdminOverview>("/v1/admin/overview"),
  adminCapabilities: () => request<{ capabilities: Capability[] }>("/v1/admin/capabilities"),
  setCapabilityState: (capabilityId: string, enabled: boolean) => request<{ capability: Capability }>(`/v1/admin/capabilities/${capabilityId}/state`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  adminAccounts: () => request<{ accounts: AdminAccount[] }>("/v1/admin/accounts"),
  createAdminAccount: (username: string, password: string, siteIds: string[], displayName?: string) => request<{ account: LocalIdentity }>("/v1/admin/accounts", { method: "POST", body: JSON.stringify({ username, password, display_name: displayName || undefined, site_ids: siteIds }) }),
  setAccountState: (accountId: string, status: "active" | "disabled") => request<{ account: AdminAccount }>(`/v1/admin/accounts/${accountId}/state`, { method: "PATCH", body: JSON.stringify({ status }) }),
  revokeAccountSessions: (accountId: string) => request<{ status: string }>(`/v1/admin/accounts/${accountId}/sessions`, { method: "DELETE" }),
  adminAudit: (action?: string) => request<{ events: AuditEvent[] }>(`/v1/admin/audit${action ? `?action=${encodeURIComponent(action)}` : ""}`),
  adminSystem: () => request<AdminSystem>("/v1/admin/system")
};
