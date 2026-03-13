import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsSandboxStatus: AnyAgentTool = {
  name: "tms_sandbox_status",
  label: "TMS: Sandbox Status",
  description:
    "Check whether the TMS backend is running in sandbox mode. " +
    "Sandbox mode uses a demo database with sample data — changes won't affect production. " +
    "Always check this at the start of a conversation to inform the user which mode they're in.",
  parameters: Type.Object({}),
  execute: async () => {
    try {
      const status = await api.get("/api/sandbox/status");
      return ok(status);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsSandboxToggle: AnyAgentTool = {
  name: "tms_sandbox_toggle",
  label: "TMS: Toggle Sandbox",
  description:
    "Toggle sandbox mode on or off. When activating, creates a demo database with sample loads, " +
    "drivers, vehicles, brokers, and compliance data. When deactivating, removes sandbox data " +
    "and switches back to production. Requires owner or dispatcher role.",
  parameters: Type.Object({
    confirm: Type.Boolean({
      description: "Must be true to confirm the toggle action",
    }),
  }),
  execute: async (_id, params) => {
    if (!params.confirm) {
      return ok({ error: "Set confirm=true to toggle sandbox mode" });
    }
    try {
      const result = await api.post("/api/sandbox/toggle", {});
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};
