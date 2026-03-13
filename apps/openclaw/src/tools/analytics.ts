import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsDashboard: AnyAgentTool = {
  name: "tms_dashboard",
  label: "TMS: Dashboard Summary",
  description:
    "Get a high-level KPI summary: active loads, total revenue, fleet size, and key metrics. " +
    "Use for quick status checks like 'how's business?' or 'what's our current load count?'",
  parameters: Type.Object({}),
  execute: async (_id) => {
    try {
      const data = await api.get("/api/analytics/dashboard");
      return ok(data);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsRevenueReport: AnyAgentTool = {
  name: "tms_revenue_report",
  label: "TMS: Revenue Report",
  description:
    "Get revenue broken down by time period. Use for questions like " +
    "'what did we make last month?' or 'show me weekly revenue trends'.",
  parameters: Type.Object({
    period: Type.Optional(
      Type.Union([Type.Literal("weekly"), Type.Literal("monthly")], {
        description: "Group by week or month (default: monthly)",
      }),
    ),
    months_back: Type.Optional(
      Type.Number({ description: "How many months of history to include (1-24, default 6)" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.period) qs.set("period", params.period);
      if (params.months_back) qs.set("months_back", String(params.months_back));
      const data = await api.get(`/api/analytics/revenue?${qs}`);
      return ok(data);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsFleetUtilization: AnyAgentTool = {
  name: "tms_fleet_utilization",
  label: "TMS: Fleet Utilization",
  description:
    "Get per-driver utilization metrics: load count, total revenue, total miles, and current status. " +
    "Use for driver performance comparisons or answering 'who's been busiest?'",
  parameters: Type.Object({}),
  execute: async (_id) => {
    try {
      const data = await api.get("/api/analytics/fleet-utilization");
      return ok(data);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsFuelCosts: AnyAgentTool = {
  name: "tms_fuel_costs",
  label: "TMS: Fuel Cost Summary",
  description:
    "Get fuel spending summary over recent months. Use for expense tracking or answering " +
    "'how much did we spend on fuel last quarter?'",
  parameters: Type.Object({
    months_back: Type.Optional(
      Type.Number({ description: "How many months of history (1-24, default 3)" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.months_back) qs.set("months_back", String(params.months_back));
      const data = await api.get(`/api/analytics/fuel-costs?${qs}`);
      return ok(data);
    } catch (e) {
      return err(e);
    }
  },
};
