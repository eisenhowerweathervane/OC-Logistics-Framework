import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsCreateLoad: AnyAgentTool = {
  name: "tms_create_load",
  label: "TMS: Create Load",
  description:
    "Create a new freight load in the TMS. Use when a new rate confirmation arrives or a load is verbally agreed. " +
    "Requires at least one stop (pickup). Returns the created load with its ID and initial status 'quoted'.",
  parameters: Type.Object({
    commodity: Type.Optional(Type.String({ description: "What is being hauled, e.g. 'Auto Parts'" })),
    rate_total: Type.Optional(Type.String({ description: "Total rate in dollars, e.g. '1850.00'" })),
    rate_type: Type.Optional(
      Type.Union([Type.Literal("flat"), Type.Literal("per_mile"), Type.Literal("percentage")], {
        description: "How the rate is structured",
      }),
    ),
    miles_loaded: Type.Optional(Type.String({ description: "Loaded miles, e.g. '485'" })),
    reference_number: Type.Optional(Type.String({ description: "Broker reference or load number" })),
    notes: Type.Optional(Type.String({ description: "Any special instructions or notes" })),
    stops: Type.Array(
      Type.Object({
        seq: Type.Number({ description: "Stop sequence starting at 1" }),
        stop_type: Type.Union([Type.Literal("pickup"), Type.Literal("delivery")], {
          description: "Pickup or delivery",
        }),
        facility_name: Type.Optional(Type.String()),
        city: Type.Optional(Type.String()),
        state: Type.Optional(Type.String({ description: "2-letter state code" })),
        appt_start: Type.Optional(Type.String({ description: "ISO 8601 appointment window start" })),
        appt_end: Type.Optional(Type.String({ description: "ISO 8601 appointment window end" })),
      }),
      { description: "At minimum one pickup stop required" },
    ),
  }),
  execute: async (_id, params) => {
    try {
      const load = await api.post("/api/loads", params);
      return ok(load);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListLoads: AnyAgentTool = {
  name: "tms_list_loads",
  label: "TMS: List Loads",
  description:
    "List loads for the organization. Filter by status to find active loads, pending invoicing, etc. " +
    "Returns a summary list (no stops detail). Use tms_get_load for full details.",
  parameters: Type.Object({
    status: Type.Optional(
      Type.String({
        description:
          "Filter by load status: quoted, booked, dispatched, arrived_pickup, loaded, in_transit, " +
          "arrived_delivery, delivered, invoice_ready, invoiced, paid, closed, archived",
      }),
    ),
    broker_id: Type.Optional(Type.String({ description: "Filter by broker UUID" })),
    date_from: Type.Optional(Type.String({ description: "ISO 8601 datetime — only loads created on or after this date" })),
    date_to: Type.Optional(Type.String({ description: "ISO 8601 datetime — only loads created on or before this date" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("status", params.status);
      if (params.broker_id) qs.set("broker_id", params.broker_id);
      if (params.date_from) qs.set("date_from", params.date_from);
      if (params.date_to) qs.set("date_to", params.date_to);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const loads = await api.get(`/api/loads?${qs}`);
      return ok(loads);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetLoad: AnyAgentTool = {
  name: "tms_get_load",
  label: "TMS: Get Load",
  description:
    "Get full details for a single load including stops, current assignment, status history, and invoice summary.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
  }),
  execute: async (_id, params) => {
    try {
      const load = await api.get(`/api/loads/${params.load_id}`);
      return ok(load);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateLoadStatus: AnyAgentTool = {
  name: "tms_update_load_status",
  label: "TMS: Update Load Status",
  description:
    "Advance a load through the state machine. Returns 422 if the transition is not allowed. " +
    "Valid sequence: quoted → booked → dispatched → arrived_pickup → loaded → in_transit → " +
    "arrived_delivery → delivered → invoice_ready → invoiced → paid → closed → archived. " +
    "Use this when the driver reports a pickup, delivery, etc.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
    status: Type.String({ description: "Target status to transition to" }),
    occurred_at: Type.String({ description: "ISO 8601 timestamp when the event occurred" }),
    location_city: Type.Optional(Type.String({ description: "City where the event occurred" })),
    note: Type.Optional(Type.String({ description: "Additional note to attach to the event" })),
  }),
  execute: async (_id, params) => {
    try {
      const { load_id, ...body } = params;
      const event = await api.post(`/api/loads/${load_id}/status-events`, body);
      return ok(event);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsAssignDriver: AnyAgentTool = {
  name: "tms_assign_driver",
  label: "TMS: Assign Driver",
  description:
    "Assign a driver and vehicle to a load. Use tms_list_drivers and tms_list_vehicles first to get valid IDs. " +
    "Automatically transitions the load from 'booked' to 'dispatched'.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
    driver_id: Type.String({ description: "UUID of the driver" }),
    vehicle_id: Type.String({ description: "UUID of the truck/vehicle" }),
    trailer_id: Type.Optional(Type.String({ description: "UUID of the trailer (if applicable)" })),
  }),
  execute: async (_id, params) => {
    try {
      const { load_id, ...body } = params;
      const assignment = await api.post(`/api/loads/${load_id}/assignments`, body);
      return ok(assignment);
    } catch (e) {
      return err(e);
    }
  },
};
