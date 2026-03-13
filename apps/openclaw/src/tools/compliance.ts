import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

// ── Fuel ─────────────────────────────────────────────────────────────────────

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

export const tmsListFuelPurchases: AnyAgentTool = {
  name: "tms_list_fuel_purchases",
  label: "TMS: List Fuel Purchases",
  description:
    "List fuel purchase records. Filter by vehicle or jurisdiction. " +
    "Use to review fuel spending or verify IFTA data.",
  parameters: Type.Object({
    vehicle_id: Type.Optional(Type.String({ description: "UUID of the vehicle (optional filter)" })),
    jurisdiction: Type.Optional(Type.String({ description: "2-letter state code to filter by, e.g. 'TX'" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 100" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.jurisdiction) qs.set("jurisdiction", params.jurisdiction);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const purchases = await api.get(`/api/fuel/purchases?${qs}`);
      return ok(purchases);
    } catch (e) {
      return err(e);
    }
  },
};

// ── Maintenance ──────────────────────────────────────────────────────────────

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

// ── Compliance Scan ──────────────────────────────────────────────────────────

export const tmsComplianceScan: AnyAgentTool = {
  name: "tms_compliance_scan",
  label: "TMS: Fleet Compliance Scan",
  description:
    "Scan the entire fleet for compliance issues: expired annual inspections, " +
    "overdue maintenance, missing documents. Returns a list of alerts with severity.",
  parameters: Type.Object({}),
  execute: async (_id) => {
    try {
      const alerts = await api.get("/api/compliance/scan");
      return ok(alerts);
    } catch (e) {
      return err(e);
    }
  },
};

// ── IFTA ─────────────────────────────────────────────────────────────────────

export const tmsCalculateIfta: AnyAgentTool = {
  name: "tms_calculate_ifta",
  label: "TMS: Calculate IFTA Return",
  description:
    "Calculate or recalculate an IFTA quarterly return. Aggregates fuel purchases and miles " +
    "by jurisdiction for the specified quarter. Use before filing.",
  parameters: Type.Object({
    year: Type.Number({ description: "Tax year, e.g. 2026" }),
    quarter: Type.Number({ description: "Quarter number: 1, 2, 3, or 4" }),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.post("/api/compliance/ifta/calculate", params);
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListIftaReturns: AnyAgentTool = {
  name: "tms_list_ifta_returns",
  label: "TMS: List IFTA Returns",
  description: "List IFTA quarterly returns. Optionally filter by year.",
  parameters: Type.Object({
    year: Type.Optional(Type.Number({ description: "Filter by year, e.g. 2026" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 20" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.year) qs.set("year", String(params.year));
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const returns = await api.get(`/api/compliance/ifta?${qs}`);
      return ok(returns);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsFileIftaReturn: AnyAgentTool = {
  name: "tms_file_ifta_return",
  label: "TMS: File IFTA Return",
  description:
    "Mark an IFTA quarterly return as filed. This locks the return so it can't be recalculated.",
  parameters: Type.Object({
    ifta_id: Type.String({ description: "UUID of the IFTA return to mark as filed" }),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.post(`/api/compliance/ifta/${params.ifta_id}/file`, {});
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};

// ── Annual Inspections ───────────────────────────────────────────────────────

export const tmsCreateAnnualInspection: AnyAgentTool = {
  name: "tms_create_annual_inspection",
  label: "TMS: Create Annual Inspection",
  description:
    "Record a DOT annual inspection for a vehicle. Sets the inspection date and optional expiry. " +
    "Clears the 'no_annual_inspection' compliance alert.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
    inspected_at: Type.String({ description: "Date of inspection, e.g. '2026-03-01'" }),
    inspector_name: Type.Optional(Type.String({ description: "Name of the inspector" })),
    expires_at: Type.Optional(Type.String({ description: "Expiry date, e.g. '2027-03-01'" })),
    report_document_id: Type.Optional(Type.String({ description: "UUID of the linked inspection report document" })),
  }),
  execute: async (_id, params) => {
    try {
      const inspection = await api.post("/api/compliance/annual-inspections", params);
      return ok(inspection);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListAnnualInspections: AnyAgentTool = {
  name: "tms_list_annual_inspections",
  label: "TMS: List Annual Inspections",
  description: "List annual inspection records. Filter by vehicle to see inspection history.",
  parameters: Type.Object({
    vehicle_id: Type.Optional(Type.String({ description: "UUID of the vehicle (optional filter)" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const inspections = await api.get(`/api/compliance/annual-inspections?${qs}`);
      return ok(inspections);
    } catch (e) {
      return err(e);
    }
  },
};

// ── Roadside Inspections ─────────────────────────────────────────────────────

export const tmsCreateRoadsideInspection: AnyAgentTool = {
  name: "tms_create_roadside_inspection",
  label: "TMS: Create Roadside Inspection",
  description:
    "Record a roadside inspection (Level 1-3 DOT). Include corrections_certified_at " +
    "if violations were found and corrected.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
    inspected_at: Type.String({ description: "Date of inspection, e.g. '2026-03-05'" }),
    report_document_id: Type.Optional(Type.String({ description: "UUID of the linked inspection report document" })),
    corrections_certified_at: Type.Optional(
      Type.String({ description: "Date corrections were certified, e.g. '2026-03-06'" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const inspection = await api.post("/api/compliance/roadside-inspections", params);
      return ok(inspection);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListRoadsideInspections: AnyAgentTool = {
  name: "tms_list_roadside_inspections",
  label: "TMS: List Roadside Inspections",
  description: "List roadside inspection records. Filter by vehicle to see inspection history.",
  parameters: Type.Object({
    vehicle_id: Type.Optional(Type.String({ description: "UUID of the vehicle (optional filter)" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const inspections = await api.get(`/api/compliance/roadside-inspections?${qs}`);
      return ok(inspections);
    } catch (e) {
      return err(e);
    }
  },
};

// ── ELD ──────────────────────────────────────────────────────────────────────

export const tmsCreateEldDay: AnyAgentTool = {
  name: "tms_create_eld_day",
  label: "TMS: Create ELD Day Log",
  description:
    "Record an ELD day log for a driver. Stores the daily driving record from the ELD device. " +
    "Requires the storage key of the uploaded ELD file.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
    date_local: Type.String({ description: "Date of the log, e.g. '2026-03-05'" }),
    file_storage_key: Type.String({ description: "Storage key of the uploaded ELD data file" }),
    eld_vendor: Type.Optional(Type.String({ description: "ELD provider name: Motive, Samsara, Geotab, etc." })),
    eld_device_id: Type.Optional(Type.String({ description: "Device serial number or ID" })),
    timezone_offset_minutes: Type.Optional(Type.Number({ description: "UTC offset in minutes, e.g. -360 for CST" })),
    file_sha256: Type.Optional(Type.String({ description: "SHA-256 hash of the ELD file" })),
    notes: Type.Optional(Type.String({ description: "Additional notes" })),
  }),
  execute: async (_id, params) => {
    try {
      const day = await api.post("/api/eld/days", params);
      return ok(day);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListEldDays: AnyAgentTool = {
  name: "tms_list_eld_days",
  label: "TMS: List ELD Day Logs",
  description:
    "List ELD day logs. Filter by driver or vehicle to review hours-of-service records.",
  parameters: Type.Object({
    driver_id: Type.Optional(Type.String({ description: "UUID of the driver (optional filter)" })),
    vehicle_id: Type.Optional(Type.String({ description: "UUID of the vehicle (optional filter)" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 100" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.driver_id) qs.set("driver_id", params.driver_id);
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const days = await api.get(`/api/eld/days?${qs}`);
      return ok(days);
    } catch (e) {
      return err(e);
    }
  },
};
