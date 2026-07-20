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
});
