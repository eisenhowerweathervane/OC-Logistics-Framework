import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsListBrokers: AnyAgentTool = {
  name: "tms_list_brokers",
  label: "TMS: List Brokers",
  description:
    "List brokers for the organization. Use to find a broker's ID, billing email, or payment terms. " +
    "Returns legal name, DBA, billing email, and payment terms days.",
  parameters: Type.Object({
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const brokers = await api.get(`/api/brokers?${qs}`);
      return ok(brokers);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetBroker: AnyAgentTool = {
  name: "tms_get_broker",
  label: "TMS: Get Broker",
  description: "Get full details for a single broker including contact info, billing email, and payment terms.",
  parameters: Type.Object({
    broker_id: Type.String({ description: "UUID of the broker" }),
  }),
  execute: async (_id, params) => {
    try {
      const broker = await api.get(`/api/brokers/${params.broker_id}`);
      return ok(broker);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsCreateBroker: AnyAgentTool = {
  name: "tms_create_broker",
  label: "TMS: Create Broker",
  description:
    "Create a new broker record. Required before creating loads for a new broker. " +
    "At minimum, provide the legal_name. Add billing_email and payment_terms_days for invoicing.",
  parameters: Type.Object({
    legal_name: Type.String({ description: "Legal company name, e.g. 'TQL' or 'CH Robinson'" }),
    dba_name: Type.Optional(Type.String({ description: "DBA / trade name if different from legal name" })),
    address_line_1: Type.Optional(Type.String({ description: "Street address" })),
    city: Type.Optional(Type.String({ description: "City" })),
    state: Type.Optional(Type.String({ description: "2-letter state code" })),
    zip: Type.Optional(Type.String({ description: "ZIP code" })),
    billing_email: Type.Optional(Type.String({ description: "Email for sending invoices" })),
    payment_terms_days: Type.Optional(Type.Number({ description: "Net payment terms in days, e.g. 30" })),
    notes: Type.Optional(Type.String({ description: "Internal notes about this broker" })),
  }),
  execute: async (_id, params) => {
    try {
      const broker = await api.post("/api/brokers", params);
      return ok(broker);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateBroker: AnyAgentTool = {
  name: "tms_update_broker",
  label: "TMS: Update Broker",
  description: "Update a broker's details — billing email, payment terms, DBA name, or notes.",
  parameters: Type.Object({
    broker_id: Type.String({ description: "UUID of the broker to update" }),
    dba_name: Type.Optional(Type.String({ description: "Updated DBA name" })),
    billing_email: Type.Optional(Type.String({ description: "Updated billing email" })),
    payment_terms_days: Type.Optional(Type.Number({ description: "Updated payment terms in days" })),
    notes: Type.Optional(Type.String({ description: "Updated notes" })),
  }),
  execute: async (_id, params) => {
    try {
      const { broker_id, ...body } = params;
      const broker = await api.patch(`/api/brokers/${broker_id}`, body);
      return ok(broker);
    } catch (e) {
      return err(e);
    }
  },
};
