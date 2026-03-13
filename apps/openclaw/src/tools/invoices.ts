import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsListReceivables: AnyAgentTool = {
  name: "tms_list_receivables",
  label: "TMS: List Receivables",
  description:
    "List invoice receivables. Use overdue_only=true to find unpaid invoices past their due date. " +
    "Useful for weekly AR check-ins and follow-up prompts.",
  parameters: Type.Object({
    status: Type.Optional(
      Type.String({ description: "Filter by status: open, partial, paid, written_off" }),
    ),
    overdue_only: Type.Optional(
      Type.Boolean({ description: "Set true to show only overdue receivables" }),
    ),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("recv_status", params.status);
      if (params.overdue_only) qs.set("overdue_only", "true");
      if (params.page) qs.set("page", String(params.page));
      const receivables = await api.get(`/api/receivables?${qs}`);
      return ok(receivables);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGenerateInvoice: AnyAgentTool = {
  name: "tms_generate_invoice",
  label: "TMS: Generate Invoice Packet",
  description:
    "Trigger invoice packet readiness check for a delivered load. The backend verifies that a rate " +
    "confirmation and POD document are both linked. If ready, the load transitions to 'invoice_ready' " +
    "and the invoice packet status becomes 'ready'. Returns the current invoice packet state.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load (must be in 'delivered' or later status)" }),
  }),
  execute: async (_id, params) => {
    try {
      const packet = await api.post(`/api/loads/${params.load_id}/invoice-packet/generate`, {});
      return ok(packet);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetInvoicePacket: AnyAgentTool = {
  name: "tms_get_invoice_packet",
  label: "TMS: Get Invoice Packet",
  description: "Get the current invoice packet status for a load.",
  parameters: Type.Object({
    load_id: Type.String({ description: "UUID of the load" }),
  }),
  execute: async (_id, params) => {
    try {
      const packet = await api.get(`/api/loads/${params.load_id}/invoice-packet`);
      return ok(packet);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsRecordPayment: AnyAgentTool = {
  name: "tms_record_payment",
  label: "TMS: Record Payment",
  description:
    "Record a payment against a receivable. Automatically updates status to 'paid' (full) or 'partial'. " +
    "Use when a broker check arrives or a payment is confirmed.",
  parameters: Type.Object({
    receivable_id: Type.String({ description: "UUID of the receivable" }),
    amount_paid: Type.String({ description: "Payment amount in dollars, e.g. '2800.00'" }),
    payment_date: Type.String({ description: "ISO 8601 date of the payment, e.g. '2026-03-15T00:00:00Z'" }),
    payment_method: Type.Optional(Type.String({ description: "Payment method: check, ach, wire, etc." })),
    reference_number: Type.Optional(Type.String({ description: "Check number or transaction reference" })),
  }),
  execute: async (_id, params) => {
    try {
      const { receivable_id, ...body } = params;
      const receivable = await api.patch(`/api/receivables/${receivable_id}`, body);
      return ok(receivable);
    } catch (e) {
      return err(e);
    }
  },
};
