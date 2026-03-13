import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsLogFuel: AnyAgentTool = {
  name: "tms_log_fuel",
  label: "TMS: Log Fuel Purchase",
  description:
    "Record a fuel purchase for IFTA tracking. Use when the driver reports stopping for fuel. " +
    "Jurisdiction is the 2-letter state/province code where the fuel was purchased.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
    purchased_at: Type.String({ description: "ISO 8601 timestamp of the purchase" }),
    seller_name: Type.String({ description: "Name of the fuel stop, e.g. 'Pilot Flying J #142'" }),
    jurisdiction: Type.Optional(Type.String({ description: "2-letter state/province code, e.g. 'OH'" })),
    fuel_type: Type.Optional(
      Type.Union([Type.Literal("diesel"), Type.Literal("gasoline"), Type.Literal("def")]),
    ),
    gallons: Type.Optional(Type.String({ description: "Gallons purchased, e.g. '150.450'" })),
    total_price: Type.Optional(Type.String({ description: "Total dollar amount, e.g. '586.71'" })),
  }),
  execute: async (_id, params) => {
    try {
      const body = {
        vehicle_id: params.vehicle_id,
        purchased_at_local: params.purchased_at,
        seller_name: params.seller_name,
        jurisdiction: params.jurisdiction,
        fuel_type: params.fuel_type,
        gallons: params.gallons,
        total_price: params.total_price,
      };
      const purchase = await api.post("/api/fuel/purchases", body);
      return ok(purchase);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsLogMaintenance: AnyAgentTool = {
  name: "tms_log_maintenance",
  label: "TMS: Log Maintenance Item",
  description:
    "Create a maintenance reminder or service item for a vehicle. " +
    "Use for upcoming oil changes, tire replacements, DOT-required inspections, etc.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
    category: Type.String({ description: "Type of maintenance: oil_change, tires, brake_inspection, etc." }),
    due_date: Type.Optional(Type.String({ description: "ISO date when service is due, e.g. '2026-06-01'" })),
    notes: Type.Optional(Type.String()),
  }),
  execute: async (_id, params) => {
    try {
      const item = await api.post("/api/compliance/maintenance", params);
      return ok(item);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListMaintenance: AnyAgentTool = {
  name: "tms_list_maintenance",
  label: "TMS: List Maintenance Items",
  description: "List open maintenance items for the fleet. Filter by vehicle_id for a specific truck.",
  parameters: Type.Object({
    vehicle_id: Type.Optional(Type.String({ description: "UUID of the vehicle (optional filter)" })),
    status: Type.Optional(
      Type.String({ description: "Status filter: open, overdue, due_soon, closed" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.status) qs.set("item_status", params.status);
      const items = await api.get(`/api/compliance/maintenance?${qs}`);
      return ok(items);
    } catch (e) {
      return err(e);
    }
  },
};
