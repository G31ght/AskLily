import { describe, expect, it, vi } from "vitest";
import { ApiFailure, platformApi } from "./api";

describe("platform API client", () => {
  it("turns a typed server denial into ApiFailure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ detail: { code: "scope_site_not_allowed", request_id: "req-1" } })
      })
    );

    await expect(platformApi.chat("status")).rejects.toEqual(
      expect.objectContaining({
        code: "scope_site_not_allowed",
        requestId: "req-1",
        status: 403
      })
    );
  });

  it("sends Workspace health and search filters only through the API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ request_id: "req-2", query: { records: [], summary: {} } })
    });
    vi.stubGlobal("fetch", fetchMock);

    await platformApi.opticHealth({ health: "critical", search: "leaf-a02" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/optic-health?health=critical&search=leaf-a02",
      expect.objectContaining({ headers: { "Content-Type": "application/json" }})
    );
  });

  it("loads the server-authorized capability catalog without client-supplied scope or module", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        request_id: "req-catalog",
        catalog_version: "1.0.0",
        view_context: { view_id: "capability_catalog", version: "1.0.0", scope: {}, filters: {}, focus_resource_id: null, query_id: null },
        presentation: { mode: "work", modules: [{ module_id: "capability-catalog-overview", view_id: "capability_catalog" }] },
        catalog: { declared_environment: "fixture", capabilities: [] }
      })
    });
    vi.stubGlobal("fetch", fetchMock);

    await platformApi.capabilityCatalog();

    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/capability-catalog",
      expect.objectContaining({ headers: { "Content-Type": "application/json" }})
    );
  });

  it("sends only controlled resource search filters and never supplies Scope or View metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ request_id: "req-resource", query: { items: [], page: 2, page_size: 10, total: 0, has_more: false, source: "fixture", limitations: [] } })
    });
    vi.stubGlobal("fetch", fetchMock);

    await platformApi.resources({ query: "leaf-b01", site_id: "site-a", resource_type: "optic_module", health: ["critical", "warning"], page: 2 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/resources?query=leaf-b01&site_id=site-a&resource_type=optic_module&health=critical&health=warning&page=2",
      expect.objectContaining({ headers: { "Content-Type": "application/json" }})
    );
  });

  it("requests a selected resource detail by its server-returned ID only", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ request_id: "req-detail", detail: {} }) });
    vi.stubGlobal("fetch", fetchMock);

    await platformApi.resourceDetail("optic-a-02");

    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/resources/optic-a-02",
      expect.objectContaining({ headers: { "Content-Type": "application/json" }})
    );
  });
});
