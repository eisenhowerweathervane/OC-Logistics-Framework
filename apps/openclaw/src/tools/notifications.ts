import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsSendOverdueArSummary: AnyAgentTool = {
  name: "tms_send_overdue_ar_summary",
  label: "TMS: Send Overdue AR Summary",
  description:
    "Send a summary of overdue receivables to the dispatch Slack channel. " +
    "Use during weekly AR check-ins or when asked about unpaid invoices.",
  parameters: Type.Object({}),
  execute: async (_id, _params) => {
    try {
      const result = await api.post("/api/notifications/slack/overdue-ar-summary", {});
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsSendComplianceCheck: AnyAgentTool = {
  name: "tms_send_compliance_check",
  label: "TMS: Send Compliance Alerts",
  description:
    "Check fleet compliance status and send alerts to the dispatch Slack channel " +
    "for any expired or expiring annual inspections and overdue maintenance items.",
  parameters: Type.Object({}),
  execute: async (_id, _params) => {
    try {
      const result = await api.post("/api/notifications/slack/compliance-check", {});
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};
