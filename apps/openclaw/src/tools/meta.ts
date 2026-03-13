import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsSystemInfo: AnyAgentTool = {
  name: "tms_system_info",
  label: "TMS: System Info",
  description:
    "Get live metadata about the OC Logistics TMS: frontend pages and URLs, " +
    "API route groups, running services, and current sandbox mode status. " +
    "Call this when you need to know what the system can do, what pages exist " +
    "in the dashboard, or to direct users to the right frontend page.",
  parameters: Type.Object({}),
  execute: async () => {
    try {
      const info = await api.get("/api/meta/system-info");
      return ok(info);
    } catch (e) {
      return err(e);
    }
  },
};
