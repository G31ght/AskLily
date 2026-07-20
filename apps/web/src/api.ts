export type Scope = {
  project_id: string;
  site_ids: string[];
  cluster_ids: string[];
  resource_types: string[];
  actions: string[];
};

export type Session = {
  request_id: string;
  identity: { role: string; display_name: string };
  scope: Scope;
  profile: "developer";
};

export type Capability = {
  capability_id: string;
  version: string;
  owner: string;
  status: string;
  profile: string;
  tool_ids: string[];
  view_ids: string[];
  limitations: string[];
};

export type ViewContext = {
  view_id: string;
  version: string;
  scope: Scope;
  filters: Record<string, unknown>;
  focus_resource_id: string | null;
  query_id: string | null;
};

export type ChatResult = {
  request_id: string;
  message: string;
  question_acknowledged: string;
  sources: string[];
  view_context: ViewContext;
  limitations: string[];
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
  capabilities: () => request<{ request_id: string; capabilities: Capability[] }>("/v1/capabilities"),
  validatePlatformView: (scope: Scope) =>
    request<{ request_id: string; view_context: ViewContext }>("/v1/views/context", {
      method: "POST",
      body: JSON.stringify({ view_id: "platform_status", scope })
    }),
  chat: (question: string) =>
    request<ChatResult>("/v1/chat", { method: "POST", body: JSON.stringify({ question }) })
};
