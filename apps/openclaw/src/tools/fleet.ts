import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsListDrivers: AnyAgentTool = {
  name: "tms_list_drivers",
  label: "TMS: List Drivers",
  description: "List drivers in the organization. Filter by status to find active drivers available for dispatch.",
  parameters: Type.Object({
    status: Type.Optional(
      Type.String({ description: "Driver status filter: active, inactive, terminated. Default: all" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("driver_status", params.status);
      const drivers = await api.get(`/api/drivers?${qs}`);
      return ok(drivers);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListVehicles: AnyAgentTool = {
  name: "tms_list_vehicles",
  label: "TMS: List Vehicles",
  description: "List trucks/vehicles in the fleet. Filter by status to find available units.",
  parameters: Type.Object({
    status: Type.Optional(
      Type.String({ description: "Vehicle status filter: available, in_use, out_of_service. Default: all" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("vehicle_status", params.status);
      const vehicles = await api.get(`/api/vehicles?${qs}`);
      return ok(vehicles);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsDriverContext: AnyAgentTool = {
  name: "tms_driver_context",
  label: "TMS: Driver Context",
  description:
    "Get a driver's current situation: active load, current status, next stop details, " +
    "trailer number, and any missing required documents. Designed for answering driver questions " +
    "like 'where do I go next?' or 'what do I still need to submit?'",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
  }),
  execute: async (_id, params) => {
    try {
      const context = await api.get(`/api/drivers/${params.driver_id}/current-context`);
      return ok(context);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsVehicleCompliance: AnyAgentTool = {
  name: "tms_vehicle_compliance",
  label: "TMS: Vehicle Compliance Summary",
  description:
    "Get compliance status for a vehicle: annual inspection expiry, open maintenance items, " +
    "last roadside inspection date, and out-of-service flag.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
  }),
  execute: async (_id, params) => {
    try {
      const summary = await api.get(`/api/vehicles/${params.vehicle_id}/compliance-summary`);
      return ok(summary);
    } catch (e) {
      return err(e);
    }
  },
};
