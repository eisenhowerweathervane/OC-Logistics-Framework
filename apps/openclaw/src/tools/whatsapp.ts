import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsDriverByPhone: AnyAgentTool = {
  name: "tms_driver_by_phone",
  label: "TMS: Identify Driver by Phone",
  description:
    "Look up a driver by their phone number. Use this when receiving a WhatsApp message " +
    "from a driver to identify them before calling tms_driver_context. " +
    "Handles various phone formats (E.164, with/without country code, dashes, spaces).",
  parameters: Type.Object({
    phone: Type.String({
      description: "Phone number in any format, e.g. '+15551234567', '555-123-4567', '5551234567'",
    }),
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

export const tmsNotifyDriverDispatched: AnyAgentTool = {
  name: "tms_notify_driver_dispatched",
  label: "TMS: Notify Driver of Dispatch",
  description:
    "Send a WhatsApp notification to a driver about a new load assignment. " +
    "Call this after tms_assign_driver to let the driver know about their new load.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
    load_id: Type.String({ description: "UUID of the load" }),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.post("/api/notifications/whatsapp/dispatch-alert", {
        driver_id: params.driver_id,
        load_id: params.load_id,
      });
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsNotifyDriverDocsNeeded: AnyAgentTool = {
  name: "tms_notify_driver_docs_needed",
  label: "TMS: Remind Driver About Missing Docs",
  description:
    "Send a WhatsApp reminder to a driver about missing documents (BOL, POD, etc.). " +
    "Use tms_driver_context first to check which docs are missing.",
  parameters: Type.Object({
    driver_id: Type.String({ description: "UUID of the driver" }),
    load_id: Type.String({ description: "UUID of the load" }),
    missing_docs: Type.Array(Type.String(), {
      description: "List of missing document types, e.g. ['bol', 'pod']",
    }),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.post("/api/notifications/whatsapp/docs-reminder", {
        driver_id: params.driver_id,
        load_id: params.load_id,
        missing_docs: params.missing_docs,
      });
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};
