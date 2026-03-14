import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsGenerateSettlement: AnyAgentTool = {
  name: "tms_generate_settlement",
  label: "TMS: Generate Driver Settlement",
  description:
    "Generate a draft settlement for a driver covering a date range. " +
    "Finds all delivered loads assigned to the driver in that period and " +
    "calculates pay based on the driver's pay_type (per_mile, percentage, flat_rate) and pay_rate.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
    period_start: Type.String({ description: "Start date (YYYY-MM-DD)" }),
    period_end: Type.String({ description: "End date (YYYY-MM-DD)" }),
  }),
  execute: async (_id, params) => {
    try {
      const settlement = await api.post("/api/settlements/generate", params);
      return ok(settlement);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListSettlements: AnyAgentTool = {
  name: "tms_list_settlements",
  label: "TMS: List Settlements",
  description: "List driver settlements, optionally filtered by driver or status.",
  parameters: Type.Object({
    driver_id: Type.Optional(Type.String({ description: "UUID of a driver to filter by" })),
    status: Type.Optional(Type.String({ description: "Filter by status: draft, approved, paid" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.driver_id) qs.set("driver_id", params.driver_id);
      if (params.status) qs.set("settlement_status", params.status);
      const settlements = await api.get(`/api/settlements?${qs}`);
      return ok(settlements);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetSettlement: AnyAgentTool = {
  name: "tms_get_settlement",
  label: "TMS: Get Settlement Detail",
  description: "Get full settlement details including all line items.",
  parameters: Type.Object({
    settlement_id: Type.String({ description: "UUID of the settlement" }),
  }),
  execute: async (_id, params) => {
    try {
      const settlement = await api.get(`/api/settlements/${params.settlement_id}`);
      return ok(settlement);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsApproveSettlement: AnyAgentTool = {
  name: "tms_approve_settlement",
  label: "TMS: Approve Settlement",
  description: "Approve a draft settlement, locking it for payment.",
  parameters: Type.Object({
    settlement_id: Type.String({ description: "UUID of the settlement" }),
  }),
  execute: async (_id, params) => {
    try {
      const settlement = await api.post(`/api/settlements/${params.settlement_id}/approve`, {});
      return ok(settlement);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsPaySettlement: AnyAgentTool = {
  name: "tms_pay_settlement",
  label: "TMS: Mark Settlement Paid",
  description: "Mark an approved settlement as paid.",
  parameters: Type.Object({
    settlement_id: Type.String({ description: "UUID of the settlement" }),
  }),
  execute: async (_id, params) => {
    try {
      const settlement = await api.post(`/api/settlements/${params.settlement_id}/pay`, {});
      return ok(settlement);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsAddSettlementLine: AnyAgentTool = {
  name: "tms_add_settlement_line",
  label: "TMS: Add Settlement Line Item",
  description:
    "Add a manual line item to a draft settlement — use for fuel advances, " +
    "deductions, bonuses, or reimbursements.",
  parameters: Type.Object({
    settlement_id: Type.String({ description: "UUID of the settlement" }),
    line_type: Type.String({
      description: "Type: load_pay, fuel_advance, deduction, bonus, reimbursement",
    }),
    amount: Type.String({ description: "Dollar amount (negative for deductions)" }),
    description: Type.Optional(Type.String({ description: "Description of the line item" })),
    load_id: Type.Optional(Type.String({ description: "UUID of related load (optional)" })),
  }),
  execute: async (_id, params) => {
    try {
      const { settlement_id, ...body } = params;
      const line = await api.post(`/api/settlements/${settlement_id}/lines`, body);
      return ok(line);
    } catch (e) {
      return err(e);
    }
  },
};
