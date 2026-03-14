import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsAddAccessorial: AnyAgentTool = {
  name: "tms_add_accessorial",
  label: "TMS: Add Accessorial Charge",
  description:
    "Add an accessorial charge to a load (detention, layover, TONU, lumper, fuel surcharge, toll, other). " +
    "These charges are billed on top of the base rate. Use when a driver reports extra charges.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
    charge_type: Type.String({
      description: "Type of charge: detention, layover, tonu, lumper, fuel_surcharge, toll, other",
    }),
    amount: Type.String({ description: "Dollar amount, e.g. '150.00'" }),
    description: Type.Optional(Type.String({ description: "Description of the charge" })),
    occurred_at: Type.Optional(Type.String({ description: "ISO 8601 timestamp when the charge occurred" })),
    notes: Type.Optional(Type.String({ description: "Additional notes" })),
  }),
  execute: async (_id, params) => {
    try {
      const { load_id, ...body } = params;
      const charge = await api.post(`/api/loads/${load_id}/accessorials`, body);
      return ok(charge);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListAccessorials: AnyAgentTool = {
  name: "tms_list_accessorials",
  label: "TMS: List Accessorial Charges",
  description: "List all accessorial charges for a load.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
  }),
  execute: async (_id, params) => {
    try {
      const charges = await api.get(`/api/loads/${params.load_id}/accessorials`);
      return ok(charges);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateAccessorial: AnyAgentTool = {
  name: "tms_update_accessorial",
  label: "TMS: Update Accessorial Charge",
  description: "Update an accessorial charge — change amount, status (pending/approved/invoiced), or notes.",
  parameters: Type.Object({
    charge_id: Type.String({ description: "UUID of the accessorial charge" }),
    charge_type: Type.Optional(Type.String({ description: "Updated charge type" })),
    amount: Type.Optional(Type.String({ description: "Updated dollar amount" })),
    status: Type.Optional(Type.String({ description: "Updated status: pending, approved, invoiced, paid" })),
    description: Type.Optional(Type.String({ description: "Updated description" })),
    notes: Type.Optional(Type.String({ description: "Updated notes" })),
  }),
  execute: async (_id, params) => {
    try {
      const { charge_id, ...body } = params;
      const charge = await api.patch(`/api/accessorials/${charge_id}`, body);
      return ok(charge);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsAccessorialSummary: AnyAgentTool = {
  name: "tms_accessorial_summary",
  label: "TMS: Accessorial Summary",
  description:
    "Get a summary of accessorial charges grouped by type with counts and totals. " +
    "Optionally filter to a specific load.",
  parameters: Type.Object({
    load_id: Type.Optional(Type.String({ description: "UUID of a load to filter by (optional)" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.load_id) qs.set("load_id", params.load_id);
      const summary = await api.get(`/api/accessorials/summary?${qs}`);
      return ok(summary);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsDeleteAccessorial: AnyAgentTool = {
  name: "tms_delete_accessorial",
  label: "TMS: Delete Accessorial Charge",
  description:
    "Delete an accessorial charge. Use when a charge was added in error or is no longer applicable. " +
    "This cannot be undone.",
  parameters: Type.Object({
    charge_id: Type.String({ description: "UUID of the accessorial charge to delete" }),
  }),
  execute: async (_id, params) => {
    try {
      await api.delete(`/api/accessorials/${params.charge_id}`);
      return ok({ deleted: true, charge_id: params.charge_id });
    } catch (e) {
      return err(e);
    }
  },
};
