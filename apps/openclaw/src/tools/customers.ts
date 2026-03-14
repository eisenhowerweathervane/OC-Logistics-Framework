import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsListCustomers: AnyAgentTool = {
  name: "tms_list_customers",
  label: "TMS: List Customers",
  description:
    "List customers (direct shippers) for the organization. Returns company name, contact info, " +
    "credit terms, preferred lanes, and status. Separate from brokers — customers are direct shipper relationships.",
  parameters: Type.Object({
    status: Type.Optional(Type.String({ description: "Filter by status: active or inactive" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("customer_status", params.status);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const customers = await api.get(`/api/customers?${qs}`);
      return ok(customers);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetCustomer: AnyAgentTool = {
  name: "tms_get_customer",
  label: "TMS: Get Customer",
  description: "Get full details for a single customer including contact info, credit terms, and preferred lanes.",
  parameters: Type.Object({
    customer_id: Type.String({ description: "UUID of the customer" }),
  }),
  execute: async (_id, params) => {
    try {
      const customer = await api.get(`/api/customers/${params.customer_id}`);
      return ok(customer);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsCreateCustomer: AnyAgentTool = {
  name: "tms_create_customer",
  label: "TMS: Create Customer",
  description:
    "Create a new customer (direct shipper) record. Separate from brokers — use this for direct shipper " +
    "relationships. At minimum provide company_name. Add contact info and credit terms as available.",
  parameters: Type.Object({
    company_name: Type.String({ description: "Company name, e.g. 'Walmart Distribution' or 'P&G'" }),
    contact_name: Type.Optional(Type.String({ description: "Primary contact person's name" })),
    contact_email: Type.Optional(Type.String({ description: "Contact email address" })),
    contact_phone: Type.Optional(Type.String({ description: "Contact phone number" })),
    address_line_1: Type.Optional(Type.String({ description: "Street address" })),
    city: Type.Optional(Type.String({ description: "City" })),
    state: Type.Optional(Type.String({ description: "2-letter state code" })),
    zip: Type.Optional(Type.String({ description: "ZIP code" })),
    credit_terms_days: Type.Optional(Type.Number({ description: "Credit terms in days, e.g. 30" })),
    preferred_lanes: Type.Optional(Type.String({ description: "Notes about preferred lanes/routes" })),
    notes: Type.Optional(Type.String({ description: "Internal notes about this customer" })),
  }),
  execute: async (_id, params) => {
    try {
      const customer = await api.post("/api/customers", params);
      return ok(customer);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateCustomer: AnyAgentTool = {
  name: "tms_update_customer",
  label: "TMS: Update Customer",
  description:
    "Update a customer's details — company name, contact info, credit terms, preferred lanes, status, or notes.",
  parameters: Type.Object({
    customer_id: Type.String({ description: "UUID of the customer to update" }),
    company_name: Type.Optional(Type.String({ description: "Updated company name" })),
    contact_name: Type.Optional(Type.String({ description: "Updated contact name" })),
    contact_email: Type.Optional(Type.String({ description: "Updated contact email" })),
    contact_phone: Type.Optional(Type.String({ description: "Updated contact phone" })),
    address_line_1: Type.Optional(Type.String({ description: "Updated street address" })),
    city: Type.Optional(Type.String({ description: "Updated city" })),
    state: Type.Optional(Type.String({ description: "Updated state" })),
    zip: Type.Optional(Type.String({ description: "Updated ZIP" })),
    credit_terms_days: Type.Optional(Type.Number({ description: "Updated credit terms in days" })),
    preferred_lanes: Type.Optional(Type.String({ description: "Updated preferred lanes notes" })),
    status: Type.Optional(Type.String({ description: "active or inactive" })),
    notes: Type.Optional(Type.String({ description: "Updated notes" })),
  }),
  execute: async (_id, params) => {
    try {
      const { customer_id, ...body } = params;
      const customer = await api.patch(`/api/customers/${customer_id}`, body);
      return ok(customer);
    } catch (e) {
      return err(e);
    }
  },
};
