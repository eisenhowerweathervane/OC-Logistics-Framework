import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsScoreLoad: AnyAgentTool = {
  name: "tms_score_load",
  label: "TMS: Score Load",
  description:
    "Get the rate-per-mile score and letter grade for a load. " +
    "Use to evaluate whether a load is worth booking — answers 'is this load a good deal?'",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load to score" }),
  }),
  execute: async (_id, params) => {
    try {
      const score = await api.get(`/api/scoring/loads/${params.load_id}`);
      return ok(score);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsLaneProfitability: AnyAgentTool = {
  name: "tms_lane_profitability",
  label: "TMS: Lane Profitability",
  description:
    "Analyze which origin→destination lanes are most profitable based on historical loads. " +
    "Optionally filter by origin/destination state. Answers 'which lanes pay best?'",
  parameters: Type.Object({
    origin_state: Type.Optional(Type.String({ description: "2-letter origin state code, e.g. 'TX'" })),
    dest_state: Type.Optional(Type.String({ description: "2-letter destination state code, e.g. 'TN'" })),
    limit: Type.Optional(Type.Number({ description: "Max results to return (default 20)" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.origin_state) qs.set("origin_state", params.origin_state);
      if (params.dest_state) qs.set("dest_state", params.dest_state);
      if (params.limit) qs.set("limit", String(params.limit));
      const lanes = await api.get(`/api/scoring/lanes?${qs}`);
      return ok(lanes);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsBrokerRatings: AnyAgentTool = {
  name: "tms_broker_ratings",
  label: "TMS: Broker Ratings",
  description:
    "Get broker ratings based on historical performance: average RPM, payment speed, and load volume. " +
    "Answers 'which brokers should we work with?' or 'who pays the best rates?'",
  parameters: Type.Object({
    limit: Type.Optional(Type.Number({ description: "Max results to return (default 20)" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.limit) qs.set("limit", String(params.limit));
      const ratings = await api.get(`/api/scoring/brokers?${qs}`);
      return ok(ratings);
    } catch (e) {
      return err(e);
    }
  },
};
