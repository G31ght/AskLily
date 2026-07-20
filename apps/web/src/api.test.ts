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
});
