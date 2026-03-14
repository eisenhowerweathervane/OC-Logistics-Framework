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

export const tmsCreateDriver: AnyAgentTool = {
  name: "tms_create_driver",
  label: "TMS: Create Driver",
  description:
    "Create a new driver record. At minimum provide first_name and last_name. " +
    "Add phone, license_state, hire_date, pay_type, and pay_rate for a complete profile.",
  parameters: Type.Object({
    first_name: Type.String({ description: "Driver's first name" }),
    last_name: Type.String({ description: "Driver's last name" }),
    phone: Type.Optional(Type.String({ description: "Phone number, e.g. '+1-555-123-4567'" })),
    license_state: Type.Optional(Type.String({ description: "2-letter state code for CDL, e.g. 'TX'" })),
    hire_date: Type.Optional(Type.String({ description: "Hire date (YYYY-MM-DD)" })),
    pay_type: Type.Optional(Type.String({ description: "Pay type: per_mile, percentage, flat_rate" })),
    pay_rate: Type.Optional(Type.String({ description: "Pay rate as a decimal string, e.g. '0.55' for per-mile" })),
  }),
  execute: async (_id, params) => {
    try {
      const driver = await api.post("/api/drivers", params);
      return ok(driver);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetDriver: AnyAgentTool = {
  name: "tms_get_driver",
  label: "TMS: Get Driver",
  description: "Get full details for a single driver including contact info, pay type, and status.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
  }),
  execute: async (_id, params) => {
    try {
      const driver = await api.get(`/api/drivers/${params.driver_id}`);
      return ok(driver);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateDriver: AnyAgentTool = {
  name: "tms_update_driver",
  label: "TMS: Update Driver",
  description:
    "Update a driver's details — name, phone, license state, pay info, or status. " +
    "Use to correct info, change pay rate, or deactivate a driver.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver to update" }),
    first_name: Type.Optional(Type.String({ description: "Updated first name" })),
    last_name: Type.Optional(Type.String({ description: "Updated last name" })),
    phone: Type.Optional(Type.String({ description: "Updated phone number" })),
    license_state: Type.Optional(Type.String({ description: "Updated 2-letter CDL state code" })),
    pay_type: Type.Optional(Type.String({ description: "Updated pay type: per_mile, percentage, flat_rate" })),
    pay_rate: Type.Optional(Type.String({ description: "Updated pay rate" })),
    status: Type.Optional(Type.String({ description: "Updated status: active, inactive, terminated" })),
  }),
  execute: async (_id, params) => {
    try {
      const { driver_id, ...body } = params;
      const driver = await api.patch(`/api/drivers/${driver_id}`, body);
      return ok(driver);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetDriverByPhone: AnyAgentTool = {
  name: "tms_get_driver_by_phone",
  label: "TMS: Get Driver by Phone",
  description:
    "Look up a driver by phone number. Useful for identifying who is calling or messaging. " +
    "The backend normalizes the number, so any format works (e.g. '+15551234567' or '555-123-4567').",
  parameters: Type.Object({
    phone: Type.String({ description: "Phone number to look up" }),
  }),
  execute: async (_id, params) => {
    try {
      const driver = await api.get(`/api/drivers/by-phone/${encodeURIComponent(params.phone)}`);
      return ok(driver);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsCreateVehicle: AnyAgentTool = {
  name: "tms_create_vehicle",
  label: "TMS: Create Vehicle",
  description:
    "Add a new truck/vehicle to the fleet. At minimum provide unit_number. " +
    "Add make, model, year, plate info, and in_service_date for a complete record.",
  parameters: Type.Object({
    unit_number: Type.String({ description: "Unit number, e.g. 'T-101'" }),
    make: Type.Optional(Type.String({ description: "Vehicle make, e.g. 'Freightliner'" })),
    model: Type.Optional(Type.String({ description: "Vehicle model, e.g. 'Cascadia'" })),
    year: Type.Optional(Type.Number({ description: "Model year, e.g. 2023" })),
    plate_state: Type.Optional(Type.String({ description: "2-letter plate state, e.g. 'TX'" })),
    plate_number: Type.Optional(Type.String({ description: "License plate number" })),
    in_service_date: Type.Optional(Type.String({ description: "Date vehicle entered service (YYYY-MM-DD)" })),
  }),
  execute: async (_id, params) => {
    try {
      const vehicle = await api.post("/api/vehicles", params);
      return ok(vehicle);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetVehicle: AnyAgentTool = {
  name: "tms_get_vehicle",
  label: "TMS: Get Vehicle",
  description: "Get full details for a single vehicle including unit number, plate info, and status.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle" }),
  }),
  execute: async (_id, params) => {
    try {
      const vehicle = await api.get(`/api/vehicles/${params.vehicle_id}`);
      return ok(vehicle);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateVehicle: AnyAgentTool = {
  name: "tms_update_vehicle",
  label: "TMS: Update Vehicle",
  description:
    "Update a vehicle's details — unit number, plate info, status, or out-of-service date. " +
    "Use to correct info or mark a truck out of service.",
  parameters: Type.Object({
    vehicle_id: Type.String({ description: "UUID of the vehicle to update" }),
    unit_number: Type.Optional(Type.String({ description: "Updated unit number" })),
    make: Type.Optional(Type.String({ description: "Updated make" })),
    model: Type.Optional(Type.String({ description: "Updated model" })),
    year: Type.Optional(Type.Number({ description: "Updated model year" })),
    plate_state: Type.Optional(Type.String({ description: "Updated plate state" })),
    plate_number: Type.Optional(Type.String({ description: "Updated plate number" })),
    status: Type.Optional(Type.String({ description: "Updated status: available, in_use, out_of_service" })),
    out_of_service_date: Type.Optional(Type.String({ description: "Date vehicle went out of service (YYYY-MM-DD)" })),
  }),
  execute: async (_id, params) => {
    try {
      const { vehicle_id, ...body } = params;
      const vehicle = await api.patch(`/api/vehicles/${vehicle_id}`, body);
      return ok(vehicle);
    } catch (e) {
      return err(e);
    }
  },
};
